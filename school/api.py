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
@frappe.whitelist()
def get_portal_dashboard():
    user = frappe.session.user
    if user in ("Administrator", "Guest"):
        return {"error": "Not authorized"}
    student = frappe.db.get_value("Student", {"portal_email": user},
        ["name", "first_name", "second_name", "last_name", "full_name",
         "student_reg_no", "student_class", "section", "house", "student_image"], as_dict=True)
    if not student:
        return {"error": "Student not found"}
    sname = student.name
    # Count records by student's class and section
    s_class   = student.student_class or ""
    s_section = student.section or ""
    s_reg_no  = student.student_reg_no or sname

    class_filters   = {"student_class": s_class} if s_class else {}
    section_filters = {"student_class": s_class, "section": s_section} if s_class and s_section else class_filters

    exam_schedules = frappe.db.count("Exam Schedule",  section_filters) if s_class else 0
    home_schedules = frappe.db.count("Home Schedule",  section_filters) if s_class else 0
    test_schedules = frappe.db.count("Test Schedule",  section_filters) if s_class else 0
    exam_results   = frappe.db.count("Exam Schedule Item", {"student_admission_no": s_reg_no}) if frappe.db.exists("DocType", "Exam Schedule Item") else 0
    inclass_tests  = frappe.db.count("Inclass Test",   {}) if frappe.db.exists("DocType", "Inclass Test") else 0
    homework       = frappe.db.count("Home Schedule Item", {"student_admission_no": s_reg_no}) if frappe.db.exists("DocType", "Home Schedule Item") else 0
    billing_summary  = frappe.db.sql("""
        SELECT SUM(outstanding_amount) as balance
        FROM `tabSales Invoice`
        WHERE customer_name = %s AND docstatus = 1
    """, student.full_name, as_dict=True)
    balance = billing_summary[0].balance if billing_summary and billing_summary[0].balance else 0
    class_name = frappe.db.get_value("Student Class", student.student_class, "class_name") or student.student_class or ""
    return {
        "student": {
            "name":       sname,
            "full_name":  student.full_name or f"{student.first_name or ''} {student.last_name or ''}".strip(),
            "reg_no":     student.student_reg_no or "",
            "class_name": class_name,
            "section":    student.section or "",
            "house":      student.house or "",
            "image":      student.student_image or "",
            "initials":   (student.first_name or "S")[0].upper()
        },
        "counts": {
            "exam_schedules": exam_schedules,
            "home_schedules": home_schedules,
            "test_schedules": test_schedules,
            "exam_results":   exam_results,
            "inclass_tests":  inclass_tests,
            "homework":       homework,
            "balance":        float(balance)
        }
    }

@frappe.whitelist()
def get_exam_schedules():
    user = frappe.session.user
    if user in ("Administrator", "Guest"): return []
    student = frappe.db.get_value("Student", {"portal_email": user}, "name")
    if not student: return []
    return frappe.get_all("Exam Schedule Item",
        filters={"student": student},
        fields=["exam_name", "subject_name", "class_name", "date", "start_time",
                "exam_type", "max_marks", "min_marks", "total_questions",
                "room_number", "number_of_students", "remarks"],
        order_by="date asc")

@frappe.whitelist()
def get_home_schedules():
    user = frappe.session.user
    if user in ("Administrator", "Guest"): return []
    student = frappe.db.get_value("Student", {"portal_email": user}, "name")
    if not student: return []
    return frappe.get_all("Home Schedule Item", filters={"student": student}, fields=["*"], order_by="date asc")

@frappe.whitelist()
def get_test_schedules():
    user = frappe.session.user
    if user in ("Administrator", "Guest"): return []
    student = frappe.db.get_value("Student", {"portal_email": user}, "name")
    if not student: return []
    return frappe.get_all("Test Schedule Item", filters={"student": student}, fields=["*"], order_by="date asc")

@frappe.whitelist()
def get_exam_results():
    user = frappe.session.user
    if user in ("Administrator", "Guest"): return []
    student = frappe.db.get_value("Student", {"portal_email": user}, "name")
    if not student: return []
    return frappe.get_all("Exam Result", filters={"student": student}, fields=["*"], order_by="creation desc")

@frappe.whitelist()
def get_inclass_tests():
    user = frappe.session.user
    if user in ("Administrator", "Guest"): return []
    student = frappe.db.get_value("Student", {"portal_email": user}, "name")
    if not student: return []
    return frappe.get_all("Inclass Test", filters={"student": student}, fields=["*"], order_by="creation desc")

@frappe.whitelist()
def get_user_redirect():
    """Returns where to redirect the logged in user."""
    user = frappe.session.user
    if not user or user == "Guest":
        return {"redirect": "/portal-login"}
    roles = frappe.get_roles(user)
    if "System Manager" in roles or "Administrator" in roles:
        return {"redirect": "/app", "role": "admin"}
    if frappe.db.exists("Student", {"portal_email": user}):
        return {"redirect": "/assets/school/html/student-portal.html", "role": "student"}
    if "School User" in roles:
        return {"redirect": "/app", "role": "school_user"}
    return {"redirect": "/assets/school/html/student-portal.html", "role": "student"}
