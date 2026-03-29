import frappe

def execute():
    field_name = "Sales Invoice-custom_shift_number"
    if frappe.db.exists("Custom Field", field_name):
        frappe.delete_doc("Custom Field", field_name, force=1)
        frappe.db.commit()
        frappe.msgprint(f"Deleted invalid custom field: {field_name}")
    else:
        frappe.msgprint(f"Custom field {field_name} not found, nothing to delete.")
