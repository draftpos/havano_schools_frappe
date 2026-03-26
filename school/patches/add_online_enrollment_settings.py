import frappe

def execute():
    fields_to_add = [
        {"dt":"School Settings","fieldname":"online_enrollment_section","fieldtype":"Section Break","label":"Online Enrollment Settings","insert_after":"bill_on_registration"},
        {"dt":"School Settings","fieldname":"allow_online_enrollment","fieldtype":"Check","label":"Allow Online Enrollment","insert_after":"online_enrollment_section","description":"Enable the public online student registration portal"},
        {"dt":"School Settings","fieldname":"online_enrollment_require_approval","fieldtype":"Check","label":"Require Approval Before Creating Student","insert_after":"allow_online_enrollment","depends_on":"eval:doc.allow_online_enrollment==1","description":"Pending=manual approval, Unchecked=student created immediately on submit"},
    ]
    for field in fields_to_add:
        if not frappe.db.exists("Custom Field",{"dt":field["dt"],"fieldname":field["fieldname"]}):
            cf = frappe.new_doc("Custom Field")
            cf.update(field)
            cf.insert(ignore_permissions=True)
            print(f"Added: {field['fieldname']}")
        else:
            print(f"Exists: {field['fieldname']}, skipping")

    # Fix the status field in Fees Structure Defaults child table
    # The child doctype is likely "Fees Structure Default" — update options to match Student statuses
    fees_default_dt = None
    # Try to find the child table doctype name
    for dt_name in ["Fees Structure Default", "Fees Structure Defaults"]:
        if frappe.db.exists("DocType", dt_name):
            fees_default_dt = dt_name
            break

    if fees_default_dt:
        status_field = frappe.db.get_value(
            "DocField",
            {"parent": fees_default_dt, "fieldname": "status"},
            "name"
        )
        if status_field:
            frappe.db.set_value("DocField", status_field, "options",
                "\nActive\nInactive\nGraduated\nDropped Out")
            print(f"Fixed status options on {fees_default_dt}")
        else:
            print(f"WARNING: 'status' field not found on {fees_default_dt}. Check fieldname.")
    else:
        print("WARNING: Fees Structure Default child doctype not found. Please manually fix status options to: Active, Inactive, Graduated, Dropped Out")

    frappe.db.commit()
    print("Done.")
