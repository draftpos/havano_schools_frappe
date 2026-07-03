import frappe

def execute():
    val = frappe.db.get_value("Print Format", "Term Exam Report Card", "html")
    print(val)
