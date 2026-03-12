# Copyright (c) 2026, Ashley and contributors
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
        if not self.invoice:
            frappe.throw("No invoices to pay.")
        company = frappe.defaults.get_global_default("company")
        student = frappe.get_doc("Student", self.student_name)
        company_currency = frappe.db.get_value("Company", company, "default_currency")
        receivable_account = frappe.db.get_value("Company", company, "default_receivable_account")
        paid_to_account = self.account
        paid_to_currency = frappe.db.get_value("Account", paid_to_account, "account_currency") or company_currency
        total_paid = sum(row.allocated or 0 for row in self.invoice)
        pe = frappe.new_doc("Payment Entry")
        pe.payment_type = "Receive"
        pe.party_type = "Customer"
        pe.party = student.full_name
        pe.company = company
        pe.posting_date = self.date or frappe.utils.today()
        pe.paid_from = receivable_account
        pe.paid_to = paid_to_account
        pe.paid_from_account_currency = company_currency
        pe.paid_to_account_currency = paid_to_currency
        pe.source_exchange_rate = 1
        pe.target_exchange_rate = 1
        pe.paid_amount = total_paid
        pe.received_amount = total_paid
        for row in self.invoice:
            if row.invoice_number and (row.allocated or 0) > 0:
                outstanding = frappe.db.get_value("Sales Invoice", row.invoice_number, "outstanding_amount") or row.outstanding
                grand_total = frappe.db.get_value("Sales Invoice", row.invoice_number, "grand_total") or outstanding
                allocated = min(float(row.allocated), float(outstanding), float(grand_total))
                pe.append("references", {
                    "reference_doctype": "Sales Invoice",
                    "reference_name": row.invoice_number,
                    "total_amount": grand_total,
                    "allocated_amount": allocated,
                    "outstanding_amount": outstanding,
                })
        pe.flags.ignore_permissions = True
        pe.flags.ignore_mandatory = True
        pe.flags.ignore_account_permission = True
        pe.flags.ignore_validate_linked_document = True
        frappe.flags.ignore_account_permission = True
        frappe.local.message_log = []
        pe.insert(ignore_permissions=True, ignore_mandatory=True)
        frappe.local.message_log = []
        frappe.db.sql("UPDATE `tabPayment Entry` SET docstatus=1 WHERE name=%s", pe.name)
        frappe.db.commit()

        # Update outstanding amounts on Sales Invoices manually
        total_opening_allocated = 0
        for row in self.invoice:
            if not (row.invoice_number or '').strip() and (row.allocated or 0) > 0:
                total_opening_allocated += row.allocated
            if row.invoice_number and (row.allocated or 0) > 0:
                current_outstanding = frappe.db.get_value("Sales Invoice", row.invoice_number, "outstanding_amount") or 0
                new_outstanding = max(0, float(current_outstanding) - float(row.allocated))
                new_status = "Paid" if new_outstanding == 0 else "Partly Paid"
                frappe.db.sql(
                    "UPDATE `tabSales Invoice` SET outstanding_amount=%s, status=%s WHERE name=%s",
                    (new_outstanding, new_status, row.invoice_number)
                )
        # Update opening balance on student
        if total_opening_allocated > 0:
            current_ob = frappe.db.get_value("Student", self.student_name, "opening_balance") or 0
            new_ob = max(0, float(current_ob) - float(total_opening_allocated))
            frappe.db.sql("UPDATE `tabStudent` SET opening_balance=%s WHERE name=%s", (new_ob, self.student_name))
        frappe.db.commit()
        self.payment_entry = pe.name
        frappe.msgprint(f"Payment Entry {pe.name} created successfully.")
