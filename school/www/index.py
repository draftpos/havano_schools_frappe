import frappe

no_cache = 1

def get_context(context):
    # If already logged in as student, redirect to portal
    if frappe.session.user != "Guest":
        user_roles = frappe.get_roles(frappe.session.user)
        if "Student Portal" in user_roles:
            frappe.local.flags.redirect_location = "/student-portal"
            raise frappe.Redirect
        # Admin stays on landing page - don't redirect
    context.no_cache = 1
