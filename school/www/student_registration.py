import frappe
from frappe import _
import json

def get_context(context):
    settings = frappe.get_single("School Settings")

    context.no_cache = 1
    context.show_sidebar = False
    context.no_csrf = 1
    
    # Pass CSRF token to template
    context.csrf_token = frappe.sessions.get_csrf_token()

    context.bill_on_registration = settings.get("bill_on_registration") or 0
    context.require_approval = settings.get("require_approval_before_creating_student") or 0
    
    # Online enrollment setting
    context.allow_online_enrollment = settings.get("allow_online_enrollment") or 0
    context.online_enrollment_enabled = context.allow_online_enrollment

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

    # Get student categories (Customer Groups)
    context.student_categories = frappe.get_all("Customer Group", fields=["name"])

    # Get houses
    context.houses = frappe.get_all("House", fields=["name"])

    # Get fees structures
    context.fees_structures = frappe.get_all("Fees Structure", fields=["name"])

    # Get categories 1, 2, 3
    context.categories_1 = frappe.get_all("Category 1", fields=["name"])
    context.categories_2 = frappe.get_all("Category 2", fields=["name"])
    context.categories_3 = frappe.get_all("Category 3", fields=["name"])

    # Get area and territory
    context.areas = frappe.get_all("Area", fields=["name"])
    context.territories = frappe.get_all("Territory", fields=["name"])

    # Get fees category
    context.fees_categories = frappe.get_all("Fees Category", fields=["name"])

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
    """Get classes filtered by school/cost center."""
    if not school:
        return []

    classes = []

    # Approach 1: cost_center field
    if frappe.db.has_column("Student Class", "cost_center"):
        classes = frappe.get_all(
            "Student Class",
            filters={"cost_center": school},
            fields=["name", "class_name"],
            order_by="name"
        )
        if classes:
            return classes

    # Approach 2: school field
    if frappe.db.has_column("Student Class", "school"):
        classes = frappe.get_all(
            "Student Class",
            filters={"school": school},
            fields=["name", "class_name"],
            order_by="name"
        )
        if classes:
            return classes

    # Approach 3: name pattern match
    try:
        classes = frappe.get_all(
            "Student Class",
            filters={"name": ["like", f"%{school}%"]},
            fields=["name", "class_name"],
            order_by="name"
        )
        if classes:
            return classes
    except Exception as e:
        frappe.log_error(f"Error filtering classes by name: {str(e)}", "Student Registration")

    # Approach 4: custom Link field to Cost Center
    try:
        custom_fields = frappe.get_all(
            "Custom Field",
            filters={"dt": "Student Class", "fieldtype": "Link", "options": "Cost Center"},
            fields=["fieldname"]
        )
        for custom_field in custom_fields:
            classes = frappe.get_all(
                "Student Class",
                filters={custom_field.fieldname: school},
                fields=["name", "class_name"],
                order_by="name"
            )
            if classes:
                return classes
    except Exception as e:
        frappe.log_error(f"Error checking custom fields: {str(e)}", "Student Registration")

    # Fallback: return all classes
    return frappe.get_all("Student Class", fields=["name", "class_name"], order_by="name")


@frappe.whitelist(allow_guest=True)
def get_all_student_classes():
    """Get all student classes regardless of school"""
    return frappe.get_all("Student Class", fields=["name", "class_name"], order_by="name")


@frappe.whitelist(allow_guest=True)
def get_sections_by_school(school):
    if not school:
        return []
    if frappe.db.has_column("Section", "cost_center"):
        sections = frappe.get_all("Section", filters={"cost_center": school}, fields=["name"], order_by="name")
        if sections:
            return sections
    if frappe.db.has_column("Section", "school"):
        sections = frappe.get_all("Section", filters={"school": school}, fields=["name"], order_by="name")
        if sections:
            return sections
    return frappe.get_all("Section", fields=["name"], order_by="name")


@frappe.whitelist(allow_guest=True)
def get_sections_by_class_and_school(student_class, school):
    if not student_class:
        return []
    if frappe.db.has_column("Section", "cost_center"):
        sections = frappe.get_all("Section", filters={"name": ["like", f"{student_class}%"], "cost_center": school}, fields=["name"], order_by="name")
        if sections:
            return sections
    if frappe.db.has_column("Section", "school"):
        sections = frappe.get_all("Section", filters={"name": ["like", f"{student_class}%"], "school": school}, fields=["name"], order_by="name")
        if sections:
            return sections
    return frappe.get_all("Section", filters={"name": ["like", f"{student_class}%"]}, fields=["name"], order_by="name")


@frappe.whitelist(allow_guest=True)
def get_all_sections():
    return frappe.get_all("Section", fields=["name"], order_by="name")


@frappe.whitelist(allow_guest=True)
def submit_registration(data):
    """Submit a new student registration"""
    
    # CRITICAL: Disable CSRF for guest users
    frappe.local.no_csrf = True
    
    # Get settings
    settings = frappe.get_single("School Settings")
    
    # Check if online enrollment is enabled
    # Use the exact field name from your School Settings
    if not settings.get("allow_online_enrollment"):
        frappe.throw(_("Online enrollment is currently disabled. Please contact the administrator."))

    if isinstance(data, str):
        data = json.loads(data)

    # Validate required fields
    required = ["first_name", "last_name", "student_class", "student_type", "school"]
    for f in required:
        if not data.get(f):
            frappe.throw(_("Field '{0}' is required.").format(f))

    # Check billing requirements
    if settings.get("bill_on_registration"):
        if not data.get("account"):
            frappe.throw(_("Please select a Payment Account."))
        if not data.get("payment_method"):
            frappe.throw(_("Please select a Payment Method."))

    # Create registration document
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
        "portal_password": data.get("portal_password"),
        "student_category": data.get("student_category"),
        "house": data.get("house"),
        "has_opening_balance": data.get("has_opening_balance"),
        "opening_balance": data.get("opening_balance"),
        "cost_center": data.get("cost_center"),
        "opening_balance_date": data.get("opening_balance_date"),
        "paying_admin_fee": data.get("paying_admin_fee"),
        "admin_fee_paid": data.get("admin_fee_paid"),
        "admin_fees_structure": data.get("admin_fees_structure"),
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
        "if_guardian_address_is_current_address": data.get("if_guardian_address_is_current_address"),
        "current_address": data.get("current_address"),
        "if_permanent_address_is_current_address": data.get("if_permanent_address_is_current_address"),
        "permanent_address": data.get("permanent_address"),
        "category_1": data.get("category_1"),
        "category_2": data.get("category_2"),
        "category_3": data.get("category_3"),
        "area": data.get("area"),
        "territory": data.get("territory"),
        "fees_category": data.get("fees_category"),
        "account": data.get("account"),
        "payment_method": data.get("payment_method"),
        "enrollment_status": "Pending"
    })

    reg.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "name": reg.name,
        "status": reg.enrollment_status,
        "message": "Registration submitted successfully! Reference: " + reg.name
    }


@frappe.whitelist(allow_guest=True)
def get_student_classes_with_school_info():
    classes = frappe.get_all("Student Class", fields=["name", "cost_center", "school"])
    custom_fields = frappe.get_all(
        "Custom Field",
        filters={"dt": "Student Class", "fieldtype": "Link", "options": "Cost Center"},
        fields=["fieldname", "label"]
    )
    return {
        "classes": classes,
        "custom_fields": custom_fields,
        "has_cost_center_column": frappe.db.has_column("Student Class", "cost_center"),
        "has_school_column": frappe.db.has_column("Student Class", "school")
    }


@frappe.whitelist(allow_guest=True)
def check_enrollment_status():
    """Helper function to check if online enrollment is enabled"""
    settings = frappe.get_single("School Settings")
    return {
        "enabled": settings.get("allow_online_enrollment") or 0,
        "allow_online_enrollment": settings.get("allow_online_enrollment") or 0
    }
