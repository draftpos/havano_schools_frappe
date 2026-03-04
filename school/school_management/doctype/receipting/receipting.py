import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, flt


class Receipting(Document):

    # ─────────────────────────────────────────────
    #  VALIDATE
    # ─────────────────────────────────────────────
    def validate(self):
        self.fetch_student_display_name()
        self.fetch_invoice_details()
        self.calculate_totals()
        self.set_account_if_missing()

    def fetch_student_display_name(self):
        if not self.student_name:
            return
        student = frappe.db.get_value(
            "Student", self.student_name,
            ["full_name", "first_name", "second_name", "last_name"],
            as_dict=True
        )
        if student:
            self.student_display_name = (
                student.full_name
                or " ".join(filter(None, [student.first_name, student.second_name, student.last_name]))
            )

    def fetch_invoice_details(self):
        """
        For each invoice row pull grand_total and outstanding_amount from Sales Invoice.
        fees_structure is built by GROUP_CONCAT of item_name from Sales Invoice Items.
        """
        for row in self.invoices:
            if not row.invoice_number:
                continue
            inv = frappe.db.get_value(
                "Sales Invoice", row.invoice_number,
                ["grand_total", "outstanding_amount"],
                as_dict=True
            )
            if inv:
                row.total       = inv.grand_total
                row.outstanding = inv.outstanding_amount

            # Always refresh fees_structure from item names on every validate
            result = frappe.db.sql("""
                SELECT GROUP_CONCAT(item_name ORDER BY idx SEPARATOR ', ') AS fees_structure
                FROM `tabSales Invoice Item`
                WHERE parent = %s
            """, row.invoice_number, as_dict=True)
            if result and result[0].fees_structure:
                row.fees_structure = result[0].fees_structure

    def calculate_totals(self):
        self.total_amount      = sum(flt(r.total)      for r in self.invoices)
        self.total_outstanding = sum(flt(r.outstanding) for r in self.invoices)
        if hasattr(self, "total_allocated"):
            self.total_allocated = sum(flt(r.allocated) for r in self.invoices)

    def set_account_if_missing(self):
        if self.account:
            return
        company      = (
            frappe.defaults.get_user_default("company")
            or frappe.db.get_single_value("Global Defaults", "default_company")
        )
        account_type = "Cash" if (self.payment_method or "") == "Cash" else "Bank"
        account = frappe.db.get_value("Account", {
            "company":      company,
            "account_type": account_type,
            "is_group":     0
        }, "name")
        if account:
            self.account = account

    # ─────────────────────────────────────────────
    #  SUBMIT / CANCEL
    # ─────────────────────────────────────────────
    def on_submit(self):
        self.create_payment_entry()

    def on_cancel(self):
        self.cancel_payment_entry()

    # ─────────────────────────────────────────────
    #  PAYMENT ENTRY CREATION
    # ─────────────────────────────────────────────
    def create_payment_entry(self):
        rows = [r for r in self.invoices if r.allocated and r.allocated > 0]
        if not rows:
            frappe.throw("No allocated amounts found. Please allocate amounts before submitting.")

        company            = frappe.defaults.get_global_default("company")
        company_currency   = frappe.db.get_value("Company", company, "default_currency")
        receivable_account = frappe.db.get_value("Company", company, "default_receivable_account")

        paid_to_account  = self.account
        if not paid_to_account:
            frappe.throw("Please select an Account before submitting.")

        paid_to_currency = (
            self.account_currency
            or frappe.db.get_value("Account", paid_to_account, "account_currency")
            or company_currency
        )

        # Customer from first invoice
        first_inv = frappe.get_doc("Sales Invoice", rows[0].invoice_number)

        total_paid = flt(self.paid_amount) or sum(flt(r.allocated) for r in rows)

        # ── Standard PE references ─────────────────────────────────────────
        # fees_structure is passed here because it exists as a custom Data field
        # on Payment Entry Reference (visible in the Reference table in your screenshot).
        # Since it is Data (not Link), the concatenated string saves correctly.
        references = []
        for row in rows:
            references.append({
                "reference_doctype":  "Sales Invoice",
                "reference_name":     row.invoice_number,
                "total_amount":       flt(row.total),
                "outstanding_amount": flt(row.outstanding),
                "allocated_amount":   flt(row.allocated),
                "fees_structure":     row.fees_structure or "",
            })

        # ── Custom invoices child table ────────────────────────────────────
        # fees_structure also lives here for the custom_invoices table on PE
        custom_invoices = []
        for row in rows:
            custom_invoices.append({
                "invoice_number": row.invoice_number,
                "fees_structure": row.fees_structure or "",
                "total":          flt(row.total),
                "outstanding":    flt(row.outstanding),
                "allocated":      flt(row.allocated),
            })

        pe = frappe.get_doc({
            "doctype":                    "Payment Entry",
            "payment_type":               self.payment_type,
            "party_type":                 self.party_type,
            "party":                      first_inv.customer,
            "party_name":                 first_inv.customer,
            "company":                    company,
            "posting_date":               self.date,
            "paid_from":                  receivable_account,
            "paid_to":                    paid_to_account,
            "paid_from_account_currency": company_currency,
            "paid_to_account_currency":   paid_to_currency,
            "source_exchange_rate":       flt(self.exchange_rate) or 1,
            "target_exchange_rate":       flt(self.exchange_rate) or 1,
            "paid_amount":                total_paid,
            "received_amount":            flt(self.received_amount) if paid_to_currency != company_currency else total_paid,
            "mode_of_payment":            self.payment_method or "Cash",
            "reference_no":               self.name,
            "reference_date":             self.date,
            "remarks":                    f"Payment via Receipt {self.name}",
            "references":                 references,
            "custom_invoices":            custom_invoices,
            "custom_receipting":          self.name,
            "custom_student":             self.student_name,
        })

        pe.insert(ignore_permissions=True)
        pe.submit()

        frappe.db.set_value("Receipting", self.name, "payment_entry", pe.name)
        frappe.msgprint(f"✅ Payment Entry <b>{pe.name}</b> created.", alert=True)

    def cancel_payment_entry(self):
        pe_name = frappe.db.get_value("Receipting", self.name, "payment_entry")
        if pe_name and frappe.db.exists("Payment Entry", pe_name):
            pe = frappe.get_doc("Payment Entry", pe_name)
            if pe.docstatus == 1:
                pe.cancel()
                frappe.msgprint(f"Payment Entry {pe_name} cancelled.", alert=True)


# ─────────────────────────────────────────────────────────────
#  WHITELISTED METHODS
#  Must be at MODULE level, NOT inside the class.
# ─────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_outstanding_invoices(student_name):
    """
    Fetch all outstanding Sales Invoices for a student.
    fees_structure = GROUP_CONCAT of item_name from Sales Invoice Items.
    Single source of truth for fees_structure population in the child table.
    """
    student = frappe.db.get_value(
        "Student", student_name,
        ["full_name", "first_name", "second_name", "last_name"],
        as_dict=True
    )
    if not student:
        return []

    customer_name = student.full_name or " ".join(
        filter(None, [student.first_name, student.second_name, student.last_name])
    )

    return frappe.db.sql("""
        SELECT
            si.name,
            si.grand_total,
            si.outstanding_amount,
            GROUP_CONCAT(sii.item_name ORDER BY sii.idx SEPARATOR ', ') AS fees_structure
        FROM `tabSales Invoice` si
        LEFT JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.customer = %s
            AND si.docstatus = 1
            AND si.outstanding_amount > 0
        GROUP BY si.name
        ORDER BY si.posting_date ASC
    """, customer_name, as_dict=True)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def search_students(doctype, txt, searchfield, start, page_len, filters):
    """
    Custom student search filtered by class and section.
    Used by set_query in receipting.js.
    """
    student_class = filters.get("student_class", "") if isinstance(filters, dict) else ""
    section       = filters.get("section", "")       if isinstance(filters, dict) else ""

    conditions = ""
    values     = {"txt": f"%{txt}%", "page_len": page_len, "start": start}

    if student_class:
        conditions += " AND s.student_class = %(student_class)s"
        values["student_class"] = student_class
    if section:
        conditions += " AND s.section = %(section)s"
        values["section"] = section

    return frappe.db.sql(f"""
        SELECT
            s.name,
            TRIM(CONCAT(
                COALESCE(s.first_name, ''), ' ',
                COALESCE(s.second_name, ''), ' ',
                COALESCE(s.last_name, '')
            )) AS full_name
        FROM `tabStudent` s
        WHERE (
            s.name LIKE %(txt)s
            OR s.first_name LIKE %(txt)s
            OR s.last_name LIKE %(txt)s
            OR CONCAT(s.first_name, ' ', s.last_name) LIKE %(txt)s
            OR TRIM(CONCAT(
                COALESCE(s.first_name,''), ' ',
                COALESCE(s.second_name,''), ' ',
                COALESCE(s.last_name,'')
            )) LIKE %(txt)s
        )
        {conditions}
        ORDER BY s.name
        LIMIT %(page_len)s OFFSET %(start)s
    """, values)