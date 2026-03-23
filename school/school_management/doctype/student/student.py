import frappe
from frappe.model.document import Document
from frappe.utils import flt

class Student(Document):

    def before_save(self):
        parts = [self.first_name, self.second_name, self.last_name]
        self.full_name = " ".join([p for p in parts if p])

        # Auto-assign admin fees from School Settings defaults based on student_type
        if self.student_type:
            try:
                settings = frappe.get_single("School Settings")
                for row in settings.get("fee_structure_defaults", []):
                    if row.status == self.student_type:
                        self.paying_admin_fee = 1
                        self.admin_fees_structure = row.fees_structure
                        break

                # Auto-check billed_on_registration if enabled in settings
                if settings.enable_registration_billing:
                    for row in settings.get("registration_billing_defaults", []):
                        if row.status == self.student_type:
                            self.fees_structure = row.fees_structure
                            break
            except Exception:
                pass

        if self.student_class:
            class_code = frappe.db.get_value("Student Class", {"name": self.student_class}, "name")
            if not class_code:
                class_code = frappe.db.get_value("Student Class", {"class_name": self.student_class}, "name")
                if class_code:
                    self.student_class = class_code

        if self.get("school"):
            self.cost_center = self.school

        # Auto-generate student_reg_no if empty
        if not self.student_reg_no and self.school:
            self.student_reg_no = self.generate_reg_no()
            self.name = self.student_reg_no

    def generate_reg_no(self):
        # Use full school name before " - " as prefix
        # Extract only alphanumeric chars, uppercase, no spaces
        school_name = self.school or ""
        prefix_raw = school_name.split(" - ")[0].strip()
        prefix = "".join([c for c in prefix_raw if c.isalnum()]).upper()
        if not prefix:
            prefix = "STU"

        # Find the last reg no matching this prefix + 5 digits pattern
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
        # If reg no was not set before insert, generate and update now
        if not self.student_reg_no and self.school:
            reg_no = self.generate_reg_no()
            frappe.db.set_value("Student", self.name, "student_reg_no", reg_no)
            self.student_reg_no = reg_no
        self.create_customer()
        self.create_opening_balance_entry()
        self.create_admin_fee_invoice()
        self.create_registration_billing()

    def on_update(self):
        if self.flags.get("ignore_on_update"):
            return
        self.create_customer()
        self.create_opening_balance_entry()
        self.create_admin_fee_invoice()
        self.create_registration_billing()

    def create_customer(self):
        if not self.full_name:
            return
        try:
            customer_group = frappe.db.get_single_value("Selling Settings", "customer_group") or "All Customer Groups"
            territory = frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"
            if self.student_category:
                customer_group = self.student_category

            # Build customer details summary
            details_parts = []
            if self.student_class:
                details_parts.append("Class: {}".format(self.student_class))
            if self.section:
                details_parts.append("Section: {}".format(self.section))
            if self.school:
                details_parts.append("School: {}".format(self.school))
            if self.student_reg_no:
                details_parts.append("Reg No: {}".format(self.student_reg_no))
            if self.student_type:
                details_parts.append("Type: {}".format(self.student_type))
            customer_details = " | ".join(details_parts)

            existing = frappe.db.exists("Customer", {"customer_name": self.full_name})

            if existing:
                # Update existing customer with latest info
                customer = frappe.get_doc("Customer", existing)
                customer.customer_group = customer_group
                customer.territory = territory
                customer.mobile_no = self.phone_number or customer.mobile_no
                customer.custom_student_section = self.section or ""
                customer.custom_student_class = self.student_class or ""
                customer.custom_school = self.school or ""
                customer.custom_student_reg_no = self.student_reg_no or ""
                customer.custom_student_type = self.student_type or ""
                customer.custom_gender = self.gender or ""
                customer.customer_details = customer_details
                if self.student_image:
                    customer.image = self.student_image
                customer.flags.ignore_permissions = True
                customer.flags.ignore_mandatory = True
                customer.save(ignore_permissions=True)
            else:
                # Create new customer
                customer = frappe.get_doc({
                    "doctype": "Customer",
                    "customer_name": self.full_name,
                    "customer_type": "Individual",
                    "customer_group": customer_group,
                    "territory": territory,
                    "mobile_no": self.phone_number or "",
                    "custom_student_section": self.section or "",
                    "custom_student_class": self.student_class or "",
                    "custom_school": self.school or "",
                    "custom_student_reg_no": self.student_reg_no or "",
                    "custom_student_type": self.student_type or "",
                    "custom_gender": self.gender or "",
                    "customer_details": customer_details,
                    "image": self.student_image or "",
                })
                customer.flags.ignore_permissions = True
                customer.insert(ignore_permissions=True)

        except Exception:
            frappe.log_error(
                title="Customer creation failed for {}".format(self.full_name),
                message=frappe.get_traceback()
            )

    def create_opening_balance_entry(self):
        if not self.has_opening_balance or not self.opening_balance:
            return
        if not self.full_name:
            return
        existing = frappe.db.exists("Journal Entry", {
            "user_remark": "Opening Balance for {}".format(self.full_name),
            "docstatus": 1
        })
        if existing:
            return
        try:
            company = frappe.defaults.get_global_default("company")
            receivable_account = frappe.db.get_value("Company", company, "default_receivable_account")

            # Use Opening Balance Equity account for the credit side
            opening_account = (
                frappe.db.get_value("Account", {
                    "account_type": "Equity",
                    "company": company,
                    "is_group": 0,
                    "account_name": ["like", "%Opening Balance%"]
                }, "name") or
                frappe.db.get_value("Account", {
                    "account_type": "Temporary",
                    "company": company,
                    "is_group": 0
                }, "name") or
                "Opening Balance Equity - SS"
            )

            je = frappe.get_doc({
                "doctype": "Journal Entry",
                "voucher_type": "Opening Entry",
                "posting_date": self.opening_balance_date or frappe.utils.today(),
                "company": company,
                "user_remark": "Opening Balance for {}".format(self.full_name),
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
        except Exception:
            frappe.log_error(
                title="Opening balance JE failed for {}".format(self.full_name),
                message=frappe.get_traceback()
            )


    
    def create_admin_fee_invoice(self):
        # Only run if Paying Admin Fee is checked and a fees structure is selected
        if not self.paying_admin_fee or not self.admin_fees_structure:
            return
        if not self.full_name:
            return

        # Prevent duplicate billing
        existing_billing = frappe.db.exists("Billing", {
            "student": self.name,
            "fees_structure": self.admin_fees_structure,
            "docstatus": ["!=", 2]
        })
        if existing_billing:
            if self.admin_fee_paid:
                # Get the sales invoice created by this billing
                inv = frappe.db.get_value("Sales Invoice", {
                    "customer": self.full_name,
                    "fees_structure": self.admin_fees_structure,
                    "docstatus": ["!=", 2]
                }, "name")
                if inv:
                    self.create_admin_fee_receipting(inv)
            return

        try:
            company = frappe.defaults.get_global_default("company")

            # Ensure customer exists
            if not frappe.db.exists("Customer", {"customer_name": self.full_name}):
                self.create_customer()

            # Get fees structure items
            fees_doc = frappe.get_doc("Fees Structure", self.admin_fees_structure)
            if not fees_doc.fees_items:
                frappe.log_error(
                    title="create_admin_fee_invoice",
                    message="Fees Structure {} has no items".format(self.admin_fees_structure)
                )
                return

            # Create Billing doc — it will create Sales Invoice on submit
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
            billing.flags.ignore_mandatory = True
            billing.insert(ignore_permissions=True)
            billing.submit()

            frappe.db.commit()

            # Get the sales invoice created by billing submit
            invoice_name = frappe.db.get_value("Sales Invoice", {
                "customer": self.full_name,
                "fees_structure": self.admin_fees_structure,
                "docstatus": ["!=", 2]
            }, "name")

            # If Paid is also checked, create receipting immediately
            if self.admin_fee_paid and invoice_name:
                self.create_admin_fee_receipting(invoice_name)

        except Exception:
            frappe.log_error(
                title="Admin fee billing failed for {}".format(self.full_name),
                message=frappe.get_traceback()
            )

    def create_admin_fee_receipting(self, invoice_name):
        if not invoice_name:
            return

        # Prevent duplicate receipting
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

            # Use account selected on Student form
            account = self.account
            if not account:
                frappe.log_error(
                    title="create_admin_fee_receipting",
                    message="No account selected on Student {}".format(self.name)
                )
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
            receipt.flags.ignore_mandatory = True
            receipt.insert(ignore_permissions=True)
            receipt.submit()

            frappe.db.commit()

        except Exception:
            frappe.log_error(
                title="Admin fee receipting failed for {}".format(self.full_name),
                message=frappe.get_traceback()
            )



    
    
    
    
    
    def create_registration_billing(self):
        """Create a billing document when student is first created based on student_type"""
        
        if hasattr(self, 'billed_on_registration') and self.billed_on_registration:
            return
        
        try:
            settings = frappe.get_single("School Settings")
            
            if not self.student_type:
                return
            
            # Get fees structure from registration_billing table
            fees_structure = None
            for row in settings.get("registration_billing", []):
                if row.status == self.student_type:
                    fees_structure = row.billing
                    break
            
            if not fees_structure:
                return
            
            # Create billing document
            billing = frappe.new_doc("Billing")
            billing.student = self.name
            billing.student_class = self.student_class
            billing.section = self.section
            billing.date = frappe.utils.today()
            billing.fees_structure = fees_structure
            
            # Add items from fees structure
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
            
            # Save and submit
            billing.flags.ignore_permissions = True
            billing.insert(ignore_permissions=True)
            billing.submit()
            
            # Mark as billed
            frappe.db.set_value("Student", self.name, "billed_on_registration", 1)
            self.billed_on_registration = 1
            
        except Exception as e:
            frappe.log_error(
                title="Registration Billing Error",
                message="Student: " + self.name + " Error: " + str(e)
            )

@frappe.whitelist()
def generate_reg_no_for_school(school, current_student=None):
    """Generate next student reg no for a given school (cost center)."""
    prefix_raw = school.split(" - ")[0].strip()
    prefix = "".join([c for c in prefix_raw if c.isalnum()]).upper()
    if not prefix:
        prefix = "STU"

    # Exclude current student if editing
    exclude_clause = ""
    params = ["^" + prefix + "[0-9]{5}$", len(prefix) + 1]
    if current_student:
        exclude_clause = "AND name != %s"
        params.append(current_student)

    last = frappe.db.sql("""
        SELECT student_reg_no FROM `tabStudent`
        WHERE student_reg_no REGEXP %s
        {exclude}
        ORDER BY CAST(SUBSTRING(student_reg_no, %s) AS UNSIGNED) DESC
        LIMIT 1
    """.format(exclude=exclude_clause), params, as_dict=True)

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
