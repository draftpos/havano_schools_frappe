import frappe
from frappe import _
import json

def get_context(context):
    settings = frappe.get_single("School Settings")
    
    context.no_cache = 1
    context.show_sidebar = False
    context.bill_on_registration = settings.get("bill_on_registration") or 0
    context.require_approval = settings.get("require_approval_before_creating_student") or 0
    
    # Get schools (Cost Centers) with fallback
    schools = frappe.get_all(
        "Cost Center",
        filters={"is_group": 0, "disabled": 0},
        fields=["name", "cost_center_name"]
    )
    if not schools:
        schools = [{"name": "Main Campus", "cost_center_name": "Main Campus"}]
    context.schools = schools
    
    # Get religions with fallback
    religions = frappe.get_all("Religion", fields=["name"])
    if not religions:
        religions = [{"name": "Christianity"}, {"name": "Islam"}, {"name": "Other"}]
    context.religions = religions
    
    # Get payment accounts with fallback
    payment_accounts = frappe.get_all(
        "Account",
        filters={"account_type": ["in", ["Cash", "Bank"]], "is_group": 0, "disabled": 0},
        fields=["name", "account_name"]
    )
    if not payment_accounts:
        payment_accounts = [
            {"name": "Cash - Main", "account_name": "Cash"},
            {"name": "Bank - Main", "account_name": "Bank Account"}
        ]
    context.payment_accounts = payment_accounts
    
    context.student_types = ["Day", "Boarding"]
    
    # Get all classes - standalone, not dependent on school
    all_classes = frappe.get_all("Student Class", fields=["name"], order_by="name")
    if not all_classes:
        all_classes = [{"name": "Grade 1"}, {"name": "Grade 2"}, {"name": "Grade 3"}]
    context.all_classes_json = json.dumps(all_classes)
    
    # Get all sections - standalone, show all sections
    all_sections = frappe.get_all("Section", fields=["name"], order_by="name")
    if not all_sections:
        all_sections = [{"name": "G1-A"}, {"name": "G1-B"}, {"name": "G2-A"}, {"name": "G2-B"}, {"name": "G3-A"}]
    context.all_sections_json = json.dumps(all_sections)
    
    fees_defaults = []
    for row in settings.get("fees_structure_defaults") or []:
        fees_defaults.append({"status": row.status, "fees_structure": row.fees_structure})
    context.fees_defaults = json.dumps(fees_defaults)


@frappe.whitelist(allow_guest=True)
def get_all_classes():
    """Get all classes from database - standalone, fallback samples if empty"""
    classes = frappe.get_all("Student Class", fields=["name"], order_by="name")
    if not classes:
        classes = [
            {"name": "Grade 1"},
            {"name": "Grade 2"},
            {"name": "Grade 3"}
        ]
    return classes


@frappe.whitelist(allow_guest=True)
def get_all_sections():
    """Get all sections from database - standalone, fallback samples if empty"""
    sections = frappe.get_all("Section", fields=["name"], order_by="name")
    if not sections:
        sections = [
            {"name": "G1-A"},
            {"name": "G1-B"},
            {"name": "G2-A"},
            {"name": "G2-B"},
            {"name": "G3-A"}
        ]
    return sections


@frappe.whitelist(allow_guest=True)
def get_sections_by_class(student_class):
    """Get sections filtered by student class (name LIKE class%)"""
    if not student_class:
        return []
    sections = frappe.get_all("Section", 
        filters={"name": ["like", f"{student_class}%"]}, 
        fields=["name"], 
        order_by="name")
    return sections


@frappe.whitelist(allow_guest=True)
def submit_registration(data):
    settings = frappe.get_single("School Settings")
    
    if not settings.get("allow_online_enrollment"):
        frappe.throw(_("Online enrollment is currently disabled."))

    if isinstance(data, str):
        data = json.loads(data)

    required = ["first_name", "last_name", "student_class", "student_type", "school"]
    for f in required:
        if not data.get(f):
            frappe.throw(_(f"Field '{f}' is required."))

    if settings.get("bill_on_registration"):
        if not data.get("account"):
            frappe.throw(_("Please select a Payment Account."))
        if not data.get("payment_method"):
            frappe.throw(_("Please select a Payment Method."))

    reg = frappe.new_doc("Student Online Registration")

    allowed_fields = [
        "school", "date_of_admission", "student_phone_number", "date_of_birth",
        "first_name", "second_name", "last_name", "student_class", "student_category",
        "religion", "section", "gender", "student_type", "national_identification_number",
        "local_identification_number", "previous_school_details", "medical_history",
        "student_image", "father_name", "mother_name", "phone_number", "father_email",
        "mother_phone", "mother_email", "father_occupation", "mother_occupation",
        "if_guardian_is", "guardian_name", "guardian_occupation", "guardian_email",
        "guardian_phone", "guardian_relation", "guardian_address",
        "current_address", "permanent_address", "account", "payment_method", "portal_email"
    ]
    
    for f in allowed_fields:
        if data.get(f):
            reg.set(f, data[f])

    if settings.get("require_approval_before_creating_student"):
        reg.enrollment_status = "Pending"
    else:
        reg.enrollment_status = "Approved"

    reg.insert(ignore_permissions=True)
    frappe.db.commit()

    if reg.enrollment_status == "Approved" and not reg.student_created:
        reg.reload()
        reg._create_student()

    return {
        "success": True,
        "name": reg.name,
        "status": reg.enrollment_status,
        "message": (
            "Registration submitted! The school will review and contact you."
            if reg.enrollment_status == "Pending"
            else "Registration approved! Your student record has been created."
        )
    }