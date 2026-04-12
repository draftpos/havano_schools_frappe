import frappe

def execute():
    ROLES = ['System Manager', 'School User', 'School Administrator']

    FULL_PERMS = {
        "read": 1, "write": 1, "create": 1, "delete": 1,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "import": 1,
        "share": 1, "print": 1, "email": 1,
        "permlevel": 0, "if_owner": 0
    }

    all_doctypes = frappe.get_all(
        'DocType',
        filters={'istable': 0},
        fields=['name', 'is_submittable'],
        limit_page_length=0
    )

    fixed = 0
    errors = 0

    for dt in all_doctypes:
        try:
            for role in ROLES:
                perms = FULL_PERMS.copy()
                if dt.is_submittable:
                    perms['submit'] = 1
                    perms['cancel'] = 1
                    perms['amend'] = 1

                existing = frappe.db.get_value(
                    'Custom DocPerm',
                    {'parent': dt.name, 'role': role, 'permlevel': 0},
                    'name'
                )

                if existing:
                    frappe.db.set_value('Custom DocPerm', existing, perms)
                else:
                    cdp = frappe.new_doc('Custom DocPerm')
                    cdp.parent = dt.name
                    cdp.parenttype = 'DocType'
                    cdp.parentfield = 'permissions'
                    cdp.role = role
                    for k, v in perms.items():
                        setattr(cdp, k, v)
                    cdp.insert(ignore_permissions=True)

            print(f"  SUCCESS: {dt.name}")
            fixed += 1

        except Exception as e:
            print(f"  ERROR: {dt.name}: {e}")
            errors += 1

    frappe.db.commit()
    print(f"Done — {fixed} doctypes updated, {errors} errors")
