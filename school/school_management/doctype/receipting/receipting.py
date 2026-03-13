import frappe
from frappe.model.document import Document
from frappe.utils import flt, today

class Receipting(Document):

    def validate(self):
        self.calculate_totals()

    def calculate_totals(self):
        total_outstanding = 0
        total_allocated = 0
        for row in self.invoice:
            total_outstanding += flt(row.outstanding)
            total_allocated += flt(row.allocated)
        self.total_outstanding = total_outstanding
        self.total_allocated = total_allocated
        self.total_balance = total_outstanding - total_allocated

    def on_submit(self):
        if flt(self.total_allocated) <= 0:
            frappe.throw("Allocation amount must be greater than 0.")
        self.create_payment_entry()

    def create_payment_entry(self):
        student_full_name = frappe.db.get_value("Student", self.student_name, "full_name")
        company = frappe.defaults.get_global_default("company") or frappe.get_all("Company")[0].name

        pe = frappe.new_doc("Payment Entry")
        pe.payment_type = "Receive"
        pe.party_type = "Customer"
        pe.party = student_full_name
        pe.company = company
        pe.posting_date = self.date or today()
        pe.paid_to = self.account
        pe.paid_amount = self.total_allocated
        pe.received_amount = self.total_allocated

        for row in self.invoice:
            if row.invoice_number and flt(row.allocated) > 0:
                pe.append("references", {
                    "reference_doctype": "Sales Invoice",
                    "reference_name": row.invoice_number,
                    "allocated_amount": row.allocated
                })

        pe.insert(ignore_permissions=True)
        pe.submit()

        self.db_set("payment_entry", pe.name)

        for row in self.invoice:
            if not row.invoice_number and row.fees_structure == "Opening Balance":
                current_ob = frappe.db.get_value("Student", self.student_name, "opening_balance")
                new_ob = flt(current_ob) - flt(row.allocated)
                frappe.db.set_value("Student", self.student_name, "opening_balance", new_ob)