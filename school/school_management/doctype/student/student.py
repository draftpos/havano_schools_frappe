import frappe
from frappe.model.document import Document
from frappe.utils import flt

class Student(Document):
    
    def validate(self):
        """Validate before save - set full name"""
        parts = [self.first_name, self.second_name, self.last_name]
        self.full_name = " ".join([p for p in parts if p])
        
        # Validate student type
        if self.student_type:
            meta = frappe.get_meta(self.doctype)
            options = [opt.strip() for opt in (meta.get_field("student_type").options or "").split("\n") if opt.strip()]
            if self.student_type not in options:
                frappe.throw(f"Student Type must be one of: {', '.join(options)}. Got: {self.student_type}")
    
    def before_save(self):
        """Before save - generate dummy email if needed"""
        settings = frappe.get_single("School Settings")
        if settings.allow_non_strict_email and self.create_user and not self.portal_email:
            name_part = self.full_name.lower().replace(" ", ".") if self.full_name else self.name
            self.portal_email = f"{name_part}@dummy.school"
            frappe.msgprint(f"Dummy portal email generated: {self.portal_email}", indicator="blue")
    
    def generate_reg_no(self):
        school_name = self.school or ""
        prefix_raw = school_name.split(" - ")[0].strip()
        prefix = "".join([c for c in prefix_raw if c.isalnum()]).upper()
        if not prefix:
            prefix = "STU"

        last = frappe.db.sql("""
            SELECT student_reg_no FROM `tabStudent`
            WHERE student_reg_no REGEXP %s
            ORDER BY CAST(SUBSTRING(student_reg_no, %s) AS UNSIGNED) DESC
            LIMIT 1
        """, ("^" + prefix + "[0-9]{5}$", len(prefix) + 1), as_dict=True)

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
        """After insert - generate registration number and create user"""
        if not self.student_reg_no and self.school:
            reg_no = self.generate_reg_no()
            frappe.db.set_value("Student", self.name, "student_reg_no", reg_no)
            self.student_reg_no = reg_no
        
        # Create user IMMEDIATELY
        self.create_all_records()
    
    def on_update(self):
        """On update - create all records"""
        if self.flags.get("ignore_on_update"):
            return
        self.create_all_records()
    
    def create_all_records(self):
        """Create all records including user"""
        # Create customer
        self.create_customer()
        
        # Create portal user if checked
        if self.create_user and self.portal_email:
            self.create_user_account()
        
        # Create other records
        self.create_opening_balance_entry()
        self.create_admin_fee_invoice()
        self.create_registration_billing()
    
    def create_user_account(self):
        """SIMPLIFIED - Create user account directly"""
        try:
            email = self.portal_email
            first_name = self.first_name or "Student"
            last_name = self.last_name or ""
            
            frappe.msgprint(f"Creating user: {email}", indicator="blue", alert=True)
            
            # Check if user exists
            if frappe.db.exists("User", email):
                user = frappe.get_doc("User", email)
                user.enabled = 1
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
                user.insert(ignore_permissions=True)
                frappe.msgprint(f"User {email} created successfully", indicator="green", alert=True)
                
                # Set password if provided
                settings = frappe.get_single("School Settings")
                if settings.allow_non_strict_email and hasattr(self, 'portal_password') and self.portal_password:
                    user.new_password = self.portal_password
                    user.save(ignore_permissions=True)
                    frappe.msgprint(f"Password set for {email}", indicator="green", alert=True)
                else:
                    # Send password reset link
                    reset_key = user.reset_password()
                    frappe.sendmail(
                        recipients=[email],
                        subject="Your School Portal Access",
                        message=f"""<p>Dear {first_name},</p>
<p>Your portal account has been created.</p>
<p>Email: {email}</p>
<p>Click here to set your password: {frappe.utils.get_url()}/update-password?key={reset_key}</p>"""
                    )
                    frappe.msgprint(f"Password reset email sent to {email}", indicator="green", alert=True)
            
            # Assign cost center permission
            if self.school:
                self.assign_cost_center_permission(email)
            
            frappe.db.commit()
            
        except Exception as e:
            frappe.log_error(f"User creation failed: {str(e)}", "Student User Creation")
            frappe.msgprint(f"Error creating user: {str(e)}", indicator="red", alert=True)
    
    def assign_cost_center_permission(self, email):
        """Assign cost center permission"""
        try:
            # Check if permission already exists
            if not frappe.db.exists("User Permission", {
                "user": email,
                "allow": "Cost Center",
                "for_value": self.school
            }):
                permission = frappe.get_doc({
                    "doctype": "User Permission",
                    "user": email,
                    "allow": "Cost Center",
                    "for_value": self.school,
                    "applicable_for": "Cost Center"
                })
                permission.insert(ignore_permissions=True)
                frappe.msgprint(f"Cost center permission assigned for {email}", indicator="green", alert=True)
        except Exception as e:
            frappe.log_error(f"Cost center permission failed: {str(e)}", "Permission Error")
    
    def create_customer(self):
        """Create or update customer"""
        if not self.full_name:
            return
        
        try:
            customer_group = frappe.db.get_single_value("Selling Settings", "customer_group") or "All Customer Groups"
            territory = frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"
            
            if self.student_category:
                customer_group = self.student_category
            
            existing = frappe.db.exists("Customer", {"customer_name": self.full_name})
            
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
                    "custom_student_type": self.student_type or ""
                })
                customer.insert(ignore_permissions=True)
            
            frappe.msgprint(f"Customer {self.full_name} created/updated", indicator="green", alert=True)
            
        except Exception as e:
            frappe.log_error(f"Customer creation failed: {str(e)}", "Customer Error")
    
    def create_opening_balance_entry(self):
        """Create opening balance journal entry"""
        if not self.has_opening_balance or not self.opening_balance:
            return
        
        if not self.full_name:
            return
        
        existing = frappe.db.exists("Journal Entry", {
            "user_remark": f"Opening Balance for {self.full_name}",
            "docstatus": 1
        })
        
        if existing:
            return
        
        try:
            company = frappe.defaults.get_global_default("company")
            receivable_account = frappe.db.get_value("Company", company, "default_receivable_account")
            
            opening_account = frappe.db.get_value("Account", {
                "account_type": "Equity",
                "company": company,
                "is_group": 0
            }, "name") or "Opening Balance Equity - SS"
            
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
                    }
                ]
            })
            je.flags.ignore_permissions = True
            je.insert()
            je.submit()
            
            frappe.msgprint(f"Opening balance entry created for {self.full_name}", indicator="green", alert=True)
            
        except Exception as e:
            frappe.log_error(f"Opening balance failed: {str(e)}", "Opening Balance Error")
    
    def create_admin_fee_invoice(self):
        """Create admin fee invoice"""
        if not self.paying_admin_fee or not self.admin_fees_structure:
            return
        
        if not self.full_name:
            return
        
        try:
            # Check if customer exists
            if not frappe.db.exists("Customer", {"customer_name": self.full_name}):
                self.create_customer()
            
            # Get fees structure
            fees_doc = frappe.get_doc("Fees Structure", self.admin_fees_structure)
            if not fees_doc.fees_items:
                return
            
            # Check if billing already exists
            existing_billing = frappe.db.exists("Billing", {
                "student": self.name,
                "fees_structure": self.admin_fees_structure,
                "docstatus": ["!=", 2]
            })
            
            if existing_billing:
                if self.admin_fee_paid:
                    inv = frappe.db.get_value("Sales Invoice", {
                        "customer": self.full_name,
                        "fees_structure": self.admin_fees_structure,
                        "docstatus": ["!=", 2]
                    }, "name")
                    if inv:
                        self.create_admin_fee_receipting(inv)
                return
            
            # Create billing
            billing = frappe.new_doc("Billing")
            billing.date = frappe.utils.today()
            billing.cost_center = self.cost_center or self.school
            billing.fees_structure = self.admin_fees_structure
            billing.student = self.name
            billing.student_class = self.student_class
            billing.section = self.section
            
            for item in fees_doc.fees_items:
                billing.append("items", {
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "qty": 1,
                    "rate": item.rate or 0,
                    "amount": flt(item.rate or 0),
                    "cost_center": self.cost_center or self.school,
                })
            
            billing.flags.ignore_permissions = True
            billing.insert(ignore_permissions=True)
            billing.submit()
            
            frappe.db.commit()
            
            # Create receipt if paid
            if self.admin_fee_paid:
                invoice_name = frappe.db.get_value("Sales Invoice", {
                    "customer": self.full_name,
                    "fees_structure": self.admin_fees_structure,
                    "docstatus": ["!=", 2]
                }, "name")
                if invoice_name:
                    self.create_admin_fee_receipting(invoice_name)
            
            frappe.msgprint(f"Admin fee invoice created for {self.full_name}", indicator="green", alert=True)
            
        except Exception as e:
            frappe.log_error(f"Admin fee invoice failed: {str(e)}", "Invoice Error")
    
    def create_admin_fee_receipting(self, invoice_name):
        """Create receipt for admin fee"""
        if not invoice_name:
            return
        
        existing = frappe.db.exists("Receipting", {
            "student_name": self.name,
            "docstatus": ["!=", 2]
        })
        
        if existing:
            return
        
        try:
            outstanding = frappe.db.get_value("Sales Invoice", invoice_name, "outstanding_amount")
            if not flt(outstanding) > 0:
                return
            
            account = self.account
            if not account:
                return
            
            receipt = frappe.new_doc("Receipting")
            receipt.student_name = self.name
            receipt.student_class = self.student_class
            receipt.section = self.section
            receipt.date = frappe.utils.today()
            receipt.account = account
            
            receipt.append("invoice", {
                "invoice_number": invoice_name,
                "outstanding": flt(outstanding),
                "allocated": flt(outstanding),
                "fees_structure": self.admin_fees_structure,
            })
            
            receipt.flags.ignore_permissions = True
            receipt.insert(ignore_permissions=True)
            receipt.submit()
            
            frappe.db.commit()
            frappe.msgprint(f"Admin fee receipt created for {self.full_name}", indicator="green", alert=True)
            
        except Exception as e:
            frappe.log_error(f"Admin fee receipting failed: {str(e)}", "Receipt Error")
    
    def create_registration_billing(self):
        """Create registration billing"""
        if hasattr(self, 'billed_on_registration') and self.billed_on_registration:
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
            
            if fees_structure:
                fs_doc = frappe.get_doc("Fees Structure", fees_structure)
                if fs_doc.get("fees_items"):
                    for item in fs_doc.get("fees_items", []):
                        billing.append("items", {
                            "item_code": item.item_code,
                            "item_name": item.item_name,
                            "qty": 1,
                            "rate": item.rate or 0,
                            "amount": flt(item.rate or 0),
                            "cost_center": self.cost_center or self.school,
                        })
            
            billing.flags.ignore_permissions = True
            billing.insert(ignore_permissions=True)
            billing.submit()
            
            frappe.db.set_value("Student", self.name, "billed_on_registration", 1)
            self.billed_on_registration = 1
            
            frappe.msgprint(f"Registration billing created for {self.full_name}", indicator="green", alert=True)
            
        except Exception as e:
            frappe.log_error("Registration Billing Error", f"Student: {self.name} Error: {str(e)}")


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
        fields=["class_name", "section"]
    )
    
    if not assigned:
        return "1=0"
    
    conditions = []
    for row in assigned:
        if row.class_name and row.section:
            conditions.append(
                f"(`tabStudent`.`student_class` = {frappe.db.escape(row.class_name)} AND `tabStudent`.`section` = {frappe.db.escape(row.section)})"
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
    
    last = frappe.db.sql(f"""
        SELECT student_reg_no FROM `tabStudent`
        WHERE student_reg_no REGEXP %s
        {exclude_clause}
        ORDER BY CAST(SUBSTRING(student_reg_no, %s) AS UNSIGNED) DESC
        LIMIT 1
    """, params, as_dict=True)
    
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