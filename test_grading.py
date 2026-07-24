import frappe
frappe.init(site='v15.local')
frappe.connect()
items = frappe.db.sql(" SELECT parent parentfield from_percent to_percent grade unit status FROM \
