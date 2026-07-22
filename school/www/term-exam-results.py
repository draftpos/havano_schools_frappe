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
		frappe.flags.ignore_permissions = True
		rows = frappe.db.sql("""
			SELECT grade, points FROM `tabA Level Grade Point`
		""", as_dict=True)
		for r in rows:
			if r.get("grade"):
				g_str = str(r.get("grade")).upper().strip()
				grade_points[g_str] = float(r.get("points") or 0)
	except Exception as e:
		frappe.log_error("Portal Grade Points Fetch Error", str(e))
	finally:
		frappe.flags.ignore_permissions = False
	context.grade_points = grade_points
	
	grading_items = []

	try:
		frappe.flags.ignore_permissions = True
		items = frappe.db.sql("""
			SELECT parent, parentfield, from_percent, to_percent, grade, unit, status
			FROM `tabGrading Score Item`
			ORDER BY from_percent DESC
		""", as_dict=1)

		if items:
			for item in items:
				grading_items.append({
					"parent": item.get("parent", "") or "",
					"parentfield": item.get("parentfield", "") or "",
					"from_percent": float(item.get("from_percent") or 0),
					"to_percent": float(item.get("to_percent") if item.get("to_percent") is not None else 100),
					"grade": item.get("grade", "") or "",
					"unit": item.get("unit", "") or "",
					"status": item.get("status", "") or ""
				})
		
		frappe.log_error("Portal Grading Debug 3", f"Final grading_items length: {len(grading_items)}")

	except Exception as e:
		frappe.log_error("Portal Grading Fetch Error", str(e))
	finally:
		frappe.flags.ignore_permissions = False

	context.grading_items = grading_items
