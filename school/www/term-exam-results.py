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
		# Direct SQL fetch to bypass any frappe.get_doc permission errors for portal users
		items = frappe.db.sql("""
			SELECT from_percent, to_percent, grade, status 
			FROM `tabGrading Score Item`
			WHERE parent = 'STD'
			ORDER BY from_percent DESC
		""", as_dict=True)
		
		if not items:
			# Fallback to the latest Grading Score if STD is empty
			latest_parent = frappe.db.sql("SELECT name FROM `tabGrading Score` ORDER BY modified DESC LIMIT 1")
			if latest_parent and latest_parent[0][0]:
				items = frappe.db.sql("""
					SELECT from_percent, to_percent, grade, status 
					FROM `tabGrading Score Item`
					WHERE parent = %s
					ORDER BY from_percent DESC
				""", (latest_parent[0][0],), as_dict=True)

		if items:
			for item in items:
				grading_items.append({
					"from_percent": item.from_percent,
					"to_percent": item.to_percent,
					"grade": item.grade,
					"status": item.status
				})
	except Exception as e:
		frappe.log_error("Portal Grading Fetch Error", str(e))

	context.grading_items = grading_items
