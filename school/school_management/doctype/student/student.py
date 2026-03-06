import frappe
from frappe.model.document import Document
class Student(Document):
    def before_save(self):
        parts = [self.first_name, self.second_name, self.last_name]
        self.full_name = " ".join([p for p in parts if p])
    def after_insert(self):
        self.create_customer()
    def on_update(self):
        self.create_customer()
    def create_customer(self):
        if not self.full_name:
            return
        if frappe.db.exists("Customer", self.full_name):
            return
        try:
            customer_group = frappe.db.get_single_value("Selling Settings", "customer_group") or "All Customer Groups"
            territory = frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"
            frappe.get_doc({
                "doctype": "Customer",
                "customer_name": self.full_name,
                "customer_type": "Individual",
                "customer_group": customer_group,
                "territory": territory,
            }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(title=f"Customer creation failed for {self.full_name}", message=str(e))
