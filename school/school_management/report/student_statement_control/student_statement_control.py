from __future__ import annotations
from frappe import _
from school.school_management.utils.student_statement import (
    get_statement_summary_rows,
    validate_filters,
)

def execute(filters=None):
    filters = validate_filters(filters or {})
    columns = [
        {"fieldname": "customer", "label": _("Student"), "fieldtype": "Link", "options": "Customer", "width": 180},
        {"fieldname": "customer_name", "label": _("Student Name"), "fieldtype": "Data", "width": 220},
        {"fieldname": "customer_group", "label": _("Customer Group"), "fieldtype": "Link", "options": "Customer Group", "width": 160},
        {"fieldname": "section", "label": _("Section"), "fieldtype": "Data", "width": 120},
        {"fieldname": "student_class", "label": _("Class"), "fieldtype": "Data", "width": 120},
        {"fieldname": "fees_structure", "label": _("Fees Structure"), "fieldtype": "Data", "width": 160},
        {"fieldname": "outstanding", "label": _("Outstanding"), "fieldtype": "Currency", "width": 150},
    ]
    return columns, get_statement_summary_rows(filters)
