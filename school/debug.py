import frappe

@frappe.whitelist(allow_guest=True)
def debug_comments():
    settings = frappe.get_doc("School Settings")
    o_level_comments = {row.comment_type: row.comment for row in getattr(settings, "o_level_admin_comments", [])}
    return o_level_comments
