# Copyright (c) 2026, Ashley and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document

class Receipting(Document):
    def validate(self):
        self.calculate_totals()

    def calculate_totals(self):
        total_outstanding = 0
        total_allocated = 0
        for row in self.invoice:
            total_outstanding += row.outstanding or 0
            total_allocated += row.allocated or 0
        self.total_outstanding = total_outstanding
        self.total_allocated = total_allocated
        self.total_balance = total_outstanding - total_allocated

    def on_submit(self):
        self.create_payment_entry()

    def create_payment_entry(self):
        if not self.invoice:
            frappe.throw("No invoices to pay.")

        company = frappe.defaults.get_global_default("company")
        student = frappe.get_doc("Student", self.student_name)

        pe = frappe.new_doc("Payment Entry")
        pe.payment_type = "Receive"
        pe.party_type = "Customer"
        pe.party = student.full_name
        pe.company = company
        pe.posting_date = self.date or frappe.utils.today()
        pe.paid_to = self.account
        pe.paid_amount = sum(row.allocated or 0 for row in self.invoice)
        pe.received_amount = pe.paid_amount
        pe.target_exchange_rate = 1

        for row in self.invoice:
            if row.invoice_number and (row.allocated or 0) > 0:
                pe.append("references", {
                    "reference_doctype": "Sales Invoice",
                    "reference_name": row.invoice_number,
                    "allocated_amount": row.allocated,
                    "outstanding_amount": row.outstanding,
                })

        pe.flags.ignore_permissions = True
        pe.flags.ignore_validate = True
        pe.insert()
        pe.submit()
        self.payment_entry = pe.name
        frappe.msgprint(f"Payment Entry {pe.name} created successfully.")
