import frappe
from frappe.model.document import Document
from frappe import _
from collections import defaultdict
import qrcode
import io
import base64


def get_grade(percentage):
	if percentage >= 90:
		return "A+"
	elif percentage >= 80:
		return "A"
	elif percentage >= 70:
		return "B"
	elif percentage >= 60:
		return "C"
	elif percentage >= 50:
		return "D"
	else:
		return "F"


def generate_qr_base64(data):
	"""Generate a QR code and return as base64 PNG string."""
	qr = qrcode.QRCode(version=1, box_size=6, border=2)
	qr.add_data(data)
	qr.make(fit=True)
	img = qr.make_image(fill_color="black", back_color="white")
	buffer = io.BytesIO()
	img.save(buffer, format="PNG")
	buffer.seek(0)
	return base64.b64encode(buffer.read()).decode("utf-8")


def build_report_html(student_name, rows, doc, qr_b64=None):
	"""Build a complete styled HTML report card for one student."""
	school_name = ""
	if doc.cost_center:
		try:
			cc = frappe.get_doc("Cost Center", doc.cost_center)
			school_name = cc.cost_center_name or doc.cost_center
		except Exception:
			school_name = doc.cost_center

	rows_sorted = sorted(rows, key=lambda r: r.subject or "")
	total_obtained = sum(r.marks_obtained or 0 for r in rows_sorted)
	total_max = sum(r.max_marks or 0 for r in rows_sorted)
	overall_pct = round((total_obtained / total_max * 100), 2) if total_max else 0
	overall_grade = get_grade(overall_pct)
	verification_url = f"{frappe.utils.get_url()}/term-exam-results?report={doc.name}"

	subject_rows_html = ""
	for r in rows_sorted:
		color = "#27ae60" if (r.percentage or 0) >= 50 else "#e74c3c"
		subject_rows_html += f"""
		<tr>
			<td style="padding:8px 10px;border-bottom:1px solid #e2e8f0">{r.subject or ''}</td>
			<td style="text-align:center;padding:8px 10px;border-bottom:1px solid #e2e8f0">{r.marks_obtained or 0}</td>
			<td style="text-align:center;padding:8px 10px;border-bottom:1px solid #e2e8f0">{r.max_marks or 0}</td>
			<td style="text-align:center;padding:8px 10px;border-bottom:1px solid #e2e8f0">{r.percentage or 0}%</td>
			<td style="text-align:center;padding:8px 10px;border-bottom:1px solid #e2e8f0;font-weight:bold;color:{color}">{r.grade or ''}</td>
			<td style="text-align:center;padding:8px 10px;border-bottom:1px solid #e2e8f0">{r.position or ''}</td>
			<td style="padding:8px 10px;border-bottom:1px solid #e2e8f0">{r.remarks or ''}</td>
		</tr>"""

	qr_html = ""
	if qr_b64:
		qr_html = f"""
		<div style="text-align:center;margin-top:4px">
			<img src="data:image/png;base64,{qr_b64}" width="90" height="90" alt="QR Code"/>
			<p style="font-size:10px;color:#64748b;margin:2px 0 0">Scan to verify</p>
		</div>"""

	opening_row = f"<p style='margin:2px 0'><strong>School Opens:</strong> {doc.opening_date}</p>" if doc.opening_date else ""

	return f"""
	<div style="font-family:Arial,sans-serif;max-width:740px;margin:auto;border:2px solid #2c3e50;border-radius:8px;overflow:hidden">
		<div style="background:#2c3e50;color:white;padding:18px 24px;text-align:center">
			<h2 style="margin:0;font-size:20px">{school_name or 'School'}</h2>
			<h3 style="margin:4px 0 0;font-size:14px;font-weight:normal">Term Exam Report Card</h3>
		</div>

		<div style="background:#ecf0f1;padding:14px 24px;display:flex;justify-content:space-between;flex-wrap:wrap">
			<div>
				<p style="margin:3px 0"><strong>Student:</strong> {student_name}</p>
				<p style="margin:3px 0"><strong>Class:</strong> {doc.student_class}{(' &nbsp;|&nbsp; Section: ' + doc.section) if doc.section else ''}</p>
				<p style="margin:3px 0"><strong>Exam:</strong> {doc.exam}</p>
			</div>
			<div style="text-align:right">
				<p style="margin:3px 0"><strong>Academic Year:</strong> {doc.academic_year}</p>
				<p style="margin:3px 0"><strong>Term:</strong> {doc.term}</p>
				<p style="margin:3px 0"><strong>Date:</strong> {doc.report_date}</p>
			</div>
		</div>

		<div style="padding:0 20px">
			<table style="width:100%;border-collapse:collapse;font-size:13px;margin:14px 0">
				<thead>
					<tr style="background:#2c3e50;color:white">
						<th style="padding:9px 10px;text-align:left">Subject</th>
						<th style="padding:9px 10px;text-align:center">Marks</th>
						<th style="padding:9px 10px;text-align:center">Max</th>
						<th style="padding:9px 10px;text-align:center">%</th>
						<th style="padding:9px 10px;text-align:center">Grade</th>
						<th style="padding:9px 10px;text-align:center">Position</th>
						<th style="padding:9px 10px;text-align:left">Remarks</th>
					</tr>
				</thead>
				<tbody>{subject_rows_html}</tbody>
				<tfoot>
					<tr style="background:#ecf0f1;font-weight:bold">
						<td style="padding:9px 10px">OVERALL</td>
						<td style="text-align:center;padding:9px 10px">{total_obtained}</td>
						<td style="text-align:center;padding:9px 10px">{total_max}</td>
						<td style="text-align:center;padding:9px 10px">{overall_pct}%</td>
						<td style="text-align:center;padding:9px 10px;color:{'#27ae60' if overall_pct >= 50 else '#e74c3c'}">{overall_grade}</td>
						<td></td><td></td>
					</tr>
				</tfoot>
			</table>
		</div>

		<div style="padding:6px 20px 10px;display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap">
			<div style="font-size:11px;color:#555">
				<strong>Grade Key:</strong> A+ ≥90% | A ≥80% | B ≥70% | C ≥60% | D ≥50% | F &lt;50%
			</div>
			{qr_html}
		</div>

		<div style="padding:14px 24px;display:flex;justify-content:space-between">
			<div style="text-align:center;width:30%">
				<div style="border-top:1px solid #333;margin-top:30px;padding-top:4px;font-size:12px">Class Teacher</div>
			</div>
			<div style="text-align:center;width:30%">
				<div style="border-top:1px solid #333;margin-top:30px;padding-top:4px;font-size:12px">Head Teacher</div>
			</div>
			<div style="text-align:center;width:30%">
				<div style="border-top:1px solid #333;margin-top:30px;padding-top:4px;font-size:12px">Parent / Guardian</div>
			</div>
		</div>

		<div style="background:#2c3e50;color:#ecf0f1;padding:10px 24px;font-size:11px">
			{opening_row}
			<p style="margin:2px 0">Verify: <a href="{verification_url}" style="color:#93c5fd">{verification_url}</a></p>
			<p style="margin:2px 0">Report ID: {doc.name} &nbsp;|&nbsp; Official school document.</p>
		</div>
	</div>"""


class TermExamReport(Document):

	def before_save(self):
		if self.docstatus == 0:
			self.fetch_exam_results()
			self.calculate_totals()
			self.calculate_positions()

	def fetch_exam_results(self):
		self.term_exam_results = []

		if not self.exam or not self.student_class:
			frappe.throw(_("Please select Exam and Class before saving."))

		schedule_filters = {"exam": self.exam, "student_class": self.student_class}
		if self.section:
			schedule_filters["section"] = self.section

		schedules = frappe.get_all(
			"Exam Schedule",
			filters=schedule_filters,
			fields=["name", "subject", "max_marks", "min_marks"]
		)

		if not schedules:
			frappe.msgprint(_("No Exam Schedules found for the selected Exam / Class / Section."), indicator="orange")
			return

		schedule_map = {s.name: s for s in schedules}
		schedule_names = list(schedule_map.keys())

		exam_results = frappe.get_all(
			"Exam Result",
			filters={"source_doc": ["in", schedule_names]},
			fields=["name", "source_doc", "subject"]
		)

		if not exam_results:
			frappe.msgprint(_("No Exam Results found for the selected Exam Schedules."), indicator="orange")
			return

		for er in exam_results:
			er_doc = frappe.get_doc("Exam Result", er.name)
			schedule = schedule_map.get(er.source_doc, frappe._dict())
			subject = er_doc.subject or schedule.get("subject", "")
			max_marks = schedule.get("max_marks") or 0

			for score in er_doc.scores:
				student = score.student_admission_no
				if not student:
					continue
				marks = score.marks_obtained or 0
				pct = round((marks / max_marks * 100), 2) if max_marks else 0
				self.append("term_exam_results", {
					"student": student,
					"subject": subject,
					"marks_obtained": marks,
					"max_marks": max_marks,
					"percentage": pct,
					"grade": get_grade(pct),
					"remarks": "",
					"position": 0
				})

	def calculate_totals(self):
		self.total_subjects = len(set(r.subject for r in self.term_exam_results))
		self.total_students = len(set(r.student for r in self.term_exam_results))

	def calculate_positions(self):
		subject_rows = defaultdict(list)
		for row in self.term_exam_results:
			subject_rows[row.subject].append(row)

		for subject, rows in subject_rows.items():
			sorted_rows = sorted(rows, key=lambda r: r.marks_obtained or 0, reverse=True)
			prev_marks = None
			rank = 1
			for i, row in enumerate(sorted_rows):
				if row.marks_obtained != prev_marks:
					rank = i + 1
				row.position = rank
				prev_marks = row.marks_obtained

	def get_verification_url(self):
		return f"{frappe.utils.get_url()}/term-exam-results?report={self.name}"

	def get_qr_base64(self):
		return generate_qr_base64(self.get_verification_url())

	def on_submit(self):
		self.send_report_emails()

	def send_report_emails(self):
		student_results = defaultdict(list)
		for row in self.term_exam_results:
			student_results[row.student].append(row)

		sent = 0
		failed = 0
		qr_b64 = self.get_qr_base64()

		for student_id, rows in student_results.items():
			try:
				student_doc = frappe.get_doc("Student", student_id)
				student_name = student_doc.student_name or student_id
				email = getattr(student_doc, "student_email_id", None) or getattr(student_doc, "email", None)

				if not email:
					for g in frappe.get_all("Student Guardian", filters={"parent": student_id}, fields=["guardian"]):
						gd = frappe.get_doc("Guardian", g.guardian)
						if gd.email_address:
							email = gd.email_address
							break

				if not email:
					frappe.log_error(f"No email for student {student_id}", "Term Exam Report Email")
					failed += 1
					continue

				frappe.sendmail(
					recipients=[email],
					subject=f"Term Exam Report Card - {student_name} | {self.term} | {self.academic_year}",
					message=build_report_html(student_name, rows, self, qr_b64),
					reference_doctype=self.doctype,
					reference_name=self.name,
					now=True
				)
				sent += 1
			except Exception:
				frappe.log_error(frappe.get_traceback(), f"Term Exam Report Email Failed: {student_id}")
				failed += 1

		frappe.msgprint(
			_(f"Report cards sent: {sent}" + (f" | Failed: {failed} (check Error Log)" if failed else "")),
			indicator="green" if not failed else "orange"
		)


# ─── Whitelisted API Methods ───────────────────────────────────────────────────

@frappe.whitelist()
def get_student_pdf(report_name, student_id):
	"""
	Generate a PDF report card for a specific student.
	Called from the portal Download button.
	"""
	import weasyprint

	user = frappe.session.user

	# Check authorization: must be the student or a linked guardian
	is_student = frappe.db.get_value("Student", {"user": user, "name": student_id}, "name")
	if not is_student:
		guardian = frappe.db.get_value("Guardian", {"user": user}, "name")
		if not guardian or not frappe.db.exists("Student Guardian", {"guardian": guardian, "parent": student_id}):
			frappe.throw(_("Not authorized"), frappe.PermissionError)

	doc = frappe.get_doc("Term Exam Report", report_name)
	if doc.docstatus != 1:
		frappe.throw(_("Report has not been submitted yet."))

	rows = [r for r in doc.term_exam_results if r.student == student_id]
	if not rows:
		frappe.throw(_("No results found for this student in this report."))

	student_name = frappe.db.get_value("Student", student_id, "student_name") or student_id
	qr_b64 = doc.get_qr_base64()

	html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>@page{{size:A4;margin:15mm}}body{{font-family:Arial,sans-serif;margin:0;padding:0}}</style>
</head><body>{build_report_html(student_name, rows, doc, qr_b64)}</body></html>"""

	pdf_bytes = weasyprint.HTML(string=html).write_pdf()
	fname = f"ReportCard_{student_name}_{doc.term}_{doc.academic_year}.pdf".replace(" ", "_")

	frappe.response.filename = fname
	frappe.response.filecontent = pdf_bytes
	frappe.response.type = "pdf"


@frappe.whitelist(allow_guest=True)
def verify_report(report):
	"""
	Public verification endpoint — QR code links here.
	Returns report metadata to confirm authenticity, no marks exposed.
	"""
	try:
		doc = frappe.get_doc("Term Exam Report", report)
		if doc.docstatus != 1:
			return {"valid": False, "message": "This report has not been officially submitted."}
		return {
			"valid": True,
			"report_name": doc.report_name,
			"exam": doc.exam,
			"term": doc.term,
			"academic_year": doc.academic_year,
			"student_class": doc.student_class,
			"section": doc.section or "",
			"report_date": str(doc.report_date),
			"total_students": doc.total_students,
			"total_subjects": doc.total_subjects,
			"issued_by": doc.cost_center or "School",
			"message": "✓ This is a genuine official report card."
		}
	except frappe.DoesNotExistError:
		return {"valid": False, "message": "Report not found. This document may be invalid or tampered."}


@frappe.whitelist(allow_guest=True)
def verify_exam_schedule(schedule):
	"""
	Verify an Exam Schedule record is genuine.
	Called from the portal verify button and QR scan.
	"""
	try:
		doc = frappe.get_doc("Exam Schedule", schedule)
		return {
			"valid": True,
			"schedule": doc.name,
			"exam": doc.exam,
			"subject": doc.subject,
			"term": doc.term or "",
			"student_class": doc.student_class,
			"section": doc.section or "",
			"date": str(doc.date) if doc.date else "",
			"max_marks": doc.max_marks or 0,
			"message": "This is a genuine official exam record."
		}
	except frappe.DoesNotExistError:
		return {"valid": False, "message": "Exam schedule not found. This record may be invalid."}


@frappe.whitelist()
def get_exam_pdf(exam, term, student_id, exam_data):
	"""
	Generate a PDF report card for one exam (all subjects) for a student.
	exam_data is passed from the frontend as a JSON object.
	"""
	import weasyprint
	import json as _json

	user = frappe.session.user
	is_student = frappe.db.get_value("Student", {"user": user, "name": student_id}, "name")
	if not is_student:
		guardian = frappe.db.get_value("Guardian", {"user": user}, "name")
		if not guardian or not frappe.db.exists("Student Guardian", {"guardian": guardian, "parent": student_id}):
			frappe.throw(_("Not authorized"), frappe.PermissionError)

	if isinstance(exam_data, str):
		exam_data = _json.loads(exam_data)

	student_name = frappe.db.get_value("Student", student_id, "student_name") or student_id
	subjects = exam_data.get("subjects", [])
	total_obtained = exam_data.get("total_obtained", 0)
	total_max = exam_data.get("total_max", 0)
	overall_pct = exam_data.get("overall_percentage", 0)
	overall_grade = exam_data.get("overall_grade", "")

	# Build QR for this exam (encode exam name + term)
	qr_data = f"{frappe.utils.get_url()}/term-exam-results?exam={exam}&term={term}"
	qr_b64 = generate_qr_base64(qr_data)

	subject_rows = ""
	for s in subjects:
		color = "#27ae60" if (s.get("percentage") or 0) >= 50 else "#e74c3c"
		subject_rows += f"""
		<tr>
			<td style="padding:8px 10px;border-bottom:1px solid #e2e8f0">{s.get('subject','')}</td>
			<td style="text-align:center;padding:8px 10px;border-bottom:1px solid #e2e8f0">{s.get('date','')}</td>
			<td style="text-align:center;padding:8px 10px;border-bottom:1px solid #e2e8f0">{s.get('marks_obtained',0)}</td>
			<td style="text-align:center;padding:8px 10px;border-bottom:1px solid #e2e8f0">{s.get('max_marks',0)}</td>
			<td style="text-align:center;padding:8px 10px;border-bottom:1px solid #e2e8f0">{s.get('percentage',0):.1f}%</td>
			<td style="text-align:center;padding:8px 10px;border-bottom:1px solid #e2e8f0;font-weight:bold;color:{color}">{s.get('grade','')}</td>
			<td style="text-align:center;padding:8px 10px;border-bottom:1px solid #e2e8f0">{s.get('status','')}</td>
		</tr>"""

	overall_color = "#27ae60" if overall_pct >= 50 else "#e74c3c"

	html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  @page {{size:A4;margin:15mm}}
  body {{font-family:Arial,sans-serif;margin:0;padding:0}}
</style>
</head>
<body>
<div style="border:2px solid #2c3e50;border-radius:8px;overflow:hidden;max-width:700px;margin:auto">
  <div style="background:#2c3e50;color:white;padding:18px 24px;text-align:center">
    <h2 style="margin:0;font-size:20px">Exam Result Card</h2>
    <h3 style="margin:4px 0 0;font-size:14px;font-weight:normal">{exam} &mdash; {term}</h3>
  </div>
  <div style="background:#ecf0f1;padding:14px 24px;display:flex;justify-content:space-between;flex-wrap:wrap">
    <div>
      <p style="margin:3px 0"><strong>Student:</strong> {student_name}</p>
      <p style="margin:3px 0"><strong>Exam:</strong> {exam}</p>
    </div>
    <div style="text-align:right">
      <p style="margin:3px 0"><strong>Term:</strong> {term}</p>
    </div>
  </div>
  <div style="padding:0 20px">
    <table style="width:100%;border-collapse:collapse;font-size:13px;margin:14px 0">
      <thead>
        <tr style="background:#2c3e50;color:white">
          <th style="padding:9px 10px;text-align:left">Subject</th>
          <th style="padding:9px 10px;text-align:center">Date</th>
          <th style="padding:9px 10px;text-align:center">Marks</th>
          <th style="padding:9px 10px;text-align:center">Max</th>
          <th style="padding:9px 10px;text-align:center">%</th>
          <th style="padding:9px 10px;text-align:center">Grade</th>
          <th style="padding:9px 10px;text-align:center">Status</th>
        </tr>
      </thead>
      <tbody>{subject_rows}</tbody>
      <tfoot>
        <tr style="background:#ecf0f1;font-weight:bold">
          <td colspan="2" style="padding:9px 10px">OVERALL TOTAL</td>
          <td style="text-align:center;padding:9px 10px">{total_obtained}</td>
          <td style="text-align:center;padding:9px 10px">{total_max}</td>
          <td style="text-align:center;padding:9px 10px">{overall_pct:.1f}%</td>
          <td style="text-align:center;padding:9px 10px;color:{overall_color}">{overall_grade}</td>
          <td></td>
        </tr>
      </tfoot>
    </table>
  </div>
  <div style="padding:10px 20px;display:flex;justify-content:space-between;align-items:center">
    <div style="font-size:11px;color:#555">
      <strong>Grade Key:</strong> A+ ≥90% | A ≥80% | B ≥70% | C ≥60% | D ≥50% | F &lt;50%
    </div>
    <div style="text-align:center">
      <img src="data:image/png;base64,{qr_b64}" width="80" height="80" alt="QR"/>
      <p style="font-size:10px;color:#64748b;margin:2px 0">Scan to verify</p>
    </div>
  </div>
  <div style="padding:14px 24px;display:flex;justify-content:space-between">
    <div style="text-align:center;width:30%"><div style="border-top:1px solid #333;margin-top:30px;padding-top:4px;font-size:12px">Class Teacher</div></div>
    <div style="text-align:center;width:30%"><div style="border-top:1px solid #333;margin-top:30px;padding-top:4px;font-size:12px">Head Teacher</div></div>
    <div style="text-align:center;width:30%"><div style="border-top:1px solid #333;margin-top:30px;padding-top:4px;font-size:12px">Parent / Guardian</div></div>
  </div>
  <div style="background:#2c3e50;color:#ecf0f1;padding:10px 24px;font-size:11px">
    <p style="margin:2px 0">Official exam result. Generated from school management system.</p>
  </div>
</div>
</body></html>"""

	pdf_bytes = weasyprint.HTML(string=html).write_pdf()
	frappe.response.filename = f"{exam}_{term}_{student_name}_Results.pdf".replace(" ", "_")
	frappe.response.filecontent = pdf_bytes
	frappe.response.type = "pdf"