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
    
    fees_defaults = []
    for row in settings.get("fees_structure_defaults") or []:
        fees_defaults.append({"status": row.status, "fees_structure": row.fees_structure})
    context.fees_defaults = json.dumps(fees_defaults)


@frappe.whitelist(allow_guest=True)
def get_classes_by_school(school):
    """Get classes filtered by school/cost center.
    
    This function tries multiple approaches to find classes linked to a school:
    1. Checks if Student Class has a 'cost_center' field and filters by it
    2. Checks if Student Class has a 'school' field and filters by it
    3. Tries to match classes that have the school name in their name
    4. Falls back to returning all classes if no matches found
    """
    if not school:
        return []

    classes = []
    
    # Approach 1: Check if Student Class has a cost_center field
    has_cost_center = frappe.db.has_column("Student Class", "cost_center")
    if has_cost_center:
        classes = frappe.get_all(
            "Student Class",
            filters={"cost_center": school},
            fields=["name"],
            order_by="name"
        )
        if classes:
            return classes
    
    # Approach 2: Check if Student Class has a school field
    has_school_field = frappe.db.has_column("Student Class", "school")
    if has_school_field:
        classes = frappe.get_all(
            "Student Class",
            filters={"school": school},
            fields=["name"],
            order_by="name"
        )
        if classes:
            return classes
    
    # Approach 3: Try to match classes that have the school in their name
    # This is useful if classes are named like "Grade 1 - Main Campus"
    try:
        classes = frappe.get_all(
            "Student Class",
            filters={
                "name": ["like", f"%{school}%"]
            },
            fields=["name"],
            order_by="name"
        )
        if classes:
            return classes
    except Exception as e:
        frappe.log_error(f"Error filtering classes by name: {str(e)}", "Student Registration")
    
    # Approach 4: Check if there's a custom field linking to Cost Center
    # This checks for any field in Student Class that is a Link to Cost Center
    try:
        custom_fields = frappe.get_all(
            "Custom Field",
            filters={
                "dt": "Student Class",
                "fieldtype": "Link",
                "options": "Cost Center"
            },
            fields=["fieldname"]
        )
        
        for custom_field in custom_fields:
            fieldname = custom_field.fieldname
            classes = frappe.get_all(
                "Student Class",
                filters={fieldname: school},
                fields=["name"],
                order_by="name"
            )
            if classes:
                return classes
    except Exception as e:
        frappe.log_error(f"Error checking custom fields: {str(e)}", "Student Registration")
    
    # Fallback: Return all classes if no filter works
    # This ensures the dropdown is never empty during setup
    classes = frappe.get_all(
        "Student Class",
        fields=["name"],
        order_by="name"
    )
    
    return classes


@frappe.whitelist(allow_guest=True)
def get_sections_by_school(school):
    """Get sections filtered by school/cost center"""
    if not school:
        return []
    
    sections = []
    
    # Check if Section has cost_center field
    if frappe.db.has_column("Section", "cost_center"):
        sections = frappe.get_all(
            "Section",
            filters={"cost_center": school},
            fields=["name"],
            order_by="name"
        )
        if sections:
            return sections
    
    # Check if Section has school field
    if frappe.db.has_column("Section", "school"):
        sections = frappe.get_all(
            "Section",
            filters={"school": school},
            fields=["name"],
            order_by="name"
        )
        if sections:
            return sections
    
    # Fallback: return all sections
    sections = frappe.get_all("Section", fields=["name"], order_by="name")
    
    return sections


@frappe.whitelist(allow_guest=True)
def get_sections_by_class_and_school(student_class, school):
    """Get sections filtered by student class and school"""
    if not student_class:
        return []
    
    sections = []
    
    # First try to filter by both class pattern and school
    if frappe.db.has_column("Section", "cost_center"):
        sections = frappe.get_all(
            "Section",
            filters={
                "name": ["like", f"{student_class}%"],
                "cost_center": school
            },
            fields=["name"],
            order_by="name"
        )
        if sections:
            return sections
    
    # Try with school field
    if frappe.db.has_column("Section", "school"):
        sections = frappe.get_all(
            "Section",
            filters={
                "name": ["like", f"{student_class}%"],
                "school": school
            },
            fields=["name"],
            order_by="name"
        )
        if sections:
            return sections
    
    # Fallback: filter only by class pattern
    sections = frappe.get_all(
        "Section",
        filters={"name": ["like", f"{student_class}%"]},
        fields=["name"],
        order_by="name"
    )
    
    return sections


@frappe.whitelist(allow_guest=True)
def get_all_sections():
    """Legacy method - kept for compatibility"""
    return frappe.get_all("Section", fields=["name"], order_by="name")


@frappe.whitelist(allow_guest=True)
def submit_registration(data):
    """Submit a new student registration"""
    settings = frappe.get_single("School Settings")
    
    # Check if online enrollment is allowed
    if not settings.get("allow_online_enrollment"):
        frappe.throw(_("Online enrollment is currently disabled."))

    # Parse data if it's a string
    if isinstance(data, str):
        data = json.loads(data)

    # Validate required fields
    required = ["first_name", "last_name", "student_class", "student_type", "school"]
    for f in required:
        if not data.get(f):
            frappe.throw(_("Field '{0}' is required.").format(f))

    # Validate payment fields if billing is enabled
    if settings.get("bill_on_registration"):
        if not data.get("account"):
            frappe.throw(_("Please select a Payment Account."))
        if not data.get("payment_method"):
            frappe.throw(_("Please select a Payment Method."))

    # Create the registration document
    reg = frappe.get_doc({
        "doctype": "Student Online Registration",
        "school": data.get("school"),
        "first_name": data.get("first_name"),
        "second_name": data.get("second_name"),
        "last_name": data.get("last_name"),
        "date_of_birth": data.get("date_of_birth"),
        "gender": data.get("gender"),
        "student_phone_number": data.get("student_phone_number"),
        "student_class": data.get("student_class"),
        "student_type": data.get("student_type"),
        "religion": data.get("religion"),
        "date_of_admission": data.get("date_of_admission"),
        "national_identification_number": data.get("national_identification_number"),
        "local_identification_number": data.get("local_identification_number"),
        "previous_school_details": data.get("previous_school_details"),
        "medical_history": data.get("medical_history"),
        "portal_email": data.get("portal_email"),
        "father_name": data.get("father_name"),
        "mother_name": data.get("mother_name"),
        "phone_number": data.get("phone_number"),
        "mother_phone": data.get("mother_phone"),
        "father_email": data.get("father_email"),
        "mother_email": data.get("mother_email"),
        "father_occupation": data.get("father_occupation"),
        "mother_occupation": data.get("mother_occupation"),
        "if_guardian_is": data.get("if_guardian_is"),
        "guardian_name": data.get("guardian_name"),
        "guardian_relation": data.get("guardian_relation"),
        "guardian_phone": data.get("guardian_phone"),
        "guardian_email": data.get("guardian_email"),
        "guardian_occupation": data.get("guardian_occupation"),
        "guardian_address": data.get("guardian_address"),
        "current_address": data.get("current_address"),
        "permanent_address": data.get("permanent_address"),
        "account": data.get("account"),
        "payment_method": data.get("payment_method"),
        "enrollment_status": "Pending"
    })

    # Insert the document
    reg.insert(ignore_permissions=True)
    frappe.db.commit()

    # Return success response
    return {
        "success": True,
        "name": reg.name,
        "status": reg.enrollment_status,
        "message": "Registration submitted successfully! Reference: " + reg.name
    }


@frappe.whitelist(allow_guest=True)
def get_student_classes_with_school_info():
    """Helper function to get all student classes with their linked school info.
    Useful for debugging and testing.
    """
    classes = frappe.get_all(
        "Student Class",
        fields=["name", "cost_center", "school"]
    )
    
    # Add custom field info
    custom_fields = frappe.get_all(
        "Custom Field",
        filters={
            "dt": "Student Class",
            "fieldtype": "Link",
            "options": "Cost Center"
        },
        fields=["fieldname", "label"]
    )
    
    return {
        "classes": classes,
        "custom_fields": custom_fields,
        "has_cost_center_column": frappe.db.has_column("Student Class", "cost_center"),
        "has_school_column": frappe.db.has_column("Student Class", "school")
    }