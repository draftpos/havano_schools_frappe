import frappe
from frappe import _

@frappe.whitelist()
def get_billing_summary():
    """
    Returns a unified view of Invoices and Receipting for the student portal.
    """
    user = frappe.session.user
    if user in ("Administrator", "Guest"): 
        return {"error": "Invalid User"}

    # Get student record
    student = frappe.db.get_value("Student", {"portal_email": user}, ["name", "full_name"], as_dict=True)
    if not student: 
        return {"error": "Student record not found"}

    # 1. Fetch Invoices (Sales Invoices)
    # Note: Using customer_name to link to Sales Invoice
    invoices = frappe.db.sql("""
        SELECT name, posting_date, due_date, grand_total, outstanding_amount, status
        FROM `tabSales Invoice`
        WHERE customer_name = %s 
        ORDER BY posting_date DESC
    """, student.full_name, as_dict=True)

    for inv in invoices:
        inv['posting_date'] = str(inv['posting_date'])
        inv['due_date'] = str(inv['due_date'])
        inv['items'] = frappe.get_all("Sales Invoice Item", 
                                      filters={"parent": inv['name']}, 
                                      fields=["item_name", "qty", "rate", "amount"])

    # 2. Fetch Receipts (Based on your new Receipting DocType)
    # Using student.name (ID) as per your form requirements
    receipts = frappe.db.sql("""
        SELECT name, date, total_outstanding, total_allocated, total_balance, account, docstatus
        FROM `tabReceipting` 
        WHERE student_name = %s 
        ORDER BY date DESC
    """, student.name, as_dict=True)

    for rec in receipts:
        rec['date'] = str(rec['date'])
        # Matching the fields in your Receipt Item table
        rec['items'] = frappe.get_all("Receipt Item", 
                                      filters={"parent": rec['name']}, 
                                      fields=["invoice_number", "fees_structure", "outstanding", "allocated"])

    return {
        "student": student, 
        "invoices": invoices, 
        "receipts": receipts
    }

@frappe.whitelist()
def get_student_invoices(student):
    """
    Used by the Receipting Form to auto-load outstanding invoices.
    Targets student_name (ID) passed from the JS.
    """
    if not student:
        return []

    # Get the Full Name to find the Customer record
    full_name = frappe.db.get_value("Student", student, "full_name")
    
    # In ERPNext, Sales Invoices link to 'Customer'. 
    # This assumes Customer Name matches Student Full Name.
    customer = frappe.db.get_value("Customer", {"customer_name": full_name}, "name")
    
    if not customer:
        # Fallback: check if the Student ID is used directly as the Customer ID
        customer = frappe.db.get_value("Customer", student, "name")

    if not customer:
        return []
    
    invoices = frappe.get_all("Sales Invoice",
        filters={
            "customer": customer, 
            "docstatus": 1, 
            "outstanding_amount": [">", 0]
        },
        fields=["name", "grand_total", "outstanding_amount", "fees_structure", "posting_date"],
        order_by="posting_date desc")
    
    for inv in invoices:
        inv["posting_date"] = str(inv["posting_date"])
        
    return invoices

# --- Profile and Schedules remain as previously defined ---

@frappe.whitelist()
def get_my_account():
    user = frappe.session.user
    if user in ("Administrator", "Guest"): return []
    student = frappe.db.get_value("Student", {"portal_email": user},
        ["name", "first_name", "second_name", "last_name", "full_name",
         "student_reg_no", "student_class", "section", "house",
         "date_of_admission", "portal_email", "student_category"], as_dict=True)
    if student:
        student["class_name"] = frappe.db.get_value("Student Class", student.student_class, "class_name") or student.student_class
        student["date_of_admission"] = str(student.date_of_admission) if student.date_of_admission else "-"
    return student