import frappe

def redirect_to_portal(login_manager):
    try:
        if frappe.session.user == "Guest":
            return
        user_roles = frappe.get_roles(frappe.session.user)
        if "Student Portal" in user_roles:
            frappe.local.response["type"] = "redirect"
            frappe.local.response["location"] = "/student-portal"
    except Exception:
        pass
