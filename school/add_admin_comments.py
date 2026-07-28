import frappe

def create_admin_comments():
    frappe.flags.in_install = True

    if not frappe.db.exists("DocType", "Admin Comment Setting"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "Admin Comment Setting",
            "module": "School Management",
            "custom": 0,
            "istable": 1,
            "editable_grid": 1,
            "fields": [
                {"fieldname": "comment_type", "label": "Type of Comment", "fieldtype": "Select", "options": "Passed all subjects\nFailed\nModerate\nExcellent", "reqd": 1, "in_list_view": 1},
                {"fieldname": "comment", "label": "Comment", "fieldtype": "Small Text", "reqd": 1, "in_list_view": 1}
            ]
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print("Created Admin Comment Setting DocType")

    school_settings = frappe.get_doc("DocType", "School Settings")
    has_section = any(f.fieldname == "admin_comments_section" for f in school_settings.fields)
    has_table = any(f.fieldname == "admin_comment_settings" for f in school_settings.fields)

    if not has_section or not has_table:
        if not has_section:
            school_settings.append("fields", {
                "fieldname": "admin_comments_section",
                "fieldtype": "Section Break",
                "label": "Admin Comments (Auto)"
            })
        if not has_table:
            school_settings.append("fields", {
                "fieldname": "admin_comment_settings",
                "fieldtype": "Table",
                "label": "Admin Comment Settings",
                "options": "Admin Comment Setting"
            })
        school_settings.save(ignore_permissions=True)
        frappe.db.commit()
        print("Updated School Settings DocType")
    else:
        print("School Settings already has Admin Comment Settings")

if __name__ == "__main__":
    frappe.init(site="v15.local")
    frappe.connect()
    create_admin_comments()
