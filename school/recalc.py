import frappe

def execute():
    frappe.flags.ignore_permissions = True
    reports = frappe.get_all("Term Exam Report", pluck="name")
    count = 0
    for r in reports:
        doc = frappe.get_doc("Term Exam Report", r)
        doc.auto_fill_grades_and_comments()
        doc.save(ignore_permissions=True)
        count += 1
    frappe.db.commit()
    print(f"Successfully recalculated {count} reports")
