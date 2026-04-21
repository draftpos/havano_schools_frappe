import frappe
from frappe.model.document import Document
from frappe.utils import flt
from frappe.utils.password import update_password as _update_password


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

        # Ensure password doesn't match registration number
        if self.portal_password and self.student_reg_no and self.portal_password == self.student_reg_no:
            frappe.throw("Portal Password cannot be the same as the Student Registration Number for security reasons.")

    def before_save(self):
        """Before save - set full name and other prep logic"""
        # (Dummy email generation removed as per manual password requirement)
        pass

    def autoname(self):
        """Autoname - generate registration number based on school/cost center"""
        self.name = self.generate_reg_no()
        self.student_reg_no = self.name

    def generate_reg_no(self):
        school_name = self.school or ""
        # Improved prefix: First word + first letter of other words
        # Example: "Greenwood Primary School" -> "GREENWOODPS"
        words = school_name.replace("-", " ").split()
        if not words:
            prefix = "STU"
        else:
            first_word = "".join([c for c in words[0] if c.isalnum()]).upper()
            others = "".join([w[0].upper() for w in words[1:] if w and w[0].isalnum()])
            prefix = first_word + others
        
        if not prefix:
            prefix = "STU"

        # Find the next sequence number for this specific prefix
        last = frappe.db.sql(
            """
            SELECT name FROM `tabStudent`
            WHERE name LIKE %s
            ORDER BY CAST(SUBSTRING(name, %s) AS UNSIGNED) DESC
            LIMIT 1
            """,
            (prefix + "%", len(prefix) + 1),
            as_dict=True,
        )

        if last and last[0].name:
            last_no = last[0].name
            num_part = last_no[len(prefix):]
            try:
                next_num = int(num_part) + 1
            except ValueError:
                next_num = 1
        else:
            next_num = 1

        return "{}{:05d}".format(prefix, next_num)

    def after_insert(self):
        """After insert - complete initialization"""
        self._create_all_users_and_records()

    def on_update(self):
        """On update - only re-run user creation when relevant fields change"""
        if self.flags.get("ignore_on_update"):
            return

        user_fields_changed = self.has_value_changed("portal_email") or self.has_value_changed("portal_password") or self.has_value_changed("create_user")

        self.create_customer()
        self.create_opening_balance_entry()
        self.create_admin_fee_invoice()
        self.create_registration_billing()

        if user_fields_changed and self.create_user and self.portal_email:
            self.create_student_portal_user()
            self.create_parent_portal_users()

    def _create_all_users_and_records(self):
        """Central method to create all users and records (used on first insert)"""
        self.create_customer()
        self.create_opening_balance_entry()
        self.create_admin_fee_invoice()
        self.create_registration_billing()

        if self.create_user and self.portal_email:
            self.create_student_portal_user()
            self.create_parent_portal_users()

    # ------------------------------------------------------------------
    # Core helper: create or update a Frappe Website User
    # ------------------------------------------------------------------

    def _get_or_create_user(self, email, full_name, role):
        """
        Create a Website User with the given role, or update the existing one.
        Returns (user_doc, is_new).  Password is NOT touched here.
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
            return user, True  # (doc, is_new)

    # ------------------------------------------------------------------
    # Password helper — uses the same path as "Change Password" in User Settings
    # ------------------------------------------------------------------

    def _force_set_password(self, email, password):
        """
        Set a user's password so they can log in immediately — identical to
        the path used by Frappe's own "Change Password" form in User Settings.

        How Frappe's Change Password works:
          1. Calls update_password(user, new_password) in frappe.utils.password
          2. That function hashes via passlibctx and does an INSERT … ON DUPLICATE
             KEY UPDATE directly against __Auth
          3. It also calls clear_sessions() / logout_all_sessions and deletes the
             password-reset key from __Auth

        We replicate steps 1-3 here so the doctype path is 100 % equivalent.
        """
        # Step 1 — official high-level call (hashes + writes __Auth row)
        # logout_all_sessions=False so an admin saving the form doesn't boot
        # any existing session for that user.
        _update_password(email, password, logout_all_sessions=False)

        # Step 2 — explicitly delete any pending reset / one-time-login key
        # so the user is not left in a "must change password" state.
        frappe.db.sql(
            """
            DELETE FROM `__Auth`
            WHERE `doctype` = 'User'
              AND `name`     = %s
              AND `fieldname` IN ('reset_password_key', 'new_password')
            """,
            (email,),
        )

        # Step 3 — flush so the __Auth row is visible before the HTTP response
        # returns (same as frappe.db.commit() at the end of the API handler).
        frappe.db.commit()

    # ------------------------------------------------------------------
    # Student portal user
    # ------------------------------------------------------------------

    def create_student_portal_user(self):
        """Create portal user for student using manual password"""
        if not self.portal_email or not self.portal_password:
            frappe.throw("Both Portal Email and Portal Password are required to create a user.")

        try:
            user, is_new = self._get_or_create_user(
                self.portal_email,
                self.full_name or self.first_name,
                "Student Portal",
            )

            # Set password via the same code-path as User Settings → Change Password
            self._force_set_password(self.portal_email, self.portal_password)

            # Send manual portal credentials email
            try:
                frappe.sendmail(
                    recipients=[self.portal_email],
                    subject="Your School Portal Access",
                    message=(
                        f"<p>Dear {self.full_name or self.first_name},</p>"
                        f"<p>Your portal account has been {'created' if is_new else 'updated'}.</p>"
                        f"<p><b>School:</b> {self.school or 'N/A'}</p>"
                        f"<p><b>Class:</b> {self.student_class or 'N/A'}{' - Section ' + self.section if self.section else ''}</p>"
                        f"<hr>"
                        f"<p><b>Username:</b> {self.portal_email}</p>"
                        f"<p><b>Password:</b> {self.portal_password}</p>"
                        f"<p>Please log in here: <a href=\"{frappe.utils.get_url('/portal-login')}\">"
                        f"{frappe.utils.get_url('/portal-login')}</a></p>"
                        f"<p>Regards,<br>School Administration</p>"
                    ),
                )
            except Exception as e:
                frappe.msgprint(
                    f"⚠️ Credentials email could not be sent (Network/Auth error). "
                    f"However, the portal user has been {'created' if is_new else 'updated'} locally.",
                    indicator="orange",
                    alert=True
                )

            frappe.msgprint(
                f"✅ Student portal user {self.portal_email} "
                f"{'created' if is_new else 'updated'} with manual password. Credentials email sent.",
                indicator="green",
                alert=True,
            )

            self._assign_cost_center_permission(self.portal_email)

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

                # Parents now use the same manual password as the student
                user, is_new = self._get_or_create_user(
                    entry["email"], entry["full_name"], entry["role"]
                )

                # Force sync password to match the student's
                if self.portal_password:
                    self._force_set_password(entry["email"], self.portal_password)

                # Send credentials email (on create or if password might have changed)
                if is_new or self.has_value_changed("portal_password"):
                    frappe.sendmail(
                        recipients=[entry["email"]],
                        subject="Your Parent Portal Access",
                        message=(
                            f"<p>Dear {entry['full_name']},</p>"
                            f"<p>A parent portal account has been {'created' if is_new else 'updated'} for you.</p>"
                            f"<p><b>Student:</b> {self.full_name or self.first_name}</p>"
                            f"<p><b>School:</b> {self.school or 'N/A'}</p>"
                            f"<hr>"
                            f"<p><b>Username:</b> {entry['email']}</p>"
                            f"<p><b>Password:</b> {self.portal_password}</p>"
                            f"<p>Please log in here: <a href=\"{frappe.utils.get_url('/portal-login')}\">"
                            f"{frappe.utils.get_url('/portal-login')}</a></p>"
                            f"<p>Regards,<br>School Administration</p>"
                        ),
                    )
                    frappe.msgprint(
                        f"✅ Parent user {entry['email']} synced. Credentials email sent.",
                        indicator="green",
                        alert=True,
                    )

                self._assign_cost_center_permission(entry["email"])

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



    def _assign_cost_center_permission(self, email):
        """Assign cost center permission to user based on selected school"""
        try:
            if not self.school:
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
            frappe.log_error(f"Failed to assign cost center permission: {str(e)}")
            return False

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

            frappe.msgprint(
                f"✅ Customer {self.full_name} created/updated",
                indicator="green",
                alert=True,
            )

        except Exception:
            frappe.log_error(
                f"Customer creation failed for {self.full_name}",
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

        except Exception:
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

        except Exception:
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

        except Exception:
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