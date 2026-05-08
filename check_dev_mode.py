import frappe
frappe.init(site="v15.local")
frappe.connect()
print(f"Developer Mode: {frappe.conf.developer_mode}")
