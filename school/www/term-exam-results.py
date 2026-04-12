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
		frappe.response.update(get_exam_results_json())
		return


def get_exam_results_json():
	user = frappe.session.user

	student = frappe.db.get_value(
		"Student",
		{"user": user},
		["name", "student_name", "student_class", "section"],
		as_dict=1
	)

	if not student:
		return {"terms": [], "student_id": None, "error": "Student record not found"}

	# Get all exam schedules for this student's class/section
	schedule_filters = {"student_class": student.student_class}
	if student.section:
		schedule_filters["section"] = student.section

	schedules = frappe.get_all(
		"Exam Schedule",
		filters=schedule_filters,
		fields=["name", "term", "exam", "subject", "date", "max_marks", "min_marks", "student_class", "section"],
		order_by="date asc"
	)

	if not schedules:
		return {
			"terms": [],
			"student_id": student.name,
			"student_name": student.student_name
		}

	# Group results by term -> exam
	terms_map = defaultdict(lambda: {"term": "", "exams": defaultdict(list)})

	for sched in schedules:
		# Get ONLY what the teacher entered for this student — no fallback calculations
		score_row = frappe.db.get_value(
			"Exam Schedule Item",
			{
				"parent": sched.name,
				"student_admission_no": student.name
			},
			["marks_obtained", "grade", "status"],
			as_dict=1
		)

		# Skip if teacher hasn't entered this student's marks yet
		if not score_row:
			continue

		# Use exactly what was saved — marks, grade, status as entered by teacher
		marks_obtained = score_row.marks_obtained  # could be 0, None
		grade = score_row.grade or ""              # exactly as set by teacher
		status = score_row.status or ""            # Pass / Moderate / Failed as set

		max_marks = sched.max_marks or 0
		min_marks = sched.min_marks or 0

		# Only calculate percentage from actual marks — no grade inference
		if marks_obtained is not None and max_marks:
			percentage = round((marks_obtained / max_marks) * 100, 1)
		else:
			percentage = None  # Not yet marked

		term = sched.term or "No Term"
		exam = sched.exam or "Exam"

		terms_map[term]["term"] = term
		terms_map[term]["exams"][exam].append({
			"subject": sched.subject or "",
			"date": str(sched.date) if sched.date else "",
			"marks_obtained": marks_obtained if marks_obtained is not None else "",
			"max_marks": max_marks,
			"min_marks": min_marks,
			"percentage": percentage,
			"grade": grade,       # teacher-set grade, not calculated
			"status": status,     # teacher-set status, not calculated
			"schedule": sched.name
		})

	# Build final list grouped by term -> exam
	terms_list = []
	for term_name, term_data in terms_map.items():
		exams_list = []

		for exam_name, subjects in term_data["exams"].items():
			# Sort subjects alphabetically
			subjects_sorted = sorted(subjects, key=lambda s: s["subject"])

			# Totals — only sum rows that have actual marks entered
			marked = [s for s in subjects_sorted if s["marks_obtained"] != ""]
			total_obtained = sum(s["marks_obtained"] for s in marked)
			total_max = sum(s["max_marks"] for s in marked)
			overall_pct = round((total_obtained / total_max) * 100, 1) if total_max else None

			exams_list.append({
				"exam": exam_name,
				"subjects": subjects_sorted,
				"total_obtained": total_obtained,
				"total_max": total_max,
				"overall_percentage": overall_pct,  # None if no marks entered yet
				"subjects_marked": len(marked),
				"subjects_total": len(subjects_sorted)
			})

		exams_list.sort(key=lambda e: e["exam"])
		terms_list.append({
			"term": term_name,
			"exams": exams_list
		})

	# Sort terms alphabetically (term names like "Term 1", "Term 2" sort correctly)
	terms_list.sort(key=lambda t: t["term"])

	return {
		"terms": terms_list,
		"student_id": student.name,
		"student_name": student.student_name,
		"student_class": student.student_class,
		"section": student.section or ""
	}