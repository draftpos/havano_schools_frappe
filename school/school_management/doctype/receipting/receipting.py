import frappe
from frappe.model.document import Document

class Receipting(Document):

    def validate(self):
        self.fetch_student_full_name()
        self.fetch_invoice_details()
        self.calculate_totals()

    def fetch_student_full_name(self):
        if self.student_name:
            self.student_display_name = frappe.db.get_value("Student", self.student_name, "full_name")

    def fetch_invoice_details(self):
        for row in self.invoices:
            if row.invoice_number:
                inv = frappe.db.get_value(
                    "Sales Invoice",
                    row.invoice_number,
                    ["grand_total", "outstanding_amount", "fees_structure"],
                    as_dict=True
                )
                if inv:
                    row.total = inv.grand_total
                    row.outstanding = inv.outstanding_amount
                    if not row.fees_structure:
                        row.fees_structure = inv.fees_structure

    def calculate_totals(self):
        self.total_amount = sum(row.total or 0 for row in self.invoices)
        self.total_allocated = sum(row.allocated or 0 for row in self.invoices)
        self.total_outstanding = self.total_amount - self.total_allocated

    def on_submit(self):
        self.create_payment_entries()

    def create_payment_entries(self):
        company = frappe.defaults.get_global_default("company")
        customer = self.student_display_name

        if not customer:
            frappe.throw("Student full name not found. Cannot create Payment Entry.")

        receivable_account = frappe.db.get_value("Company", company, "default_receivable_account")

        # Determine paid_to account based on payment method
        if self.payment_method == "Bank":
            if self.bank_account:
                paid_to_account = frappe.db.get_value("Bank Account", self.bank_account, "account")
            else:
                paid_to_account = frappe.db.get_value("Company", company, "default_bank_account")
        else:
            paid_to_account = frappe.db.get_value("Company", company, "default_cash_account")

        if not paid_to_account:
            paid_to_account = frappe.db.get_value("Account",
                {"account_type": "Cash", "company": company}, "name"
            )

        if not paid_to_account:
            frappe.throw("No account found. Please set default cash account or select a bank account.")

        pe = frappe.new_doc("Payment Entry")
        pe.payment_type = self.payment_type
        pe.party_type = self.party_type
        pe.party = customer
        pe.posting_date = self.date
        pe.company = company
        pe.paid_amount = self.total_allocated
        pe.received_amount = self.total_allocated
        pe.paid_to = paid_to_account
        pe.paid_from = receivable_account
        pe.reference_no = self.bank_reference or self.name
        pe.reference_date = self.date
        pe.mode_of_payment = self.payment_method
        pe.remarks = f"Payment received via Receipting {self.name}"
        pe.total_allocated_amount = self.total_allocated

        for row in self.invoices:
            if not row.allocated or row.allocated <= 0:
                continue
            pe.append("references", {
                "reference_doctype": "Sales Invoice",
                "reference_name": row.invoice_number,
                "fees_structure": row.fees_structure,
                "total_amount": row.total,
                "outstanding_amount": row.outstanding,
                "allocated_amount": row.allocated,
            })

        pe.flags.ignore_permissions = True
        pe.insert()
        pe.submit()
        frappe.db.commit()

        frappe.msgprint(
            f"✓ Payment Entry {pe.name} created successfully.",
            title="Receipting Submitted"
        )
