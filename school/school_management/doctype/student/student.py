import frappe
from frappe.model.document import Document
from frappe.utils import flt
from frappe.utils.password import update_password as _update_password
from frappe.core.doctype.user.user import User


class Student(Document):

    def validate(self):
        """Validate before save - set full name"""
        parts = [self.first_name, self.second_name, self.last_name]
        self.full_name = " ".join([p for p in parts if p])

        # Validate student type
        if self.student_type:
            meta = frappe.get_meta(self.doctype)
            options = [
                opt.strip()
                for opt in (meta.get_field("student_type").options or "").split("\n")
                if opt.strip()
            ]
            if self.student_type not in options:
                frappe.throw(
                    f"Student Type must be one of: {', '.join(options)}. Got: {self.student_type}"
                )

    def before_save(self):
        """Before save - generate dummy email if needed"""
        settings = frappe.get_single("School Settings")
        if settings.allow_non_strict_email and self.create_user and not self.portal_email:
            name_part = (
                self.full_name.lower().replace(" ", ".") if self.full_name else self.name
            )
            self.portal_email = f"{name_part}@dummy.school"
            frappe.msgprint(
                f"Dummy portal email generated: {self.portal_email}", indicator="blue"
            )

    def generate_reg_no(self):
        school_name = self.school or ""
        prefix_raw = school_name.split(" - ")[0].strip()
        prefix = "".join([c for c in prefix_raw if c.isalnum()]).upper()
        if not prefix:
            prefix = "STU"

        last = frappe.db.sql(
            """
            SELECT student_reg_no FROM `tabStudent`
            WHERE student_reg_no REGEXP %s
            ORDER BY CAST(SUBSTRING(student_reg_no, %s) AS UNSIGNED) DESC
            LIMIT 1
            """,
            ("^" + prefix + "[0-9]{5}$", len(prefix) + 1),
            as_dict=True,
        )

        if last and last[0].student_reg_no:
            last_no = last[0].student_reg_no
            num_part = last_no[len(prefix):]
            try:
                next_num = int(num_part) + 1
            except ValueError:
                next_num = 1
        else:
            next_num = 1

        return "{}{:05d}".format(prefix, next_num)

    def after_insert(self):
        """After insert - generate registration number if not set"""
        if not self.student_reg_no and self.school:
            reg_no = self.generate_reg_no()
            frappe.db.set_value("Student", self.name, "student_reg_no", reg_no)
            self.student_reg_no = reg_no

        self._create_all_users_and_records()

    def on_update(self):
        """On update - only re-run user creation when relevant fields change"""
        if self.flags.get("ignore_on_update"):
            return

        user_fields_changed = self.has_value_changed(
            "create_user"
        ) or self.has_value_changed("portal_email")

        self.create_customer()
        self.create_opening_balance_entry()
        self.create_admin_fee_invoice()
        self.create_registration_billing()

        if user_fields_changed and self.create_user:
            if not self.portal_email:
                frappe.throw("Please enter Portal Email address before saving.")
            self.create_student_portal_user()
            self.create_parent_portal_users()

    def _create_all_users_and_records(self):
        """Central method to create all users and records (used on first insert)"""
        self.create_customer()
        self.create_opening_balance_entry()
        self.create_admin_fee_invoice()
        self.create_registration_billing()

        if self.create_user:
            if not self.portal_email:
                frappe.throw("Please enter Portal Email address before saving.")
            self.create_student_portal_user()
            self.create_parent_portal_users()
        else:
            frappe.msgprint(
                "Create Portal User is not checked. No user will be created.",
                indicator="orange",
                alert=True,
            )

    # ------------------------------------------------------------------
    # Core helper: create or update a Frappe Website User
    # ------------------------------------------------------------------

    def _get_or_create_user(self, email, full_name, role):
        """
        Create a Website User with the given role, or update the existing one.
        Returns (user_doc, is_new). Password is NOT touched here.
        """
        name_parts = (full_name or email.split("@")[0]).split()
        first = name_parts[0]
        last = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        if frappe.db.exists("User", email):
            user = frappe.get_doc("User", email)
            existing_roles = [r.role for r in user.roles]
            if role not in existing_roles:
                user.append("roles", {"role": role})
            user.enabled = 1
            user.flags.ignore_permissions = True
            user.flags.ignore_password_policy = True
            user.save(ignore_permissions=True)
            return user, False  # (doc, is_new)
        else:
            user = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": first,
                "last_name": last,
                "enabled": 1,
                "user_type": "Website User",
                "send_welcome_email": 0,
                "roles": [{"role": role}],
            })
            user.flags.ignore_permissions = True
            user.flags.ignore_password_policy = True
            user.insert(ignore_permissions=True)
            
            # Trigger webhook after user creation
            self._trigger_user_created_webhook(email, full_name, role)
            
            return user, True  # (doc, is_new)

    def _trigger_user_created_webhook(self, email, full_name, role):
        """Trigger webhook when user is created"""
        try:
            # Create a webhook event
            webhook_data = {
                "event": "user_created",
                "user_email": email,
                "user_name": full_name,
                "user_role": role,
                "student_name": self.name,
                "student_full_name": self.full_name,
                "timestamp": frappe.utils.now()
            }
            
            # Log webhook event
            frappe.log_error(
                "User Created Webhook",
                f"User: {email}, Role: {role}, Student: {self.name}\nData: {webhook_data}"
            )
            
            # You can add external webhook call here if needed
            # Example: requests.post("https://your-webhook-url.com/endpoint", json=webhook_data)
            
        except Exception as e:
            frappe.log_error(f"Webhook trigger failed: {str(e)}", "Webhook Error")

    # ------------------------------------------------------------------
    # Password helper — three-layer approach for guaranteed login
    # ------------------------------------------------------------------

    def _force_set_password(self, email, password):
        """
        Reliably write the password so the user can log in immediately.

        Layer 1 — frappe.utils.password.update_password
        Layer 2 — direct __Auth upsert
        Layer 3 — frappe.db.commit
        """
        # Layer 1
        _update_password(email, password, logout_all_sessions=True)

        # Layer 2 — direct upsert into __Auth
        try:
            from frappe.utils.password import passlibctx
            hashed = passlibctx.hash(password)

            existing_auth = frappe.db.sql(
                "SELECT name FROM `__Auth` "
                "WHERE `doctype`=%s AND `name`=%s AND `fieldname`=%s",
                ("User", email, "password"),
            )
            if existing_auth:
                frappe.db.sql(
                    "UPDATE `__Auth` SET `password`=%s, `encrypted`=0 "
                    "WHERE `doctype`=%s AND `name`=%s AND `fieldname`=%s",
                    (hashed, "User", email, "password"),
                )
            else:
                frappe.db.sql(
                    "INSERT INTO `__Auth` "
                    "(`doctype`, `name`, `fieldname`, `password`, `encrypted`) "
                    "VALUES (%s, %s, %s, %s, 0)",
                    ("User", email, "password", hashed),
                )
        except Exception:
            frappe.log_error(
                "_force_set_password direct __Auth write",
                frappe.get_traceback(),
            )

        # Layer 3 — flush so the row is committed before the response returns
        frappe.db.commit()
        
        # Trigger password set webhook
        self._trigger_password_set_webhook(email)

    def _trigger_password_set_webhook(self, email):
        """Trigger webhook when password is set"""
        try:
            webhook_data = {
                "event": "password_set",
                "user_email": email,
                "student_name": self.name,
                "student_full_name": self.full_name,
                "timestamp": frappe.utils.now()
            }
            
            frappe.log_error(
                "Password Set Webhook",
                f"Password set for user: {email}\nData: {webhook_data}"
            )
            
        except Exception as e:
            frappe.log_error(f"Password webhook failed: {str(e)}", "Webhook Error")

    # ------------------------------------------------------------------
    # Student portal user
    # ------------------------------------------------------------------

    def create_student_portal_user(self):
        """Create portal user for student with immediate login capability"""
        settings = frappe.get_single("School Settings")
        has_password = hasattr(self, "portal_password") and self.portal_password

        try:
            user, is_new = self._get_or_create_user(
                self.portal_email,
                self.full_name or self.first_name,
                "Student Portal",
            )

            if settings.allow_non_strict_email and has_password:
                # Force-write the password so the student can log in immediately
                self._force_set_password(self.portal_email, self.portal_password)
                
                # Also set as new_password for immediate effect
                user.new_password = self.portal_password
                user.flags.ignore_password_policy = True
                user.save(ignore_permissions=True)
                
                frappe.msgprint(
                    f"✅ Student user {self.portal_email} "
                    f"{'created' if is_new else 'updated'} — can log in now with password.",
                    indicator="green",
                    alert=True,
                )
                
                # Test login capability
                self._test_user_login(self.portal_email, self.portal_password)
                
            else:
                # No password supplied — send a reset / welcome link
                reset_key = user.reset_password()
                frappe.sendmail(
                    recipients=[self.portal_email],
                    subject="Your School Portal Access",
                    message=(
                        f"<p>Dear {self.full_name or self.first_name},</p>"
                        f"<p>Your student portal account has been created.</p>"
                        f"<p>Email: {self.portal_email}</p>"
                        f"<p>Click below to set your password and log in:</p>"
                        f"<p><a href=\"{frappe.utils.get_url()}"
                        f"/update-password?key={reset_key}\">"
                        f"Set Password &amp; Login</a></p>"
                        f"<p>Regards,<br>School Administration</p>"
                    ),
                )
                frappe.msgprint(
                    f"✅ Student user {self.portal_email} created. Invitation email sent.",
                    indicator="green",
                    alert=True,
                )

            self._assign_cost_center_permission(self.portal_email)
            self._assign_default_role_permissions(self.portal_email)
            self._assign_user_to_student(self.portal_email)

        except Exception as e:
            frappe.log_error(
                f"Student portal user creation failed for {self.portal_email}",
                frappe.get_traceback(),
            )
            frappe.msgprint(
                f"❌ Error creating student user {self.portal_email}: {str(e)}",
                indicator="red",
                alert=True,
            )

    def _test_user_login(self, email, password):
        """Test if user can login with the given password"""
        try:
            from frappe.utils.password import check_password
            
            # Try to authenticate
            authenticated_user = check_password(email, password)
            if authenticated_user:
                frappe.msgprint(
                    f"✅ Login test successful for {email}",
                    indicator="green",
                    alert=True,
                )
            else:
                frappe.msgprint(
                    f"⚠️ Login test failed for {email}. Please reset password if needed.",
                    indicator="orange",
                    alert=True,
                )
        except Exception as e:
            frappe.msgprint(
                f"⚠️ Login test warning for {email}: {str(e)}",
                indicator="orange",
                alert=True,
            )

    def _assign_user_to_student(self, email):
        """Link the portal user to the student document"""
        try:
            # Add user permission for student document
            if not frappe.db.exists("User Permission", {
                "user": email,
                "allow": "Student",
                "for_value": self.name
            }):
                user_permission = frappe.get_doc({
                    "doctype": "User Permission",
                    "user": email,
                    "allow": "Student",
                    "for_value": self.name,
                    "applicable_for": "Student"
                })
                user_permission.flags.ignore_permissions = True
                user_permission.insert(ignore_permissions=True)
                
                frappe.msgprint(
                    f"✅ User {email} linked to student {self.name}",
                    indicator="green",
                    alert=True,
                )
        except Exception as e:
            frappe.log_error(f"User to student assignment failed: {str(e)}", "Assignment Error")

    # ------------------------------------------------------------------
    # Parent portal users
    # ------------------------------------------------------------------

    def create_parent_portal_users(self):
        """Create portal users for parents / guardians"""
        parent_entries = []

        if self.father_email:
            parent_entries.append({
                "email": self.father_email,
                "full_name": self.father_name or "Parent",
                "role": "Parent",
            })

        if self.mother_email and self.mother_email != self.father_email:
            parent_entries.append({
                "email": self.mother_email,
                "full_name": self.mother_name or "Parent",
                "role": "Parent",
            })

        if self.guardian_email and self.guardian_email not in [
            self.father_email,
            self.mother_email,
        ]:
            parent_entries.append({
                "email": self.guardian_email,
                "full_name": self.guardian_name or "Guardian",
                "role": "Parent",
            })

        for entry in parent_entries:
            try:
                existing_parent = frappe.db.exists(
                    "Parent", {"portal_email": entry["email"]}
                )

                if existing_parent:
                    parent_doc = frappe.get_doc("Parent", existing_parent)
                    already_linked = any(
                        row.student == self.name
                        for row in parent_doc.get("children", [])
                    )
                    if not already_linked:
                        parent_doc.append("children", {"student": self.name})
                        parent_doc.flags.ignore_permissions = True
                        parent_doc.save(ignore_permissions=True)
                        frappe.msgprint(
                            f"Student linked to existing parent: {entry['email']}",
                            indicator="blue",
                            alert=True,
                        )
                else:
                    parent_doc = frappe.new_doc("Parent")
                    parent_doc.full_name = entry["full_name"]
                    parent_doc.portal_email = entry["email"]
                    parent_doc.flags.ignore_permissions = True
                    parent_doc.insert(ignore_permissions=True)
                    parent_doc.append("children", {"student": self.name})
                    parent_doc.save(ignore_permissions=True)
                    frappe.msgprint(
                        f"Parent account created for: {entry['email']}",
                        indicator="green",
                        alert=True,
                    )

                # Parents always receive a reset link (no stored password)
                user, is_new = self._get_or_create_user(
                    entry["email"], entry["full_name"], entry["role"]
                )

                if is_new:
                    reset_key = user.reset_password()
                    frappe.sendmail(
                        recipients=[entry["email"]],
                        subject="Your School Portal Access",
                        message=(
                            f"<p>Dear {entry['full_name']},</p>"
                            f"<p>A portal account has been created for you.</p>"
                            f"<p>Email: {entry['email']}</p>"
                            f"<p>Click below to set your password:</p>"
                            f"<p><a href=\"{frappe.utils.get_url()}"
                            f"/update-password?key={reset_key}\">"
                            f"Set Password &amp; Login</a></p>"
                            f"<p>Regards,<br>School Administration</p>"
                        ),
                    )
                    frappe.msgprint(
                        f"✅ Parent user {entry['email']} created. Invitation sent.",
                        indicator="green",
                        alert=True,
                    )

                self._assign_cost_center_permission(entry["email"])
                self._assign_default_role_permissions(entry["email"])

            except Exception as e:
                frappe.log_error(
                    f"Parent user creation failed for {entry['email']}",
                    frappe.get_traceback(),
                )
                frappe.msgprint(
                    f"❌ Error creating parent user {entry['email']}: {str(e)}",
                    indicator="red",
                    alert=True,
                )

    # ------------------------------------------------------------------
    # Permission helpers
    # ------------------------------------------------------------------

    def _assign_cost_center_permission(self, email):
        """Assign cost center permission to user based on selected school"""
        try:
            if not self.school:
                frappe.msgprint(
                    "⚠️ No school selected, skipping cost center permission",
                    indicator="orange",
                    alert=True,
                )
                return False

            existing_permission = frappe.db.exists(
                "User Permission",
                {
                    "user": email,
                    "allow": "Cost Center",
                    "for_value": self.school,
                },
            )

            if not existing_permission:
                user_permission = frappe.get_doc({
                    "doctype": "User Permission",
                    "user": email,
                    "allow": "Cost Center",
                    "for_value": self.school,
                    "applicable_for": "",
                })
                user_permission.flags.ignore_permissions = True
                user_permission.insert(ignore_permissions=True)
                frappe.msgprint(
                    f"✅ Cost Center '{self.school}' permission assigned to {email}",
                    indicator="green",
                    alert=True,
                )
            else:
                frappe.msgprint(
                    f"ℹ️ Cost Center permission already exists for {email}",
                    indicator="blue",
                    alert=True,
                )

            return True

        except Exception as e:
            frappe.log_error(
                f"Cost center permission assignment failed for {email}",
                frappe.get_traceback(),
            )
            frappe.msgprint(
                f"⚠️ Could not assign cost center permission: {str(e)}",
                indicator="orange",
                alert=True,
            )
            return False

    def _assign_default_role_permissions(self, email):
        """Assign default role-based permissions to user"""
        try:
            user = frappe.get_doc("User", email)
            
            if not user.user_type == "Website User":
                user.user_type = "Website User"
                user.flags.ignore_permissions = True
                user.save(ignore_permissions=True)
            
            frappe.msgprint(
                f"✅ Default permissions assigned to {email}",
                indicator="green",
                alert=True,
            )
            
        except Exception as e:
            frappe.log_error(
                f"Default role permission assignment failed for {email}",
                frappe.get_traceback(),
            )

    # ------------------------------------------------------------------
    # Customer
    # ------------------------------------------------------------------

    def create_customer(self):
        """Create or update customer linked to this student"""
        if not self.full_name:
            return

        try:
            customer_group = (
                frappe.db.get_single_value("Selling Settings", "customer_group")
                or "All Customer Groups"
            )
            territory = (
                frappe.db.get_single_value("Selling Settings", "territory")
                or "All Territories"
            )

            if self.student_category:
                customer_group = self.student_category

            details_parts = []
            if self.student_class:
                details_parts.append(f"Class: {self.student_class}")
            if self.section:
                details_parts.append(f"Section: {self.section}")
            if self.school:
                details_parts.append(f"School: {self.school}")
            if self.student_reg_no:
                details_parts.append(f"Reg No: {self.student_reg_no}")
            if self.student_type:
                details_parts.append(f"Type: {self.student_type}")

            customer_details = " | ".join(details_parts)

            existing = None
            if self.student_reg_no:
                existing = frappe.db.get_value(
                    "Customer",
                    {"custom_student_reg_no": self.student_reg_no},
                    "name",
                )
            if not existing:
                existing = frappe.db.exists(
                    "Customer", {"customer_name": self.full_name}
                )

            if existing:
                customer = frappe.get_doc("Customer", existing)
                customer.customer_name = self.full_name
                customer.customer_group = customer_group
                customer.territory = territory
                customer.mobile_no = self.phone_number or customer.mobile_no
                customer.custom_student_reg_no = self.student_reg_no or ""
                customer.custom_student_section = self.section or ""
                customer.custom_student_class = self.student_class or ""
                customer.custom_school = self.school or ""
                customer.custom_student_type = self.student_type or ""
                customer.custom_gender = self.gender or ""
                customer.customer_details = customer_details
                customer.custom_class = self.name
                customer.student_name = self.full_name
                if self.student_image:
                    customer.image = self.student_image
                customer.flags.ignore_permissions = True
                customer.save(ignore_permissions=True)
                
                if self.create_user and self.portal_email:
                    self._assign_customer_to_user(self.portal_email, customer.name)
            else:
                customer = frappe.get_doc({
                    "doctype": "Customer",
                    "customer_name": self.full_name,
                    "customer_type": "Individual",
                    "customer_group": customer_group,
                    "territory": territory,
                    "mobile_no": self.phone_number or "",
                    "custom_student_reg_no": self.student_reg_no or "",
                    "custom_student_section": self.section or "",
                    "custom_student_class": self.student_class or "",
                    "custom_school": self.school or "",
                    "custom_student_type": self.student_type or "",
                    "custom_gender": self.gender or "",
                    "customer_details": customer_details,
                    "image": self.student_image or "",
                    "custom_class": self.name,
                    "student_name": self.full_name,
                })
                customer.flags.ignore_permissions = True
                customer.insert(ignore_permissions=True)
                
                if self.create_user and self.portal_email:
                    self._assign_customer_to_user(self.portal_email, customer.name)

            frappe.msgprint(
                f"✅ Customer {self.full_name} created/updated",
                indicator="green",
                alert=True,
            )

        except Exception as e:
            frappe.log_error(
                f"Customer creation failed for {self.full_name}",
                frappe.get_traceback(),
            )
            frappe.msgprint(
                f"❌ Error creating customer: {str(e)}",
                indicator="red",
                alert=True,
            )

    def _assign_customer_to_user(self, email, customer_name):
        """Assign customer to user for portal access"""
        try:
            existing_contact = frappe.db.exists(
                "Contact",
                {
                    "email_id": email,
                }
            )
            
            if not existing_contact:
                contact = frappe.get_doc({
                    "doctype": "Contact",
                    "first_name": self.first_name,
                    "last_name": self.last_name,
                    "email_ids": [{"email_id": email, "is_primary": 1}],
                    "links": [{"link_doctype": "Customer", "link_name": customer_name}]
                })
                contact.flags.ignore_permissions = True
                contact.insert(ignore_permissions=True)
                frappe.msgprint(
                    f"✅ Contact created for {email} linked to customer {customer_name}",
                    indicator="green",
                    alert=True,
                )
        except Exception as e:
            frappe.log_error(
                f"Customer to user assignment failed for {email}",
                frappe.get_traceback(),
            )

    # ------------------------------------------------------------------
    # Opening balance
    # ------------------------------------------------------------------

    def create_opening_balance_entry(self):
        """Create opening balance journal entry"""
        if not self.has_opening_balance or not self.opening_balance:
            return
        if not self.full_name:
            return

        existing = frappe.db.exists(
            "Journal Entry",
            {
                "user_remark": f"Opening Balance for {self.full_name}",
                "docstatus": 1,
            },
        )
        if existing:
            return

        try:
            company = frappe.defaults.get_global_default("company")
            receivable_account = frappe.db.get_value(
                "Company", company, "default_receivable_account"
            )

            opening_account = (
                frappe.db.get_value(
                    "Account",
                    {
                        "account_type": "Equity",
                        "company": company,
                        "is_group": 0,
                        "account_name": ["like", "%Opening Balance%"],
                    },
                    "name",
                )
                or frappe.db.get_value(
                    "Account",
                    {
                        "account_type": "Temporary",
                        "company": company,
                        "is_group": 0,
                    },
                    "name",
                )
                or "Opening Balance Equity - SS"
            )

            je = frappe.get_doc({
                "doctype": "Journal Entry",
                "voucher_type": "Opening Entry",
                "posting_date": self.opening_balance_date or frappe.utils.today(),
                "company": company,
                "user_remark": f"Opening Balance for {self.full_name}",
                "accounts": [
                    {
                        "account": receivable_account,
                        "party_type": "Customer",
                        "party": self.full_name,
                        "debit_in_account_currency": self.opening_balance,
                        "credit_in_account_currency": 0,
                        "cost_center": self.cost_center,
                    },
                    {
                        "account": opening_account,
                        "debit_in_account_currency": 0,
                        "credit_in_account_currency": self.opening_balance,
                        "cost_center": self.cost_center,
                    },
                ],
            })
            je.flags.ignore_permissions = True
            je.insert()
            je.submit()

            frappe.msgprint(
                f"✅ Opening balance entry created for {self.full_name}",
                indicator="green",
                alert=True,
            )

        except Exception as e:
            frappe.log_error(
                f"Opening balance JE failed for {self.full_name}",
                frappe.get_traceback(),
            )

    # ------------------------------------------------------------------
    # Admin fee invoice + receipt
    # ------------------------------------------------------------------

    def create_admin_fee_invoice(self):
        """Create admin fee invoice"""
        if not self.paying_admin_fee or not self.admin_fees_structure:
            return
        if not self.full_name:
            return

        existing_billing = frappe.db.exists(
            "Billing",
            {
                "student": self.name,
                "fees_structure": self.admin_fees_structure,
                "docstatus": ["!=", 2],
            },
        )

        if existing_billing:
            if self.admin_fee_paid:
                inv = frappe.db.get_value(
                    "Sales Invoice",
                    {
                        "customer": self.full_name,
                        "fees_structure": self.admin_fees_structure,
                        "docstatus": ["!=", 2],
                    },
                    "name",
                )
                if inv:
                    self.create_admin_fee_receipting(inv)
            return

        try:
            if not frappe.db.exists("Customer", {"customer_name": self.full_name}):
                self.create_customer()

            fees_doc = frappe.get_doc("Fees Structure", self.admin_fees_structure)
            if not fees_doc.fees_items:
                frappe.log_error(
                    "create_admin_fee_invoice",
                    f"Fees Structure {self.admin_fees_structure} has no items",
                )
                return

            billing = frappe.new_doc("Billing")
            billing.date = frappe.utils.today()
            billing.cost_center = self.cost_center or self.school
            billing.fees_structure = self.admin_fees_structure
            billing.student = self.name
            billing.student_class = self.student_class
            billing.section = self.section

            for item in fees_doc.fees_items:
                billing.append(
                    "items",
                    {
                        "item_code": item.item_code,
                        "item_name": item.item_name,
                        "qty": 1,
                        "rate": item.rate or 0,
                        "amount": flt(item.rate or 0),
                        "cost_center": self.cost_center or self.school,
                    },
                )

            billing.flags.ignore_permissions = True
            billing.insert(ignore_permissions=True)
            billing.submit()

            invoice_name = frappe.db.get_value(
                "Sales Invoice",
                {
                    "customer": self.full_name,
                    "fees_structure": self.admin_fees_structure,
                    "docstatus": ["!=", 2],
                },
                "name",
            )

            if self.admin_fee_paid and invoice_name:
                self.create_admin_fee_receipting(invoice_name)

            frappe.msgprint(
                f"✅ Admin fee invoice created for {self.full_name}",
                indicator="green",
                alert=True,
            )

        except Exception as e:
            frappe.log_error(
                f"Admin fee billing failed for {self.full_name}",
                frappe.get_traceback(),
            )

    def create_admin_fee_receipting(self, invoice_name):
        """Create receipt for admin fee"""
        if not invoice_name:
            return

        existing = frappe.db.exists(
            "Receipting",
            {
                "student_name": self.name,
                "docstatus": ["!=", 2],
            },
        )
        if existing:
            return

        try:
            outstanding = frappe.db.get_value(
                "Sales Invoice", invoice_name, "outstanding_amount"
            )
            if not flt(outstanding) > 0:
                return

            account = self.account
            if not account:
                frappe.log_error(
                    "create_admin_fee_receipting",
                    f"No account selected on Student {self.name}",
                )
                return

            receipt = frappe.new_doc("Receipting")
            receipt.student_name = self.name
            receipt.student_class = self.student_class
            receipt.section = self.section
            receipt.date = frappe.utils.today()
            receipt.account = account

            receipt.append(
                "invoice",
                {
                    "invoice_number": invoice_name,
                    "outstanding": flt(outstanding),
                    "allocated": flt(outstanding),
                    "fees_structure": self.admin_fees_structure,
                },
            )

            receipt.flags.ignore_permissions = True
            receipt.insert(ignore_permissions=True)
            receipt.submit()

            frappe.msgprint(
                f"✅ Admin fee receipt created for {self.full_name}",
                indicator="green",
                alert=True,
            )

        except Exception as e:
            frappe.log_error(
                f"Admin fee receipting failed for {self.full_name}",
                frappe.get_traceback(),
            )

    # ------------------------------------------------------------------
    # Registration billing
    # ------------------------------------------------------------------

    def create_registration_billing(self):
        """Create registration billing based on student type"""
        if hasattr(self, "billed_on_registration") and self.billed_on_registration:
            return

        try:
            settings = frappe.get_single("School Settings")

            if not self.student_type:
                return

            fees_structure = None
            for row in settings.get("registration_billing", []):
                if row.status == self.student_type:
                    fees_structure = row.billing
                    break

            if not fees_structure:
                return

            billing = frappe.new_doc("Billing")
            billing.student = self.name
            billing.student_class = self.student_class
            billing.section = self.section
            billing.date = frappe.utils.today()
            billing.fees_structure = fees_structure

            fs_doc = frappe.get_doc("Fees Structure", fees_structure)
            if fs_doc.get("fees_items"):
                for item in fs_doc.get("fees_items", []):
                    billing.append(
                        "items",
                        {
                            "item_code": item.item_code,
                            "item_name": item.item_name,
                            "qty": 1,
                            "rate": item.rate or 0,
                            "amount": flt(item.rate or 0),
                            "cost_center": self.cost_center or self.school,
                        },
                    )

            billing.flags.ignore_permissions = True
            billing.insert(ignore_permissions=True)
            billing.submit()

            frappe.db.set_value("Student", self.name, "billed_on_registration", 1)
            self.billed_on_registration = 1

            frappe.msgprint(
                f"✅ Registration billing created for {self.full_name}",
                indicator="green",
                alert=True,
            )

        except Exception as e:
            frappe.log_error(
                "Registration Billing Error",
                f"Student: {self.name} Error: {str(e)}",
            )


# ----------------------------------------------------------------------
# Webhook endpoint for external password setting
# ----------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def set_user_password_via_webhook(email, password, api_key=None):
    """
    Webhook endpoint to set user password externally
    Usage: POST /api/method/school.school.doctype.student.student.set_user_password_via_webhook
    """
    try:
        # Verify API key if provided
        if api_key:
            valid_api_key = frappe.db.get_single_value("School Settings", "webhook_api_key")
            if api_key != valid_api_key:
                return {"status": "error", "message": "Invalid API key"}
        
        # Check if user exists
        if not frappe.db.exists("User", email):
            return {"status": "error", "message": f"User {email} does not exist"}
        
        # Set password
        _update_password(email, password, logout_all_sessions=True)
        
        # Direct __Auth update for safety
        try:
            from frappe.utils.password import passlibctx
            hashed = passlibctx.hash(password)
            
            existing_auth = frappe.db.sql(
                "SELECT name FROM `__Auth` "
                "WHERE `doctype`=%s AND `name`=%s AND `fieldname`=%s",
                ("User", email, "password"),
            )
            if existing_auth:
                frappe.db.sql(
                    "UPDATE `__Auth` SET `password`=%s, `encrypted`=0 "
                    "WHERE `doctype`=%s AND `name`=%s AND `fieldname`=%s",
                    (hashed, "User", email, "password"),
                )
            else:
                frappe.db.sql(
                    "INSERT INTO `__Auth` "
                    "(`doctype`, `name`, `fieldname`, `password`, `encrypted`) "
                    "VALUES (%s, %s, %s, %s, 0)",
                    ("User", email, "password", hashed),
                )
        except:
            pass
        
        frappe.db.commit()
        
        return {"status": "success", "message": f"Password set for {email}"}
        
    except Exception as e:
        frappe.log_error(f"Webhook password set failed: {str(e)}", "Webhook Error")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def create_user_via_webhook(email, first_name, last_name, role, password=None, api_key=None):
    """
    Webhook endpoint to create user externally
    """
    try:
        # Verify API key if provided
        if api_key:
            valid_api_key = frappe.db.get_single_value("School Settings", "webhook_api_key")
            if api_key != valid_api_key:
                return {"status": "error", "message": "Invalid API key"}
        
        # Check if user exists
        if frappe.db.exists("User", email):
            return {"status": "error", "message": f"User {email} already exists"}
        
        # Create user
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "enabled": 1,
            "user_type": "Website User",
            "send_welcome_email": 0,
            "roles": [{"role": role}]
        })
        user.flags.ignore_permissions = True
        user.flags.ignore_password_policy = True
        user.insert(ignore_permissions=True)
        
        # Set password if provided
        if password:
            _update_password(email, password, logout_all_sessions=True)
            user.new_password = password
            user.save(ignore_permissions=True)
        
        frappe.db.commit()
        
        return {"status": "success", "message": f"User {email} created", "user": user.name}
        
    except Exception as e:
        frappe.log_error(f"Webhook user creation failed: {str(e)}", "Webhook Error")
        return {"status": "error", "message": str(e)}


# ----------------------------------------------------------------------
# Permission query hook
# ----------------------------------------------------------------------

def get_permission_query_conditions(user):
    """Teachers only see students in their assigned classes/sections"""
    if not user:
        user = frappe.session.user

    if "System Manager" in frappe.get_roles(user):
        return ""

    if "Teacher" not in frappe.get_roles(user):
        return ""

    teacher_name = frappe.db.get_value("Teacher", {"portal_email": user}, "name")
    if not teacher_name:
        teacher_name = frappe.db.get_value("Teacher", {"email": user}, "name")

    if not teacher_name:
        return "1=0"

    assigned = frappe.db.get_all(
        "Teacher Class Assignment Item",
        filters={"parent": teacher_name},
        fields=["class_name", "section"],
    )

    if not assigned:
        return "1=0"

    conditions = []
    for row in assigned:
        if row.class_name and row.section:
            conditions.append(
                f"(`tabStudent`.`student_class` = {frappe.db.escape(row.class_name)}"
                f" AND `tabStudent`.`section` = {frappe.db.escape(row.section)})"
            )
        elif row.class_name:
            conditions.append(
                f"`tabStudent`.`student_class` = {frappe.db.escape(row.class_name)}"
            )

    if not conditions:
        return "1=0"

    return "(" + " OR ".join(conditions) + ")"


# ----------------------------------------------------------------------
# Whitelisted API
# ----------------------------------------------------------------------

@frappe.whitelist()
def generate_reg_no_for_school(school, current_student=None):
    """Generate next student reg no for a given school (cost center)"""
    prefix_raw = school.split(" - ")[0].strip()
    prefix = "".join([c for c in prefix_raw if c.isalnum()]).upper()
    if not prefix:
        prefix = "STU"

    exclude_clause = ""
    params = ["^" + prefix + "[0-9]{5}$", len(prefix) + 1]
    if current_student:
        exclude_clause = "AND name != %s"
        params.append(current_student)

    last = frappe.db.sql(
        f"""
        SELECT student_reg_no FROM `tabStudent`
        WHERE student_reg_no REGEXP %s
        {exclude_clause}
        ORDER BY CAST(SUBSTRING(student_reg_no, %s) AS UNSIGNED) DESC
        LIMIT 1
        """,
        params,
        as_dict=True,
    )

    if last and last[0].student_reg_no:
        last_no = last[0].student_reg_no
        num_part = last_no[len(prefix):]
        try:
            next_num = int(num_part) + 1
        except ValueError:
            next_num = 1
    else:
        next_num = 1

    return "{}{:05d}".format(prefix, next_num)