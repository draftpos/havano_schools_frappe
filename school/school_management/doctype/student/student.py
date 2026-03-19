import frappe
from frappe.model.document import Document

class Student(Document):

    def before_save(self):
        parts = [self.first_name, self.second_name, self.last_name]
        self.full_name = " ".join([p for p in parts if p])

        if self.student_class:
            class_code = frappe.db.get_value("Student Class", {"name": self.student_class}, "name")
            if not class_code:
                class_code = frappe.db.get_value("Student Class", {"class_name": self.student_class}, "name")
                if class_code:
                    self.student_class = class_code

        # Sync school selection to cost_center
        if self.get("school"):
            self.cost_center = self.school

    def after_insert(self):
        self.create_customer()
        self.create_opening_balance_entry()

    def on_update(self):
        if self.flags.get("ignore_on_update"):
            return
        self.create_customer()
        self.create_opening_balance_entry()

    def create_customer(self):
        if not self.full_name:
            return

        if frappe.db.exists("Customer", {"customer_name": self.full_name}):
            return

        try:
            customer_group = frappe.db.get_single_value("Selling Settings", "customer_group") or "All Customer Groups"
            territory = frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"

            if self.student_category:
                customer_group = self.student_category

            customer = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": self.full_name,
                "customer_type": "Individual",
                "customer_group": customer_group,
                "territory": territory,
            })

            customer.insert(ignore_permissions=True)

        except Exception:
            frappe.log_error(
                title=f"Customer creation failed for {self.full_name}",
                message=frappe.get_traceback()
            )

    def create_opening_balance_entry(self):
        if not self.has_opening_balance or not self.opening_balance:
            return
        if not self.full_name:
            return

        # Avoid duplicate journal entries
        existing = frappe.db.exists("Journal Entry", {
            "user_remark": "Opening Balance for {}".format(self.full_name),
            "docstatus": 1
        })
        if existing:
            return

        try:
            company = frappe.defaults.get_global_default("company")
            receivable_account = frappe.db.get_value(
                "Company", company, "default_receivable_account"
            )
            opening_account = frappe.db.get_value(
                "Company", company, "default_payable_account"
            ) or "Temporary Opening - SS"

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

