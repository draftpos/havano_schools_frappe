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
		# Try to fetch 'STD' first to match backend term_exam_report.py grading logic
		if frappe.db.exists("Grading Score", "STD"):
			gs = frappe.get_doc("Grading Score", "STD")
		else:
			# Fallback to the most recently modified grading score
			scale_name = frappe.get_all("Grading Score", limit=1, order_by="modified desc", fields=["name"])
			if scale_name:
				gs = frappe.get_doc("Grading Score", scale_name[0].name)
			else:
				gs = None
		
		if gs:
			for item in gs.grading_items:
				grading_items.append({
					"from_percent": item.from_percent,
					"to_percent": item.to_percent,
					"grade": item.grade,
					"status": item.status
				})
	except Exception:
		pass

	context.grading_items = grading_items
