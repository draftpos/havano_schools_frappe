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
	grading_items = []
	try:
		# Use get_all on the child table directly with ignore_permissions to safely fetch data
		items = frappe.get_all("Grading Score Item", 
			filters={"parent": "STD"}, 
			fields=["from_percent", "to_percent", "grade", "status"],
			order_by="from_percent desc",
			ignore_permissions=True
		)
		
		if not items:
			# Fallback to the latest Grading Score if STD is empty
			latest_parent = frappe.get_all("Grading Score", order_by="modified desc", limit=1, ignore_permissions=True)
			if latest_parent:
				items = frappe.get_all("Grading Score Item",
					filters={"parent": latest_parent[0].name},
					fields=["from_percent", "to_percent", "grade", "status"],
					order_by="from_percent desc",
					ignore_permissions=True
				)

		if items:
			for item in items:
				grading_items.append({
					"from_percent": item.get("from_percent"),
					"to_percent": item.get("to_percent"),
					"grade": item.get("grade"),
					"status": item.get("status")
				})
	except Exception as e:
		frappe.log_error("Portal Grading Fetch Error", str(e))

	context.grading_items = grading_items
