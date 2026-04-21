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
            "label": _("Receipts"),
            "fieldname": "receipts",
            "fieldtype": "Currency",
            "width": 110
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
    # Get all relevant students first
    student_conditions = []
    student_values = {}
    if filters.get("cost_center"):
        student_conditions.append("s.cost_center = %(cost_center)s")
        student_values["cost_center"] = filters["cost_center"]
    if filters.get("student_class"):
        student_conditions.append("s.student_class = %(student_class)s")
        student_values["student_class"] = filters["student_class"]
    if filters.get("section"):
        student_conditions.append("s.section = %(section)s")
        student_values["section"] = filters["section"]
    if filters.get("fees_structure"):
        student_conditions.append("fs.fees_items LIKE %(_fees_structure)s")
        student_values["_fees_structure"] = f"%{filters['fees_structure']}%"

    student_where = " AND ".join(student_conditions) if student_conditions else "1=1"

    students = frappe.db.sql("""
        SELECT DISTINCT s.name, s.full_name, s.student_class, s.section, s.cost_center
        FROM `tabStudent` s
        LEFT JOIN `tabBilling` b ON b.student_class = s.student_class
        LEFT JOIN `tabFees Structure` fs ON fs.name = b.fees_structure
        WHERE {where}
    """.format(where=student_where), student_values, as_dict=True)

    if not students:
        return []

    student_list = [s.full_name for s in students]
    student_map = {(s.full_name.lower(), s.student_class or '', s.section or '', s.cost_center or ''): s for s in students}

    # Invoices for these students
    invoice_conditions = ["si.docstatus = 1", "si.customer IN %(student_list)s"]
    invoice_values = {"student_list": tuple(student_list)}

    if filters.get("fees_structure"):
        invoice_conditions.append("si.fees_structure = %(fees_structure)s")
        invoice_values["fees_structure"] = filters["fees_structure"]

    invoice_where = " AND ".join(invoice_conditions)

    invoices = frappe.db.sql("""
        SELECT
            si.customer as student_name,
            si.student_class,
            COALESCE(si.student_section, s.section) as section,
            COALESCE(si.cost_center, s.cost_center) as cost_center,
            si.fees_structure,
            SUM(si.grand_total) as invoiced,
            SUM(si.grand_total - si.outstanding_amount) as invoice_paid,
            SUM(si.outstanding_amount) as outstanding
        FROM `tabSales Invoice` si
        INNER JOIN `tabStudent` s ON s.full_name = si.customer
        WHERE {where}
        GROUP BY si.customer, si.student_class, si.student_section, s.section,
                 si.cost_center, s.cost_center, si.fees_structure
    """.format(where=invoice_where), invoice_values, as_dict=True)

    # Receipts for these students
    receipt_conditions = ["r.docstatus = 1"]
    receipt_values = {}

    receipt_where = " AND ".join(receipt_conditions)

    receipts = frappe.db.sql("""
        SELECT
            s.full_name as student_name,
            s.student_class,
            s.section,
            s.cost_center,
            ri.fees_structure,
            SUM(ri.allocated) as receipts
        FROM `tabReceipt Item` ri
        INNER JOIN `tabReceipting` r ON r.name = ri.parent
        INNER JOIN `tabStudent` s ON s.name = r.student_name
        WHERE s.full_name IN %(student_list)s AND {where}
        GROUP BY s.full_name, s.student_class, s.section, s.cost_center, ri.fees_structure
    """.format(where=receipt_where), invoice_values, as_dict=True)

    # Map receipts
    receipt_map = {}
    for r in receipts:
        key = (r.student_name.lower(), r.student_class or '', r.section or '', r.cost_center or '', r.fees_structure or '')
        receipt_map[key] = flt(r.receipts)

    # Build result
    result = []
    processed_keys = set()
    for inv in invoices:
        key = (inv.student_name.lower(), inv.student_class or '', inv.section or '', inv.cost_center or '', inv.fees_structure or '')
        receipts_amount = receipt_map.get(key, 0)
        ob = frappe.db.get_value("Student", {"full_name": inv.student_name}, "opening_balance") or 0

        total_paid = flt(inv.invoice_paid) + receipts_amount
        total_due = flt(inv.outstanding) + flt(ob)
        status = "Clear" if total_due <= 0.01 else "Owing"

        result.append({
            "student_name": inv.student_name,
            "student_class": inv.student_class or "",
            "section": inv.section or "",
            "cost_center": inv.cost_center or "",
            "fees_structure": inv.fees_structure or "",
            "invoiced": flt(inv.invoiced),
            "receipts": receipts_amount,
            "paid": total_paid,
            "outstanding": flt(inv.outstanding),
            "opening_balance": flt(ob),
            "total_due": total_due,
            "status": status
        })
        processed_keys.add(key)

    # Add rows with only receipts (no invoices)
    for r in receipts:
        key = (r.student_name.lower(), r.student_class or '', r.section or '', r.cost_center or '', r.fees_structure or '')
        if key not in processed_keys:
            ob = frappe.db.get_value("Student", {"full_name": r.student_name}, "opening_balance") or 0
            total_due = 0 + flt(ob)  # no outstanding
            status = "Clear" if total_due <= 0.01 else "Owing"

            result.append({
                "student_name": r.student_name,
                "student_class": r.student_class or "",
                "section": r.section or "",
                "cost_center": r.cost_center or "",
                "fees_structure": r.fees_structure or "",
                "invoiced": 0,
                "receipts": flt(r.receipts),
                "paid": flt(r.receipts),
                "outstanding": 0,
                "opening_balance": flt(ob),
                "total_due": total_due,
                "status": status
            })

    return sorted(result, key=lambda x: x["student_name"])
