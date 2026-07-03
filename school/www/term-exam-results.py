import frappe

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/portal-login"
		raise frappe.Redirect

	context.no_cache = 1
	if frappe.form_dict.get("from") == "admin":
		context.show_sidebar = False
	else:
		context.show_sidebar = True
		context.website_sidebar = "Student Portal"
	grading_items = []

	try:
		# Fetch all Grading Score Items across the system, ignoring STD if it exists since they want standalone
		items = frappe.get_all("Grading Score Item", 
			filters=[["parent", "!=", "STD"]], 
			fields=["from_percent", "to_percent", "grade", "status"],
			order_by="from_percent desc",
			ignore_permissions=True
		)
		
		# If they literally deleted STD and all others are empty, just fetch everything
		if not items:
			items = frappe.get_all("Grading Score Item", 
				fields=["from_percent", "to_percent", "grade", "status"],
				order_by="from_percent desc",
				ignore_permissions=True
			)

		if items:
			for item in items:
				grading_items.append({
					"from_percent": item.get("from_percent", 0),
					"to_percent": item.get("to_percent", 100),
					"grade": item.get("grade", ""),
					"status": item.get("status", "")
				})
		
		frappe.log_error("Portal Grading Debug 3", f"Final grading_items length: {len(grading_items)}")

	except Exception as e:
		frappe.log_error("Portal Grading Fetch Error", str(e))

	context.grading_items = grading_items
