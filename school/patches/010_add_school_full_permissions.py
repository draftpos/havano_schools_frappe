import frappe
from frappe.custom.doctype.custom_docperm.custom_docperm import get_matching_custom_permissions


def execute():
    school_module = "School Management"
    roles = ["School User", "System Manager"]
    full_perms = {
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 1,
        "submit": 1,
        "cancel": 1,
        "amend": 1,
        "print": 1,
        "email": 1,
        "share": 1,
        "export": 1,
        "report": 1,
        "select": 1
    }
    
    doctypes = frappe.get_all("DocType", filters={"module": school_module}, fields=["name"])
    
    for dt in doctypes:
        doctype = dt.name
        for role in roles:
            # Check if full perm exists for this role/permlevel 0
            existing = get_matching_custom_permissions(doctype, role, permlevel=0)
            if not existing or not all(existing[0].get(k, 0) == v for k, v in full_perms.items()):
                # Delete existing partial
                if existing:
                    for perm in existing:
                        perm.delete()
                # Add full
                perm = frappe.get_doc({
                    "doctype": "Custom DocPerm",
                    "parent": doctype,
                    "parentfield": "permissions",
                    "parenttype": "DocType",
                    "role": role,
                    "permlevel": 0,
                    **full_perms
                }).insert()
                frappe.db.commit()
                frappe.msgprint(f"Added full perms for {role} on {doctype}")
    
    frappe.msgprint("School full permissions patch completed.")

