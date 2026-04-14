import frappe
from frappe.model.document import Document
from frappe.utils import flt
from frappe.utils.password import update_password


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
        # Generate dummy email only if non-strict email is enabled AND no portal email provided
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

        # Create all linked records immediately after insert
        self._create_all_users_and_records()

    def on_update(self):
        """On update - create/update all records only when relevant fields change"""
        if self.flags.get("ignore_on_update"):
            return

        # Only re-run user creation if email or create_user flag changed
        user_fields_changed = self.has_value_changed("create_user") or self.has_value_changed(
            "portal_email"
        )

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

    def create_student_portal_user(self):
        """Create portal user for student"""
        settings = frappe.get_single("School Settings")

        if (
            settings.allow_non_strict_email
            and hasattr(self, "portal_password")
            and self.portal_password
        ):
            success = self._create_user_with_password(
                self.portal_email,
                self.full_name or self.first_name,
                "Student Portal",
                self.portal_password,
            )
            if success:
                frappe.msgprint(
                    f"✅ Student user {self.portal_email} created with password",
                    indicator="green",
                    alert=True,
                )
        else:
            success = self._create_user_and_send_invite(
                self.portal_email,
                self.full_name or self.first_name,
                "Student Portal",
            )
            if success:
                frappe.msgprint(
                    f"✅ Student user {self.portal_email} created. Invitation sent.",
                    indicator="green",
                    alert=True,
                )

    def create_parent_portal_users(self):
        """Create portal users for parents"""
        parent_entries = []

        if self.father_email:
            parent_entries.append(
                {
                    "email": self.father_email,
                    "full_name": self.father_name or "Parent",
                    "role": "Parent",
                }
            )

        if self.mother_email and self.mother_email != self.father_email:
            parent_entries.append(
                {
                    "email": self.mother_email,
                    "full_name": self.mother_name or "Parent",
                    "role": "Parent",
                }
            )

        if self.guardian_email and self.guardian_email not in [
            self.father_email,
            self.mother_email,
        ]:
            parent_entries.append(
                {
                    "email": self.guardian_email,
                    "full_name": self.guardian_name or "Guardian",
                    "role": "Parent",
                }
            )

        for entry in parent_entries:
            existing_parent = frappe.db.exists("Parent", {"portal_email": entry["email"]})

            if existing_parent:
                parent_doc = frappe.get_doc("Parent", existing_parent)
                already_linked = any(
                    row.student == self.name for row in parent_doc.get("children", [])
                )
                if not already_linked:
                    parent_doc.append("children", {"student": self.name})
                    parent_doc.flags.ignore_permissions = True
                    parent_doc.save(ignore_permissions=True)
                    frappe.msgprint(
                        f"Student linked to existing parent account: {entry['email']}",
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

            self._create_user_and_send_invite(
                entry["email"], entry["full_name"], "Parent"
            )

    def _create_user_with_password(self, email, full_name, role, password):
        """Create user with a specific password using Frappe's update_password utility"""
        try:
            if frappe.db.exists("User", email):
                user = frappe.get_doc("User", email)
                roles = [r.role for r in user.roles]
                if role not in roles:
                    user.append("roles", {"role": role})
                user.enabled = 1
                user.flags.ignore_permissions = True
                user.flags.ignore_password_policy = True
                user.save(ignore_permissions=True)
                frappe.msgprint(
                    f"✅ User {email} updated", indicator="green", alert=True
                )
            else:
                user = frappe.get_doc(
                    {
                        "doctype": "User",
                        "email": email,
                        "first_name": (
                            full_name.split()[0] if full_name else email.split("@")[0]
                        ),
                        "last_name": (
                            " ".join(full_name.split()[1:])
                            if full_name and len(full_name.split()) > 1
                            else ""
                        ),
                        "enabled": 1,
                        "user_type": "Website User",
                        "send_welcome_email": 0,
                        "roles": [{"role": role}],
                    }
                )
                user.flags.ignore_permissions = True
                user.flags.ignore_password_policy = True
                user.insert(ignore_permissions=True)
                frappe.msgprint(
                    f"✅ User {email} created", indicator="green", alert=True
                )

            # ✅ Correct Frappe way to set/update a user password
            update_password(email, password)

            self._assign_cost_center_permission(email)
            return True

        except Exception as e:
            frappe.log_error(f"User creation failed for {email}", frappe.get_traceback())
            frappe.msgprint(
                f"❌ Error creating user {email}: {str(e)}", indicator="red", alert=True
            )
            return False

    def _create_user_and_send_invite(self, email, full_name, role):
        """Create user and send password reset invite"""
        try:
            if frappe.db.exists("User", email):
                user = frappe.get_doc("User", email)
                roles = [r.role for r in user.roles]
                if role not in roles:
                    user.append("roles", {"role": role})
                user.enabled = 1
                user.flags.ignore_permissions = True
                user.save(ignore_permissions=True)
                frappe.msgprint(
                    f"✅ User {email} already exists, role assigned",
                    indicator="green",
                    alert=True,
                )
            else:
                user = frappe.get_doc(
                    {
                        "doctype": "User",
                        "email": email,
                        "first_name": (
                            full_name.split()[0] if full_name else email.split("@")[0]
                        ),
                        "last_name": (
                            " ".join(full_name.split()[1:])
                            if full_name and len(full_name.split()) > 1
                            else ""
                        ),
                        "enabled": 1,
                        "user_type": "Website User",
                        "send_welcome_email": 0,
                        "roles": [{"role": role}],
                    }
                )
                user.flags.ignore_permissions = True
                user.insert(ignore_permissions=True)

                # Send password reset / welcome email
                reset_key = user.reset_password()
                frappe.sendmail(
                    recipients=[email],
                    subject="Your School Portal Access",
                    message=f"""<p>Dear {full_name},</p>
<p>Your portal account has been created.</p>
<p>Email: {email}</p>
<p>Please click below to set your password:</p>
<p><a href="{frappe.utils.get_url()}/update-password?key={reset_key}">Set Password &amp; Login</a></p>
<p>Regards,<br>School Administration</p>""",
                )

                frappe.msgprint(
                    f"✅ User {email} created. Invitation sent to email.",
                    indicator="green",
                    alert=True,
                )

            self._assign_cost_center_permission(email)
            return True

        except Exception as e:
            frappe.log_error(f"User creation failed for {email}", frappe.get_traceback())
            frappe.msgprint(
                f"❌ Error creating user {email}: {str(e)}", indicator="red", alert=True
            )
            return False

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
                user_permission = frappe.get_doc(
                    {
                        "doctype": "User Permission",
                        "user": email,
                        "allow": "Cost Center",
                        "for_value": self.school,
                        # ✅ Leave blank so permission applies across all doctypes,
                        #    not just within the Cost Center doctype itself.
                        "applicable_for": "",
                    }
                )
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
                    "Customer", {"custom_student_reg_no": self.student_reg_no}, "name"
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
                customer = frappe.get_doc(
                    {
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
                    }
                )
                customer.flags.ignore_permissions = True
                customer.insert(ignore_permissions=True)

            frappe.msgprint(
                f"✅ Customer {self.full_name} created/updated",
                indicator="green",
                alert=True,
            )

        except Exception:
            frappe.log_error(
                f"Customer creation failed for {self.full_name}", frappe.get_traceback()
            )

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
                    {"account_type": "Temporary", "company": company, "is_group": 0},
                    "name",
                )
                or "Opening Balance Equity - SS"
            )

            je = frappe.get_doc(
                {
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
                }
            )
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
                f"Opening balance JE failed for {self.full_name}", frappe.get_traceback()
            )

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
                f"Admin fee billing failed for {self.full_name}", frappe.get_traceback()
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