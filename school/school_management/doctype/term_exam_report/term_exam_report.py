
import frappe
from frappe.model.document import Document
from frappe import _
from collections import defaultdict
import qrcode
import io
import base64


def generate_qr_base64(data):
	qr = qrcode.QRCode(version=1, box_size=6, border=2)
	qr.add_data(data)
	qr.make(fit=True)
	img = qr.make_image(fill_color="black", back_color="white")
	buf = io.BytesIO()
	img.save(buf, format="PNG")
	buf.seek(0)
	return base64.b64encode(buf.read()).decode("utf-8")


class TermExamReport(Document):

	def before_save(self):
		if self.docstatus == 0:
			self.calculate_totals()

	def calculate_totals(self):
		students = set(r.student for r in self.term_exam_results if r.student)
		subjects = set(r.subject for r in self.term_exam_results if r.subject)
		self.total_students = len(students)
		self.total_subjects = len(subjects)

	def get_verification_url(self):
		return f"{frappe.utils.get_url()}/term-exam-results?report={self.name}"

	def get_qr_base64(self):
		return generate_qr_base64(self.get_verification_url())

	def on_submit(self):
		self.send_report_emails()

	def send_report_emails(self):
		"""Group results by student and send individual report card emails."""
		student_rows = defaultdict(list)
		for row in self.term_exam_results:
			if row.student:
				student_rows[row.student].append(row)

		if not student_rows:
			frappe.msgprint(_("No results to send."), indicator="orange")
			return

		school_name = ""
		if self.cost_center:
			cc = frappe.db.get_value("Cost Center", self.cost_center, "cost_center_name")
			school_name = cc or self.cost_center

		qr_b64 = self.get_qr_base64()
		sent = 0
		failed = 0

		for student_id, rows in student_rows.items():
			try:
				student_doc = frappe.get_doc("Student", student_id)
				student_name = (
					" ".join(filter(None, [
						student_doc.get("first_name"),
						student_doc.get("second_name"),
						student_doc.get("last_name")
					])) or student_doc.get("full_name") or student_id
				)

				email = (
					student_doc.get("father_email") or
					student_doc.get("mother_email") or
					student_doc.get("guardian_email") or
					student_doc.get("portal_email") or
					student_doc.get("student_email_id") or
					student_doc.get("email")
				)

				if not email:
					frappe.log_error(f"No email for student {student_id}", "Term Exam Report")
					failed += 1
					continue

				html = build_report_html(
					student_name=student_name,
					student_id=student_id,
					rows=rows,
					doc=self,
					school_name=school_name,
					qr_b64=qr_b64
				)

				frappe.sendmail(
					recipients=[email],
					subject=f"Term Report Card — {student_name} | {self.term} | {self.academic_year}",
					message=html,
					reference_doctype=self.doctype,
					reference_name=self.name,
					now=True
				)
				sent += 1

			except Exception:
				frappe.log_error(frappe.get_traceback(), f"Term Exam Report Email: {student_id}")
				failed += 1

		frappe.msgprint(
			_(f"Report cards sent: {sent}" + (f" | Failed: {failed} (check Error Log)" if failed else "")),
			indicator="green" if not failed else "orange"
		)


def build_report_html(student_name, student_id, rows, doc, school_name="", qr_b64=None):
	"""Build full HTML report card for one student — all subjects."""

	rows_sorted = sorted(rows, key=lambda r: r.subject or "")

	marked = [r for r in rows_sorted if r.marks_obtained is not None and r.marks_obtained != ""]
	total_obtained = sum(r.marks_obtained or 0 for r in marked)
	total_max = sum(r.max_marks or 0 for r in marked)
	overall_pct = round((total_obtained / total_max * 100), 1) if total_max else 0

	subject_rows_html = ""
	for r in rows_sorted:
		marks = r.marks_obtained if r.marks_obtained is not None else "—"
		max_m = r.max_marks or "—"
		pct = f"{r.percentage:.1f}%" if r.percentage else "—"
		grade = r.grade or "—"
		status = r.status or "—"
		remarks = r.remarks or ""
		status_color = "#27ae60" if status == "Pass" else "#f59e0b" if status == "Moderate" else "#e74c3c" if status == "Failed" else "#64748b"

		subject_rows_html += f"""
		<tr>
			<td style="padding:8px 10px;border-bottom:1px solid #e2e8f0">{r.subject or ''}</td>
			<td style="padding:8px 10px;border-bottom:1px solid #e2e8f0;color:#64748b;font-size:12px">{r.exam or ''}</td>
			<td style="text-align:center;padding:8px 10px;border-bottom:1px solid #e2e8f0">{marks}</td>
			<td style="text-align:center;padding:8px 10px;border-bottom:1px solid #e2e8f0">{max_m}</td>
			<td style="text-align:center;padding:8px 10px;border-bottom:1px solid #e2e8f0">{pct}</td>
			<td style="text-align:center;padding:8px 10px;border-bottom:1px solid #e2e8f0;font-weight:700">{grade}</td>
			<td style="text-align:center;padding:8px 10px;border-bottom:1px solid #e2e8f0;color:{status_color};font-weight:600;font-size:12px">{status}</td>
			<td style="padding:8px 10px;border-bottom:1px solid #e2e8f0;font-size:12px;color:#64748b">{remarks}</td>
		</tr>"""

	overall_color = "#27ae60" if overall_pct >= 50 else "#e74c3c"
	verification_url = doc.get_verification_url()

	qr_html = ""
	if qr_b64:
		qr_html = f"""
		<div style="text-align:center">
			<img src="data:image/png;base64,{qr_b64}" width="85" height="85" alt="QR"/>
			<p style="font-size:10px;color:#64748b;margin:3px 0 0">Scan to verify</p>
		</div>"""

	opening_row = f"<p style='margin:2px 0'><strong>School Opens:</strong> {doc.opening_date}</p>" if doc.opening_date else ""

	return f"""
<div style="font-family:Arial,sans-serif;max-width:750px;margin:auto;border:2px solid #1e3a5f;border-radius:8px;overflow:hidden">
	<div style="background:#1e3a5f;color:white;padding:18px 28px;text-align:center">
		<h2 style="margin:0;font-size:22px;letter-spacing:1px">{school_name or 'School'}</h2>
		<h3 style="margin:6px 0 0;font-size:13px;font-weight:400;opacity:0.85">TERM EXAMINATION REPORT CARD</h3>
	</div>
	<div style="background:#eef2f7;padding:14px 28px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;border-bottom:1px solid #cbd5e1">
		<div>
			<p style="margin:3px 0;font-size:14px"><strong>Student:</strong> {student_name}</p>
			<p style="margin:3px 0;font-size:13px;color:#475569"><strong>Admission No:</strong> {student_id}</p>
			<p style="margin:3px 0;font-size:13px;color:#475569"><strong>Class:</strong> {doc.student_class}{(' &nbsp;|&nbsp; Section: ' + doc.section) if doc.section else ''}</p>
		</div>
		<div style="text-align:right">
			<p style="margin:3px 0;font-size:13px"><strong>Academic Year:</strong> {doc.academic_year}</p>
			<p style="margin:3px 0;font-size:13px"><strong>Term:</strong> {doc.term}</p>
			<p style="margin:3px 0;font-size:13px"><strong>Report Date:</strong> {doc.report_date}</p>
		</div>
	</div>
	<div style="padding:0 20px">
		<table style="width:100%;border-collapse:collapse;font-size:13px;margin:14px 0">
			<thead>
				<tr style="background:#1e3a5f;color:white">
					<th style="padding:9px 10px;text-align:left">Subject</th>
					<th style="padding:9px 10px;text-align:left">Exam</th>
					<th style="padding:9px 10px;text-align:center">Marks</th>
					<th style="padding:9px 10px;text-align:center">Max</th>
					<th style="padding:9px 10px;text-align:center">%</th>
					<th style="padding:9px 10px;text-align:center">Grade</th>
					<th style="padding:9px 10px;text-align:center">Status</th>
					<th style="padding:9px 10px;text-align:left">Remarks</th>
				</tr>
			</thead>
			<tbody>{subject_rows_html}</tbody>
			<tfoot>
				<tr style="background:#eef2f7;font-weight:700">
					<td colspan="2" style="padding:9px 10px">OVERALL TOTAL</td>
					<td style="text-align:center;padding:9px 10px">{total_obtained}</td>
					<td style="text-align:center;padding:9px 10px">{total_max}</td>
					<td style="text-align:center;padding:9px 10px;color:{overall_color}">{overall_pct}%</td>
					<td style="text-align:center;padding:9px 10px">—</td>
					<td style="text-align:center;padding:9px 10px"></td>
					<td></td>
				</tr>
			</tfoot>
		</table>
	</div>
	<div style="padding:8px 20px 12px;display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:12px">
		<div style="font-size:11px;color:#64748b">
			<strong>Grade Key (as set by school):</strong> Grades and status are entered by subject teachers.<br>
			Pass ≥ passing mark &nbsp;|&nbsp; Moderate = borderline &nbsp;|&nbsp; Failed = below passing mark
		</div>
		{qr_html}
	</div>
	<div style="padding:16px 28px;display:flex;justify-content:space-between">
		<div style="text-align:center;width:28%">
			<div style="border-top:1px solid #334155;margin-top:36px;padding-top:5px;font-size:12px;color:#475569">Class Teacher</div>
		</div>
		<div style="text-align:center;width:28%">
			<div style="border-top:1px solid #334155;margin-top:36px;padding-top:5px;font-size:12px;color:#475569">Head Teacher</div>
		</div>
		<div style="text-align:center;width:28%">
			<div style="border-top:1px solid #334155;margin-top:36px;padding-top:5px;font-size:12px;color:#475569">Parent / Guardian</div>
		</div>
	</div>
	<div style="background:#1e3a5f;color:#cbd5e1;padding:10px 28px;font-size:11px">
		{opening_row}
		<p style="margin:2px 0">Verify at: <a href="{verification_url}" style="color:#93c5fd">{verification_url}</a></p>
		<p style="margin:2px 0">Report ID: {doc.name} &nbsp;|&nbsp; Official school document — do not alter.</p>
	</div>
</div>"""


@frappe.whitelist()
def get_student_reports():
	"""Fetch all submitted term reports for the logged-in student."""
	user = frappe.session.user

	student = frappe.db.get_value(
		"Student",
		{"portal_email": user},
		["name", "student_name", "student_class", "section"],
		as_dict=1
	)

	if not student:
		return {"reports": [], "student_id": None, "error": "Student record not found"}

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

	if student.section:
		reports = [r for r in reports if not r.section or r.section == student.section]

	result_reports = []

	for report in reports:
		rows = frappe.get_all(
			"Term Exam Result Item",
			filters={"parent": report.name, "student": student.name},
			fields=["subject", "exam", "marks_obtained", "max_marks",
					"percentage", "grade", "status", "remarks"],
			order_by="subject asc"
		)

		if not rows:
			continue

		marked = [r for r in rows if r.marks_obtained is not None]
		total_obtained = sum(r.marks_obtained or 0 for r in marked)
		total_max = sum(r.max_marks or 0 for r in marked)
		overall_pct = round((total_obtained / total_max * 100), 1) if total_max else None

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
"student_name": getattr(student, "student_name", getattr(student, "full_name", student.name)),
		"student_class": student.student_class,
		"section": student.section or ""
	}


@frappe.whitelist()
def fetch_results(report_name):
	doc = frappe.get_doc("Term Exam Report", report_name)

	if not doc.term or not doc.student_class:
		frappe.throw(_("Please set Term and Class before fetching results."))

	class_section_filters = {"class": doc.student_class}
	if doc.section:
		class_section_filters["section"] = doc.section

	subject_links = frappe.get_all(
		"Subject Class and Section",
		filters=class_section_filters,
		fields=["parent", "class", "section"],
	)

	if not subject_links:
		subject_links = frappe.get_all(
			"Subject Class and Section",
			filters={"class": doc.student_class},
			fields=["parent", "class", "section"],
		)
		if not subject_links:
			frappe.throw(_("No subjects found for class {0}.").format(doc.student_class))

	subject_names = list(set([s.parent for s in subject_links]))

	subjects = frappe.get_all(
		"Subject",
		filters={"name": ["in", subject_names]},
		fields=["name", "subject_name"],
		order_by="subject_name asc"
	)

	if not subjects:
		frappe.throw(_("No subjects found for this class/section."))

	student_filters = {"student_class": doc.student_class}
	if doc.section:
		student_filters["section"] = doc.section

	students = frappe.get_all(
		"Student",
		filters=student_filters,
		fields=["name", "first_name", "second_name", "last_name", "full_name"],
		order_by="first_name asc"
	)

	if not students:
		frappe.throw(_("No students found for this class/section."))

	sched_filters = {
		"term": doc.term,
		"student_class": doc.student_class,
		"subject": ["in", subject_names]
	}
	if doc.section:
		sched_filters["section"] = doc.section

	schedules = frappe.get_all(
		"Exam Schedule",
		filters=sched_filters,
		fields=["name", "subject", "exam", "max_marks", "min_marks"]
	)

	subject_schedule_map = defaultdict(list)
	for s in schedules:
		subject_schedule_map[s.subject].append(s)

	rows = []
	for student in students:
		student_name = " ".join(filter(None, [
			student.get("first_name"),
			student.get("second_name"),
			student.get("last_name")
		])) or student.get("full_name") or student.name

		for subject in subjects:
			subj_schedules = subject_schedule_map.get(subject.name, [])

			if not subj_schedules:
				rows.append({
					"student": student.name,
					"student_name": student_name,
					"subject": subject.name,
					"exam": "",
					"marks_obtained": None,
					"max_marks": None,
					"percentage": None,
					"grade": "",
					"status": "",
					"remarks": ""
				})
				continue

			sched = subj_schedules[-1]

			score = frappe.db.get_value(
				"Exam Schedule Item",
				{"parent": sched.name, "student_admission_no": student.name},
				["marks_obtained", "grade", "status"],
				as_dict=1
			)

			marks = score.marks_obtained if score else None
			max_m = sched.max_marks or None
			pct = round((marks / max_m * 100), 1) if (marks is not None and max_m) else None
			grade = score.grade if score else ""
			status = score.status if score else ""

			rows.append({
				"student": student.name,
				"student_name": student_name,
				"subject": subject.name,
				"exam": sched.exam or "",
				"marks_obtained": marks,
				"max_marks": max_m,
				"percentage": pct,
				"grade": grade,
				"status": status,
				"remarks": ""
			})

	return {
		"rows": rows,
		"total_students": len(students),
		"total_subjects": len(subjects)
	}


@frappe.whitelist(allow_guest=True)
def verify_report(report):
	"""Public verification endpoint — called from QR scan."""
	try:
		doc = frappe.get_doc("Term Exam Report", report)
		if doc.docstatus != 1:
			return {"valid": False, "message": "This report has not been officially submitted."}
		return {
			"valid": True,
			"report_name": doc.report_name,
			"term": doc.term,
			"academic_year": doc.academic_year,
			"student_class": doc.student_class,
			"section": doc.section or "",
			"report_date": str(doc.report_date),
			"total_students": doc.total_students,
			"total_subjects": doc.total_subjects,
			"issued_by": frappe.db.get_value("Cost Center", doc.cost_center, "cost_center_name") if doc.cost_center else "School",
			"message": "✓ This is a genuine official report card."
		}
	except frappe.DoesNotExistError:
		return {"valid": False, "message": "Report not found. This document may be invalid."}


@frappe.whitelist()
def get_student_count(student_class, section=None):
	student_filters = {"student_class": student_class}
	if section:
		student_filters["section"] = section

	students = frappe.get_all("Student", filters=student_filters, fields=["name"])

	subject_filters = {"class": student_class}
	if section:
		subject_filters["section"] = section

	subject_links = frappe.get_all(
		"Subject Class and Section",
		filters=subject_filters,
		fields=["parent"]
	)
	if not subject_links:
		subject_links = frappe.get_all(
			"Subject Class and Section",
			filters={"class": student_class},
			fields=["parent"]
		)

	subject_names = list(set([s.parent for s in subject_links]))

	return {
		"students": len(students),
		"subjects": len(subject_names)
	}


@frappe.whitelist()
def get_student_pdf(report_name, student_id):
	"""Generate a PDF report card for one student from a Term Exam Report."""
	import weasyprint

	user = frappe.session.user
	is_student = frappe.db.get_value("Student", {"user": user, "name": student_id}, "name")
	if not is_student:
		parent = frappe.db.get_value("Parent", {"portal_email": frappe.db.get_value("User", user, "email")}, "name")
		if not parent:
			frappe.throw(_("Not authorized"), frappe.PermissionError)

	doc = frappe.get_doc("Term Exam Report", report_name)
	if doc.docstatus != 1:
		frappe.throw(_("Report has not been submitted yet."))

	rows = [r for r in doc.term_exam_results if r.student == student_id]
	if not rows:
		frappe.throw(_("No results found for this student in this report."))

	student_name = frappe.db.get_value(
		"Student", student_id,
		["first_name", "second_name", "last_name"],
		as_dict=1
	)
	if student_name:
		full_name = " ".join(filter(None, [
			student_name.first_name,
			student_name.second_name,
			student_name.last_name
		])) or student_id
	else:
		full_name = student_id

	school_name = ""
	if doc.cost_center:
		school_name = frappe.db.get_value("Cost Center", doc.cost_center, "cost_center_name") or doc.cost_center

	qr_b64 = doc.get_qr_base64()

	html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  @page {{size:A4;margin:15mm}}
  body {{font-family:Arial,sans-serif;margin:0;padding:0}}
</style>
</head><body>
{build_report_html(full_name, student_id, rows, doc, school_name, qr_b64)}
</body></html>"""

	pdf_bytes = weasyprint.HTML(string=html).write_pdf()
	fname = f"ReportCard_{full_name}_{doc.term}_{doc.academic_year}.pdf".replace(" ", "_")
	frappe.response.filename = fname
	frappe.response.filecontent = pdf_bytes
	frappe.response.type = "pdf"

@frappe.whitelist(allow_guest=True)
def verify_report_text(report, student=None):
	"""
	QR code endpoint — returns a styled HTML verification card in the browser.
	URL pattern: /api/method/school...verify_report_text?report=REPORT-001&student=STU-0001
	"""
	def html_response(content):
		frappe.response["type"] = "html"
		frappe.response["message"] = content

	try:
		doc = frappe.get_doc("Term Exam Report", report)

		if doc.docstatus != 1:
			html_response(_verification_card(
				valid=False,
				title="Invalid Report",
				message="This report has not been officially submitted or has been cancelled.",
				details=[]
			))
			return

		school_name = (
			frappe.db.get_value("Cost Center", doc.cost_center, "cost_center_name")
			or doc.cost_center
			or "School"
		) if doc.cost_center else "School"

		student_name = ""
		if student:
			sdata = frappe.db.get_value(
				"Student", student,
				["first_name", "second_name", "last_name", "full_name"],
				as_dict=True
			)
			if sdata:
				student_name = (
					" ".join(filter(None, [
						sdata.first_name, sdata.second_name, sdata.last_name
					])) or sdata.full_name or student
				)

		section_part = f" — {doc.section}" if doc.section else ""
		intro = ""
		if student_name:
			intro = (
				f"This is {student_name}, from {school_name}, "
				f"in {doc.student_class}{section_part}. "
				f"This is an official report."
			)
		else:
			intro = (
				f"Official Term Exam Report from {school_name}, "
				f"Class {doc.student_class}{section_part}."
			)

		details = [
			("Student Name",    student_name or "—"),
			("Admission No.",   student or "—"),
			("School",          school_name),
			("Class",           doc.student_class or "—"),
			("Section",         doc.section or "—"),
			("Term",            doc.term or "—"),
			("Academic Year",   doc.academic_year or "—"),
			("Report Date",     str(doc.report_date) if doc.report_date else "—"),
			("Report ID",       doc.name),
		]

		html_response(_verification_card(
			valid=True,
			title="Valid",
			message=intro,
			details=details
		))

	except frappe.DoesNotExistError:
		html_response(_verification_card(
			valid=False,
			title="Not Found",
			message="This report could not be found. It may be invalid or has been removed.",
			details=[]
		))


def _verification_card(valid, title, message, details):
	"""Returns a self-contained HTML verification card."""
	accent      = "#16a34a" if valid else "#dc2626"
	icon        = "✔" if valid else "✘"
	badge_bg    = "#dcfce7" if valid else "#fee2e2"
	badge_color = "#15803d" if valid else "#b91c1c"

	rows_html = ""
	for label, value in details:
		if value and value != "—":
			rows_html += f"""
			<tr>
				<td style="padding:9px 14px;font-weight:600;color:#475569;font-size:13px;
				           border-bottom:1px solid #f1f5f9;width:40%;white-space:nowrap">{label}</td>
				<td style="padding:9px 14px;color:#0f172a;font-size:13px;
				           border-bottom:1px solid #f1f5f9">{value}</td>
			</tr>"""

	table_section = ""
	if rows_html:
		table_section = f"""
		<table style="width:100%;border-collapse:collapse;margin-top:20px;
		              border:1px solid #e2e8f0;border-radius:8px;overflow:hidden">
			<tbody>{rows_html}</tbody>
		</table>"""

	return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Report Verification</title>
  <style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      background: #f1f5f9;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px 16px;
    }}
    .card {{
      background: #ffffff;
      border-radius: 16px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.10);
      max-width: 520px;
      width: 100%;
      overflow: hidden;
    }}
    .card-top {{
      background: {accent};
      padding: 28px 28px 24px;
      text-align: center;
    }}
    .icon-circle {{
      width: 64px; height: 64px;
      background: rgba(255,255,255,0.2);
      border-radius: 50%;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 32px;
      color: #fff;
      margin-bottom: 12px;
    }}
    .card-top h1 {{
      color: #fff;
      font-size: 26px;
      font-weight: 800;
      letter-spacing: 1px;
    }}
    .card-body {{
      padding: 24px 28px 32px;
    }}
    .badge {{
      display: inline-block;
      background: {badge_bg};
      color: {badge_color};
      font-size: 12px;
      font-weight: 700;
      padding: 4px 12px;
      border-radius: 20px;
      letter-spacing: 0.5px;
      margin-bottom: 14px;
      text-transform: uppercase;
    }}
    .message {{
      font-size: 14px;
      color: #334155;
      line-height: 1.65;
      background: #f8fafc;
      border-left: 4px solid {accent};
      border-radius: 4px;
      padding: 12px 16px;
    }}
    .footer-note {{
      margin-top: 24px;
      font-size: 11px;
      color: #94a3b8;
      text-align: center;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="card-top">
      <div class="icon-circle">{icon}</div>
      <h1>{title}</h1>
    </div>
    <div class="card-body">
      <div class="badge">{"Verified Official Document" if valid else "Verification Failed"}</div>
      <div class="message">{message}</div>
      {table_section}
      <p class="footer-note">This verification is generated automatically. Do not alter this document.</p>
    </div>
  </div>
</body>
</html>"""