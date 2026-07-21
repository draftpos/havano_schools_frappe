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
		
	grade_points = {}
	try:
		pts_rows = frappe.get_all("A Level Grade Point", fields=["grade", "points"], filters={"parent": "School Settings"}, ignore_permissions=True)
		for row in pts_rows:
			if row.grade:
				grade_points[str(row.grade).upper().strip()] = row.points
	except Exception:
		pass
	context.grade_points = grade_points
	
	grading_items = []

	try:
		# Fetch all Grading Score Items across the system
		items = frappe.get_all("Grading Score Item", 
			fields=["parent", "parentfield", "from_percent", "to_percent", "grade", "unit", "status"],
			order_by="from_percent desc",
			ignore_permissions=True
		)

		if items:
			for item in items:
				grading_items.append({
					"parent": item.get("parent", ""),
					"parentfield": item.get("parentfield", ""),
					"from_percent": item.get("from_percent", 0),
					"to_percent": item.get("to_percent", 100),
					"grade": item.get("grade", ""),
					"unit": item.get("unit", ""),
					"status": item.get("status", "")
				})
		
		frappe.log_error("Portal Grading Debug 3", f"Final grading_items length: {len(grading_items)}")

	except Exception as e:
		frappe.log_error("Portal Grading Fetch Error", str(e))

	context.grading_items = grading_items
