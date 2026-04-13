import frappe
from collections import defaultdict

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/portal-login"
		raise frappe.Redirect

	context.no_cache = 1
	context.show_sidebar = False

	if frappe.form_dict.get("format") == "json":
		frappe.response.update(get_reports_json())
		return


def get_reports_json():
	user = frappe.session.user

	student = frappe.db.get_value(
		"Student",
		{"user": user},
		["name", "student_name", "student_class", "section"],
		as_dict=1
	)

	if not student:
		return {"reports": [], "student_id": None, "error": "Student record not found"}

	# Get all submitted Term Exam Reports for this student's class/section
	report_filters = {
		"student_class": student.student_class,
		"docstatus": 1
	}

	reports = frappe.get_all(
		"Term Exam Report",
		filters=report_filters,
		fields=["name", "report_name", "term", "academic_year", "report_date",
				"opening_date", "cost_center", "total_subjects", "total_students",
				"student_class", "section"],
		order_by="report_date desc"
	)

	# Filter by section — include reports with no section or matching section
	if student.section:
		reports = [r for r in reports if not r.section or r.section == student.section]

	result_reports = []

	for report in reports:
		# Get this student's rows from the child table
		rows = frappe.get_all(
			"Term Exam Result Item",
			filters={"parent": report.name, "student": student.name},
			fields=["subject", "exam", "marks_obtained", "max_marks",
					"percentage", "grade", "status", "remarks"],
			order_by="subject asc"
		)

		if not rows:
			continue

		# Calculate overall totals from actual data
		marked = [r for r in rows if r.marks_obtained is not None]
		total_obtained = sum(r.marks_obtained or 0 for r in marked)
		total_max = sum(r.max_marks or 0 for r in marked)
		overall_pct = round((total_obtained / total_max * 100), 1) if total_max else None

		# Get school name from cost center
		school_name = ""
		if report.cost_center:
			school_name = frappe.db.get_value("Cost Center", report.cost_center, "cost_center_name") or report.cost_center

		result_reports.append({
			"name": report.name,
			"report_name": report.report_name,
			"term": report.term,
			"academic_year": report.academic_year,
			"report_date": str(report.report_date) if report.report_date else "",
			"opening_date": str(report.opening_date) if report.opening_date else "",
			"school_name": school_name,
			"student_class": report.student_class,
			"section": report.section or "",
			"subjects": [dict(r) for r in rows],
			"total_obtained": total_obtained,
			"total_max": total_max,
			"overall_percentage": overall_pct,
		})

	return {
		"reports": result_reports,
		"student_id": student.name,
		"student_name": student.student_name,
		"student_class": student.student_class,
		"section": student.section or ""
	}