import frappe

def execute():
    # Doctypes Teacher role needs access to
    teacher_doctypes = [
        "Term",
        "Kanban Board",
        "Exam Schedule",
        "Exam Schedule Item",
        "Exam Result",
        "Exam",
        "Exam Type",
        "Home Schedule",
        "Home Schedule Item",
        "Homework",
        "Homework Type",
        "Test Schedule",
        "Test Schedule Item",
        "Inclass Test",
        "Student",
        "Student Class",
        "Section",
        "Subject",
        "Subject Group",
        "Student Attendance",
        "Grading Score",
        "Grade",
        "Academic Year",
        "Assignment Submission",
        "Assign Class to Teacher",
        "Assign Subjects to Teacher",
        "List Filter",
        "Notification Log",
    ]

    TEACHER_PERMS = {
        "read": 1, "write": 1, "create": 1, "delete": 0,
        "submit": 0, "cancel": 0, "amend": 0,
        "report": 1, "export": 1, "import": 0,
        "share": 1, "print": 1, "email": 1,
        "permlevel": 0, "if_owner": 0
    }

    fixed = 0
    for dt_name in teacher_doctypes:
        try:
            # Check if doctype exists
            if not frappe.db.exists("DocType", dt_name):
                print(f"  SKIP (not found): {dt_name}")
                continue

            existing = frappe.db.get_value(
                'Custom DocPerm',
                {'parent': dt_name, 'role': 'Teacher', 'permlevel': 0},
                'name'
            )

            if existing:
                frappe.db.set_value('Custom DocPerm', existing, TEACHER_PERMS)
            else:
                cdp = frappe.new_doc('Custom DocPerm')
                cdp.parent = dt_name
                cdp.parenttype = 'DocType'
                cdp.parentfield = 'permissions'
                cdp.role = 'Teacher'
                for k, v in TEACHER_PERMS.items():
                    setattr(cdp, k, v)
                cdp.insert(ignore_permissions=True)

            print(f"  SUCCESS: {dt_name}")
            fixed += 1

        except Exception as e:
            print(f"  ERROR: {dt_name}: {e}")

    frappe.db.commit()
    print(f"\nDone — {fixed} doctypes updated for Teacher role")
# Already handled — just re-run with List Filter added
