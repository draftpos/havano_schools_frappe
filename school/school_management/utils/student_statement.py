from __future__ import annotations

import io
import shutil
import zipfile
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe import _
from frappe.utils import cstr, flt, formatdate, now_datetime
from frappe.utils.pdf import get_pdf

DETAIL_TEMPLATE = "school/school_management/school_statements/templates/includes/student_statement_pdf.html"

PDF_OPTIONS = {
    "page-size": "A4",
    "margin-top": "8mm",
    "margin-bottom": "8mm",
    "margin-left": "8mm",
    "margin-right": "8mm",
    "encoding": "UTF-8",
    "print-media-type": None,
    "disable-smart-shrinking": None,
}


def validate_filters(filters):
    filters = frappe._dict(filters or {})
    if not filters.get("company"):
        filters.company = frappe.defaults.get_user_default("Company")
    if not filters.get("company"):
        frappe.throw(_("Company is required."))
    if not filters.get("report_date"):
        filters.report_date = now_datetime().date().isoformat()
    if not filters.get("to_date"):
        filters.to_date = filters.report_date
    if not filters.get("from_date"):
        report_date_obj = frappe.utils.getdate(filters.report_date)
        filters.from_date = report_date_obj.replace(day=1).isoformat()
    if frappe.utils.getdate(filters.from_date) > frappe.utils.getdate(filters.to_date):
        frappe.throw(_("From Date cannot be after To Date."))
    return filters


def get_customer_dimension_fields():
    return {}


def _get_student_for_customer(customer):
    return frappe.db.get_value("Student", {"customer": customer}, "name")


def _get_fees_structure_for_customer(customer, company):
    student = _get_student_for_customer(customer)
    if not student:
        return None
    result = frappe.db.sql("""
        SELECT b.fees_structure
        FROM `tabBilling` b
        WHERE b.docstatus < 2
          AND b.company = %(company)s
          AND EXISTS (
            SELECT 1 FROM `tabBilling Item` bi
            WHERE bi.parent = b.name
          )
        ORDER BY b.date DESC LIMIT 1
    """, {"company": company}, as_dict=True)
    if result:
        return result[0].get("fees_structure")
    return None


def _customer_filter_sql(filters, fields=None):
    conditions = []
    values = {
        "company": filters.get("company"),
        "report_date": filters.get("report_date"),
        "from_date": filters.get("from_date"),
        "to_date": filters.get("to_date"),
        "customer": filters.get("customer"),
        "customer_group": filters.get("customer_group"),
        "section": filters.get("section"),
        "student_class": filters.get("student_class"),
    }

    if filters.get("customer"):
        conditions.append("c.name = %(customer)s")
    if filters.get("customer_group"):
        conditions.append("c.customer_group = %(customer_group)s")
    if filters.get("section"):
        conditions.append("""EXISTS (
            SELECT 1 FROM `tabStudent` st
            WHERE st.customer = c.name AND st.section = %(section)s
        )""")
    if filters.get("student_class"):
        conditions.append("""EXISTS (
            SELECT 1 FROM `tabStudent` st
            WHERE st.customer = c.name AND st.student_class = %(student_class)s
        )""")

    clause = (" AND " + " AND ".join(conditions)) if conditions else ""
    return clause, values


def get_students_for_batch(filters):
    filters = validate_filters(filters)
    clause, values = _customer_filter_sql(filters)

    return frappe.db.sql(f"""
        SELECT
            c.name AS customer,
            c.customer_name,
            c.customer_group,
            st.section,
            st.student_class
        FROM `tabCustomer` c
        LEFT JOIN `tabStudent` st ON st.customer = c.name
        WHERE c.disabled = 0
        {clause}
        ORDER BY c.customer_group, c.customer_name, c.name
    """, values, as_dict=True)


def _get_currency(company):
    return frappe.get_cached_value("Company", company, "default_currency") or frappe.defaults.get_global_default("currency")


def _get_party_opening_balance(company, customer, from_date):
    return flt(frappe.db.sql("""
        SELECT COALESCE(SUM(gle.debit - gle.credit), 0)
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.company = %(company)s AND gle.party_type = "Customer"
          AND gle.party = %(customer)s AND gle.is_cancelled = 0
          AND gle.posting_date < %(from_date)s AND acc.account_type = "Receivable"
    """, {"company": company, "customer": customer, "from_date": from_date})[0][0])


def _get_party_closing_balance(company, customer, to_date):
    return flt(frappe.db.sql("""
        SELECT COALESCE(SUM(gle.debit - gle.credit), 0)
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.company = %(company)s AND gle.party_type = "Customer"
          AND gle.party = %(customer)s AND gle.is_cancelled = 0
          AND gle.posting_date <= %(to_date)s AND acc.account_type = "Receivable"
    """, {"company": company, "customer": customer, "to_date": to_date})[0][0])


def _get_statement_entries(company, customer, from_date, to_date):
    return frappe.db.sql("""
        SELECT gle.name, gle.posting_date, gle.voucher_type, gle.voucher_no,
               gle.debit, gle.credit, gle.remarks
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.company = %(company)s AND gle.party_type = "Customer"
          AND gle.party = %(customer)s AND gle.is_cancelled = 0
          AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
          AND acc.account_type = "Receivable"
        ORDER BY gle.posting_date, gle.creation, gle.name
    """, {"company": company, "customer": customer, "from_date": from_date, "to_date": to_date}, as_dict=True)


def _get_formatted_address_for_linked_party(link_doctype, link_name):
    result = frappe.db.sql("""
        SELECT a.name FROM `tabAddress` a
        INNER JOIN `tabDynamic Link` dl ON dl.parent = a.name
        WHERE dl.link_doctype = %(link_doctype)s AND dl.link_name = %(link_name)s
          AND a.disabled = 0
        ORDER BY a.is_primary_address DESC, a.modified DESC LIMIT 1
    """, {"link_doctype": link_doctype, "link_name": link_name}, as_dict=True)
    if not result:
        return ""
    return frappe.get_cached_value("Address", result[0]["name"], "display") or ""


def _get_company_logo(company):
    logo = frappe.db.get_value("Company", company, "company_logo")
    return logo if logo else None


def _get_customer_details(customer, fields=None):
    customer_doc = frappe.get_cached_doc("Customer", customer)
    student = frappe.db.get_value("Student", {"customer": customer},
        ["section", "student_class", "fees_category"], as_dict=True) or {}
    return {
        "customer": customer_doc.name,
        "customer_name": customer_doc.customer_name,
        "customer_group": customer_doc.customer_group,
        "mobile_no": getattr(customer_doc, "mobile_no", None),
        "email_id": getattr(customer_doc, "email_id", None),
        "address": _get_formatted_address_for_linked_party("Customer", customer_doc.name),
        "section": student.get("section"),
        "student_class": student.get("student_class"),
        "fees_category": student.get("fees_category"),
    }


def _get_school_details(company):
    company_doc = frappe.get_cached_doc("Company", company)
    return {
        "company": company_doc.name,
        "company_name": company_doc.company_name,
        "phone_no": getattr(company_doc, "phone_no", None),
        "email": getattr(company_doc, "email", None),
        "address": _get_formatted_address_for_linked_party("Company", company_doc.name),
        "logo": _get_company_logo(company_doc.name),
    }


def build_statement_rows(filters, customer):
    filters = validate_filters(filters)
    company = filters["company"]
    from_date = filters["from_date"]
    to_date = filters["to_date"]

    opening_balance = _get_party_opening_balance(company, customer, from_date)
    transactions = _get_statement_entries(company, customer, from_date, to_date)

    rows = []
    running_balance = flt(opening_balance)

    rows.append({
        "posting_date": from_date, "display_date": formatdate(from_date),
        "voucher_type": "", "voucher_no": "", "reference_no": "",
        "description": "Balance b/d",
        "debit": opening_balance if opening_balance > 0 else 0,
        "credit": abs(opening_balance) if opening_balance < 0 else 0,
        "running_balance": running_balance, "is_opening": 1, "is_closing": 0,
    })

    for entry in transactions:
        debit = flt(entry.get("debit"))
        credit = flt(entry.get("credit"))
        running_balance += debit - credit
        rows.append({
            "posting_date": entry.get("posting_date"),
            "display_date": formatdate(entry.get("posting_date")),
            "voucher_type": entry.get("voucher_type"),
            "voucher_no": entry.get("voucher_no"),
            "reference_no": entry.get("voucher_no") or "",
            "description": entry.get("remarks") or entry.get("voucher_type") or "",
            "debit": debit, "credit": credit, "running_balance": running_balance,
            "is_opening": 0, "is_closing": 0,
        })

    closing_balance = _get_party_closing_balance(company, customer, to_date)
    rows.append({
        "posting_date": to_date, "display_date": formatdate(to_date),
        "voucher_type": "", "voucher_no": "", "reference_no": "",
        "description": "Balance c/d",
        "debit": closing_balance if closing_balance > 0 else 0,
        "credit": abs(closing_balance) if closing_balance < 0 else 0,
        "running_balance": closing_balance, "is_opening": 0, "is_closing": 1,
    })

    return rows, opening_balance, closing_balance


def build_statement_context(filters, customer):
    filters = validate_filters(filters)
    currency = _get_currency(filters["company"])
    rows, opening_balance, closing_balance = build_statement_rows(filters, customer)
    fees_structure = _get_fees_structure_for_customer(customer, filters["company"])

    return {
        "title": "Student Statement",
        "filters": filters,
        "currency": currency,
        "school": _get_school_details(filters["company"]),
        "student": _get_customer_details(customer),
        "fees_structure": fees_structure,
        "rows": rows,
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "generated_on": now_datetime(),
    }


def render_statement_html(filters, customer):
    context = build_statement_context(filters, customer)
    return frappe.render_template(DETAIL_TEMPLATE, context)


def _assert_wkhtmltopdf():
    if not shutil.which("wkhtmltopdf"):
        frappe.throw(_("wkhtmltopdf is not installed."), title=_("Missing PDF Engine"))


def _save_private_file(file_name, content, is_private=1):
    file_doc = frappe.get_doc({
        "doctype": "File", "file_name": file_name,
        "content": content, "is_private": is_private,
    })
    file_doc.save(ignore_permissions=True)
    return file_doc


def _sanitize_file_component(value, fallback):
    cleaned = cstr(value or fallback).strip()
    for bad in ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]:
        cleaned = cleaned.replace(bad, "-")
    return cleaned or fallback


def render_statement_pdf_bytes(filters, customer):
    _assert_wkhtmltopdf()
    html = render_statement_html(filters, customer)
    return get_pdf(html, PDF_OPTIONS)


def render_statement_zip_file(filters):
    filters = validate_filters(filters)
    students = get_students_for_batch(filters)
    if not students:
        frappe.throw(_("No students matched the selected filters."))
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for student in students:
            pdf_bytes = render_statement_pdf_bytes(filters, student["customer"])
            safe_name = _sanitize_file_component(student.get("customer_name") or student["customer"], student["customer"])
            zip_file.writestr(f"{safe_name}.pdf", pdf_bytes)
    zip_buffer.seek(0)
    section_bit = _sanitize_file_component(filters.get("section"), "all-sections")
    class_bit = _sanitize_file_component(filters.get("student_class"), "all-classes")
    file_name = f"Student Statements {filters['company']} {section_bit} {class_bit}.zip"
    return _save_private_file(file_name, zip_buffer.read())


def render_batch_pdf_file(filters):
    filters = validate_filters(filters)
    students = get_students_for_batch(filters)
    if not students:
        frappe.throw(_("No students matched the selected filters."))
    _assert_wkhtmltopdf()
    statements_html = []
    for idx, student in enumerate(students):
        html = render_statement_html(filters, student["customer"])
        statements_html.append(f"<div style="width:100%; box-sizing:border-box;">{html}</div>")
        if idx < len(students) - 1:
            statements_html.append("<div style="page-break-after: always;"></div>")
    merged_html = "".join(statements_html)
    pdf_bytes = get_pdf(merged_html, PDF_OPTIONS)
    section_bit = _sanitize_file_component(filters.get("section"), "all-sections")
    class_bit = _sanitize_file_component(filters.get("student_class"), "all-classes")
    file_name = f"Student Statements {filters['company']} {section_bit} {class_bit}.pdf"
    return _save_private_file(file_name, pdf_bytes)


def get_statement_summary_rows(filters):
    filters = validate_filters(filters)
    clause, values = _customer_filter_sql(filters)

    return frappe.db.sql(f"""
        SELECT
            gle.party AS customer,
            c.customer_name,
            c.customer_group,
            st.section,
            st.student_class,
            st.fees_category AS fees_structure,
            COALESCE(SUM(gle.debit - gle.credit), 0) AS outstanding
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc
            ON acc.name = gle.account
           AND acc.account_type = "Receivable"
           AND acc.company = %(company)s
        INNER JOIN `tabCustomer` c ON c.name = gle.party
        LEFT JOIN `tabStudent` st ON st.customer = gle.party
        WHERE gle.company = %(company)s
          AND gle.party_type = "Customer"
          AND gle.is_cancelled = 0
          AND gle.posting_date <= %(report_date)s
          {clause}
        GROUP BY gle.party, c.customer_name, c.customer_group, st.section, st.student_class, st.fees_category
        HAVING ABS(COALESCE(SUM(gle.debit - gle.credit), 0)) > 0.0001
        ORDER BY c.customer_group, st.section, st.student_class, c.customer_name
    """, values, as_dict=True)


def get_batch_student_count(filters):
    filters = validate_filters(filters)
    clause, values = _customer_filter_sql(filters)
    result = frappe.db.sql(f"""
        SELECT COUNT(DISTINCT c.name)
        FROM `tabCustomer` c
        LEFT JOIN `tabStudent` st ON st.customer = c.name
        WHERE c.disabled = 0 {clause}
    """, values)
    return {"count": result[0][0] if result else 0}
