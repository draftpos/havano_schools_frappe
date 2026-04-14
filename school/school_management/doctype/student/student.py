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

    def before_save(self):
        """Before save - generate dummy email if needed"""
        settings = frappe.get_single("School Settings")
        # ONLY generate dummy email if non-strict email is DISABLED
        if not settings.allow_non_strict_email and self.create_user and not self.portal_email:
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
        """On update - create all records"""
        if self.flags.get("ignore_on_update"):
            return

        self._create_all_users_and_records()

    def _create_all_users_and_records(self):
        """Central method to create all users and records"""
        # Create customer
        self.create_customer()
        
        # Create opening balance entry
        self.create_opening_balance_entry()
        
        # Create admin fee invoice
        self.create_admin_fee_invoice()
        
        # Create registration billing
        self.create_registration_billing()

        # Create portal user if checked
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
    # Student portal user with CORRECT password logic
    # ------------------------------------------------------------------

    def create_student_portal_user(self):
        """Create portal user for student with correct password logic"""
        settings = frappe.get_single("School Settings")
        
        # Get password from form (if user entered one)
        user_provided_password = self.get('portal_password')
        
        email = self.portal_email
        first_name = self.first_name or "Student"
        last_name = self.last_name or ""
        full_name = self.full_name or first_name
        
        frappe.msgprint(f"Creating user: {email}", indicator="blue", alert=True)
        
        try:
            # Check if user exists
            if frappe.db.exists("User", email):
                user = frappe.get_doc("User", email)
                # Add role if not present
                roles = [r.role for r in user.roles]
                if "Student Portal" not in roles:
                    user.append("roles", {"role": "Student Portal"})
                user.enabled = 1
                user.user_type = "Website User"
                user.flags.ignore_permissions = True
                user.save(ignore_permissions=True)
                frappe.msgprint(f"User {email} already exists and enabled", indicator="green", alert=True)
            else:
                # Create new user
                user = frappe.get_doc({
                    "doctype": "User",
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "enabled": 1,
                    "user_type": "Website User",
                    "send_welcome_email": 0,
                    "roles": [{"role": "Student Portal"}]
                })
                user.flags.ignore_permissions = True
                user.insert(ignore_permissions=True)
                frappe.msgprint(f"User {email} created successfully", indicator="green", alert=True)
            
            # CRITICAL: Password logic based on allow_non_strict_email setting
            if settings.allow_non_strict_email:
                # When checkbox is CHECKED: Use user-provided password
                if user_provided_password:
                    frappe.msgprint(f"Setting user-provided password for {email}", indicator="blue", alert=True)
                    _update_password(email, user_provided_password, logout_all_sessions=True)
                    frappe.db.commit()
                    frappe.msgprint(f"✅ Password set for {email}", indicator="green", alert=True)
                    
                    # Test the login
                    from frappe.utils.password import check_password
                    try:
                        check_password(email, user_provided_password)
                        frappe.msgprint(f"✅ Login test PASSED for {email}", indicator="green", alert=True)
                    except Exception as e:
                        frappe.msgprint(f"⚠️ Please test login manually: {str(e)}", indicator="orange", alert=True)
                else:
                    # No password provided - send reset link
                    frappe.msgprint(f"No password provided, sending reset link to {email}", indicator="blue", alert=True)
                    reset_key = user.reset_password()
                    frappe.sendmail(
                        recipients=[email],
                        subject="Your School Portal Access",
                        message=f"""<p>Dear {full_name},</p>
<p>Your student portal account has been created.</p>
<p>Email: {email}</p>
<p>Click below to set your password:</p>
<p><a href="{frappe.utils.get_url()}/update-password?key={reset_key}">Set Password & Login</a></p>
<p>Regards,<br>School Administration</p>"""
                    )
                    frappe.msgprint(f"✅ Password reset email sent to {email}", indicator="green", alert=True)
            else:
                # When checkbox is UNCHECKED: Auto-generate password and send reset link
                frappe.msgprint(f"Auto-generating password for {email}", indicator="blue", alert=True)
                reset_key = user.reset_password()
                frappe.sendmail(
                    recipients=[email],
                    subject="Your School Portal Access",
                    message=f"""<p>Dear {full_name},</p>
<p>Your student portal account has been created.</p>
<p>Email: {email}</p>
<p>Click below to set your password:</p>
<p><a href="{frappe.utils.get_url()}/update-password?key={reset_key}">Set Password & Login</a></p>
<p>Regards,<br>School Administration</p>"""
                )
                frappe.msgprint(f"✅ Password reset email sent to {email}", indicator="green", alert=True)

            # Assign permissions
            self._assign_cost_center_permission(email)
            self._assign_user_to_student(email)

        except Exception as e:
            frappe.log_error(f"Student portal user creation failed: {str(e)}", "Student User Creation")
            frappe.msgprint(f"❌ Error creating user: {str(e)}", indicator="red", alert=True)

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
                frappe.msgprint(f"✅ User {email} linked to student {self.name}", indicator="green", alert=True)
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

                # Create user for parent (always send reset link)
                self._create_parent_user(entry["email"], entry["full_name"])

            except Exception as e:
                frappe.log_error(
                    f"Parent user creation failed for {entry['email']}",
                    frappe.get_traceback(),
                )

    def _create_parent_user(self, email, full_name):
        """Create parent user"""
        try:
            if frappe.db.exists("User", email):
                user = frappe.get_doc("User", email)
                roles = [r.role for r in user.roles]
                if "Parent" not in roles:
                    user.append("roles", {"role": "Parent"})
                user.enabled = 1
                user.save(ignore_permissions=True)
            else:
                user = frappe.get_doc({
                    "doctype": "User",
                    "email": email,
                    "first_name": full_name,
                    "enabled": 1,
                    "user_type": "Website User",
                    "send_welcome_email": 0,
                    "roles": [{"role": "Parent"}]
                })
                user.flags.ignore_permissions = True
                user.insert(ignore_permissions=True)
                
                # Send password reset email
                reset_key = user.reset_password()
                frappe.sendmail(
                    recipients=[email],
                    subject="Your School Portal Access",
                    message=f"""<p>Dear {full_name},</p>
<p>A parent portal account has been created for you.</p>
<p>Email: {email}</p>
<p>Click below to set your password:</p>
<p><a href="{frappe.utils.get_url()}/update-password?key={reset_key}">Set Password & Login</a></p>
<p>Regards,<br>School Administration</p>"""
                )
            
            self._assign_cost_center_permission(email)
            frappe.msgprint(f"✅ Parent user {email} created", indicator="green", alert=True)
            
        except Exception as e:
            frappe.log_error(f"Parent user creation failed: {str(e)}", "Parent User Error")

    # ------------------------------------------------------------------
    # Permission helpers
    # ------------------------------------------------------------------

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

            return True

        except Exception as e:
            frappe.log_error(
                f"Cost center permission assignment failed for {email}",
                frappe.get_traceback(),
            )
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

        except Exception as e:
            frappe.log_error(
                f"Customer creation failed for {self.full_name}",
                frappe.get_traceback(),
            )

    # ------------------------------------------------------------------
    # Opening balance (keep your existing implementation)
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
    # Admin fee invoice + receipt (keep your existing implementation)
    # ------------------------------------------------------------------

    def create_admin_fee_invoice(self):
        """Create admin fee invoice"""
        if not self.paying_admin_fee or not self.admin_fees_structure:
            return
        # Add your existing implementation

    def create_admin_fee_receipting(self, invoice_name):
        """Create receipt for admin fee"""
        # Add your existing implementation

    # ------------------------------------------------------------------
    # Registration billing (keep your existing implementation)
    # ------------------------------------------------------------------

    def create_registration_billing(self):
        """Create registration billing based on student type"""
        if hasattr(self, "billed_on_registration") and self.billed_on_registration:
            return
        # Add your existing implementation


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