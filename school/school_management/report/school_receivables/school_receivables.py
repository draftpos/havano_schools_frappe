import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": _("Student"),
            "fieldname": "student_name",
            "fieldtype": "Data",
            "width": 180
        },
        {
            "label": _("Class"),
            "fieldname": "student_class",
            "fieldtype": "Link",
            "options": "Student Class",
            "width": 120
        },
        {
            "label": _("Section"),
            "fieldname": "section",
            "fieldtype": "Link",
            "options": "Section",
            "width": 100
        },
        {
            "label": _("School / Cost Centre"),
            "fieldname": "cost_center",
            "fieldtype": "Link",
            "options": "Cost Center",
            "width": 150
        },
        {
            "label": _("Fees Structure"),
            "fieldname": "fees_structure",
            "fieldtype": "Link",
            "options": "Fees Structure",
            "width": 150
        },
        {
            "label": _("Invoiced"),
            "fieldname": "invoiced",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Paid"),
            "fieldname": "paid",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Outstanding"),
            "fieldname": "outstanding",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Opening Balance"),
            "fieldname": "opening_balance",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Total Due"),
            "fieldname": "total_due",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100
        }
    ]


def get_data(filters):
    conditions = ["si.docstatus = 1"]
    values = {}

    if filters.get("cost_center"):
        conditions.append("si.cost_center = %(cost_center)s")
        values["cost_center"] = filters["cost_center"]

    if filters.get("student_class"):
        conditions.append("si.student_class = %(student_class)s")
        values["student_class"] = filters["student_class"]

    if filters.get("section"):
        conditions.append("si.student_section = %(section)s")
        values["section"] = filters["section"]

    if filters.get("fees_structure"):
        conditions.append("si.fees_structure = %(fees_structure)s")
        values["fees_structure"] = filters["fees_structure"]

    where = " AND ".join(conditions)

    invoices = frappe.db.sql("""
        SELECT
            si.customer as student_name,
            si.student_class,
            si.student_section as section,
            si.cost_center,
            si.fees_structure,
            SUM(si.grand_total) as invoiced,
            SUM(si.grand_total - si.outstanding_amount) as paid,
            SUM(si.outstanding_amount) as outstanding
        FROM `tabSales Invoice` si
        WHERE {where}
        GROUP BY si.customer, si.student_class, si.student_section,
                 si.cost_center, si.fees_structure
        ORDER BY si.customer ASC
    """.format(where=where), values, as_dict=True)

    # Add opening balances
    result = []
    for row in invoices:
        ob = frappe.db.get_value("Student",
            {"full_name": row.student_name},
            "opening_balance") or 0

        total_due = flt(row.outstanding) + flt(ob)
        status = "Clear" if total_due <= 0 else "Owing"

        result.append({
            "student_name": row.student_name,
            "student_class": row.student_class or "",
            "section": row.section or "",
            "cost_center": row.cost_center or "",
            "fees_structure": row.fees_structure or "",
            "invoiced": flt(row.invoiced),
            "paid": flt(row.paid),
            "outstanding": flt(row.outstanding),
            "opening_balance": flt(ob),
            "total_due": total_due,
            "status": status
        })

    return result
