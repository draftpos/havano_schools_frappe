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
        # Prevent duplicate payment entries
        existing = frappe.get_all('Payment Entry',
            filters={'reference_no': self.name, 'docstatus': ['!=', 2]},
            limit=1)
        if existing:
            frappe.msgprint('Payment Entry already exists for this receipt. Skipping.')
            return

        student_full_name = frappe.db.get_value("Student", self.student_name, "full_name")
        company = frappe.defaults.get_global_default("company") or frappe.get_all("Company")[0].name
        company_currency = frappe.db.get_value("Company", company, "default_currency")

        paid_from = frappe.db.get_value("Company", company, "default_receivable_account")

        paid_to_currency = frappe.db.get_value("Account", self.account, "account_currency") or company_currency
        paid_from_currency = frappe.db.get_value("Account", paid_from, "account_currency") or company_currency

        pe = frappe.new_doc("Payment Entry")
        pe.payment_type = "Receive"
        pe.party_type = "Customer"
        pe.party = student_full_name
        pe.company = company
        pe.posting_date = self.date or today()
        pe.paid_from = paid_from
        pe.paid_to = self.account
        pe.paid_from_account_currency = paid_from_currency
        pe.paid_to_account_currency = paid_to_currency
        pe.paid_amount = self.total_allocated
        pe.received_amount = self.total_allocated
        pe.source_exchange_rate = 1
        pe.target_exchange_rate = 1
        pe.base_paid_amount = self.total_allocated
        pe.base_received_amount = self.total_allocated
        pe.reference_no = self.name
        pe.reference_date = self.date or today()

        total_allocated_in_refs = 0
        for row in self.invoice:
            if row.invoice_number and flt(row.allocated) > 0:
                actual_outstanding = frappe.db.get_value("Sales Invoice", row.invoice_number, "outstanding_amount")
                allocated = min(flt(row.allocated), flt(actual_outstanding))
                if allocated > 0:
                    pe.append("references", {
                        "reference_doctype": "Sales Invoice",
                        "reference_name": row.invoice_number,
                        "allocated_amount": allocated,
                        "due_date": frappe.db.get_value("Sales Invoice", row.invoice_number, "due_date"),
                        "total_amount": frappe.db.get_value("Sales Invoice", row.invoice_number, "grand_total"),
                        "outstanding_amount": actual_outstanding,
                    })
                    total_allocated_in_refs += allocated

        # Ensure difference/unallocated amounts are zero so GL posts cleanly
        pe.total_allocated_amount = total_allocated_in_refs
        pe.unallocated_amount = 0
        pe.write_off_amount = 0
        pe.difference_amount = 0

        # Insert without skipping validate so set_missing_values runs properly
        pe.flags.ignore_permissions = True
        pe.flags.ignore_mandatory = True
        pe.insert(ignore_permissions=True)

        # Recalculate after insert
        pe.run_method("set_missing_values")
        pe.run_method("set_amounts")

        # Force amounts clean before submit
        pe.unallocated_amount = 0
        pe.write_off_amount = 0
        pe.difference_amount = 0

        # Submit WITHOUT ignore_validate — this is critical for GL entries to post
        pe.flags.ignore_permissions = True
        pe.flags.ignore_mandatory = True
        pe.submit()
        frappe.db.commit()

        frappe.msgprint(f"Payment Entry {pe.name} created and GL entries posted successfully.")

        # Update invoice outstanding amounts directly
        for row in self.invoice:
            if row.invoice_number and flt(row.allocated) > 0:
                actual_outstanding = frappe.db.get_value("Sales Invoice", row.invoice_number, "outstanding_amount")
                allocated = min(flt(row.allocated), flt(actual_outstanding))
                new_outstanding = flt(actual_outstanding) - allocated
                new_status = "Paid" if new_outstanding <= 0 else "Partly Paid"
                frappe.db.set_value("Sales Invoice", row.invoice_number, {
                    "outstanding_amount": new_outstanding,
                    "status": new_status
                })
                if new_outstanding <= 0:
                    try:
                        si_doc = frappe.get_doc("Sales Invoice", row.invoice_number)
                        si_doc.cancel()
                        frappe.msgprint(f"Sales Invoice {row.invoice_number} cancelled as fully paid.")
                    except Exception as e:
                        frappe.log_error(f"Failed to cancel SI {row.invoice_number}: {str(e)}")

        # Handle opening balance payments
        for row in self.invoice:
            if not row.invoice_number and row.fees_structure == "Opening Balance":
                current_ob = frappe.db.get_value("Student", self.student_name, "opening_balance")
                new_ob = flt(current_ob) - flt(row.allocated)
                frappe.db.set_value("Student", self.student_name, "opening_balance", new_ob)

        frappe.db.commit()