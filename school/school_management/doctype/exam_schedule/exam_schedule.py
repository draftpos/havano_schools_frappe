# Copyright (c) 2026, Ashley and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
class ExamSchedule(Document):
	def validate(self):
		self.calculate_grades()
		self.validate_exam_marks_lock()

	def validate_exam_marks_lock(self):
		if self.subject:
			dept = frappe.db.get_value("Subject", self.subject, "department")
			if dept:
				dept_doc = frappe.get_doc("Department", dept)
				if dept_doc.lock_exam_marks:
					old_doc = self.get_doc_before_save()
					changed = False
					if not old_doc:
						changed = True
					else:
						old_map = {item.student_admission_no: item for item in old_doc.exam_items if item.student_admission_no}
						for item in self.exam_items:
							if item.student_admission_no:
								old_item = old_map.get(item.student_admission_no)
								if old_item:
									if (item.marks_obtained != old_item.marks_obtained or 
										item.grade != old_item.grade or 
										item.status != old_item.status or
										item.teacher_comment != old_item.teacher_comment):
										changed = True
										break
								else:
									changed = True
									break
									
					if changed:
						user = frappe.session.user
						is_admin_or_mgr = (user == "Administrator" or "System Manager" in frappe.get_roles(user))
						
						teacher = frappe.db.get_value("Teacher", {"portal_email": user}, "name")
						if not teacher:
							teacher = frappe.db.get_value("Teacher", {"email": user}, "name")
						
						is_hod = (teacher and dept_doc.hod == teacher)
						
						if not (is_admin_or_mgr or is_hod):
							frappe.throw(
								f"Editing exam marks for subject '{self.subject}' (Department '{dept}') "
								"has been locked by the HOD."
							)

	def calculate_grades(self):
		if not self.max_marks:
			frappe.throw(_("Max Marks is required for grade calculation"))
		for item in self.exam_items:
			if item.marks_obtained is not None:
				perc = (item.marks_obtained / self.max_marks) * 100
				grading_score = frappe.get_doc("Grading Score", getattr(self, "grading_score", "STD") or "STD")
				match = None
				for gitem in grading_score.grading_items:
					if perc >= gitem.from_percent and (not gitem.to_percent or perc <= gitem.to_percent):
						match = gitem
						break
				if match:
					item.grade = match.grade
					item.status = match.status or "Pass"
				else:
					item.grade = ""
					item.status = ""
				
				if not item.teacher_comment:
					if perc >= 80:
						item.teacher_comment = "Excellent performance! Keep up the brilliant work."
					elif perc >= 70:
						item.teacher_comment = "Very good progress. With a bit more effort, you can reach the top."
					elif perc >= 60:
						item.teacher_comment = "Good effort. Consistent practice will bring even better results."
					elif perc >= 50:
						item.teacher_comment = "Satisfactory result, but there is room for improvement."
					else:
						item.teacher_comment = "Needs extra support and more focus. Please put in more effort next term."



@frappe.whitelist()
def get_teacher_subjects(teacher=None, student_class=None, section=None):
	"""Get subjects assigned to a teacher, optionally filtered by class/section."""
	if not teacher:
		return []

	filters = {"teacher": teacher}
	if student_class:
		filters["student_class"] = student_class
	if section:
		filters["section"] = section

	assignments = frappe.get_all(
		"Assign Subjects to Teacher",
		filters=filters,
		fields=["subject", "student_class", "section"]
	)

	subjects = list(set([a.subject for a in assignments if a.subject]))
	return subjects


@frappe.whitelist()
def get_students(student_class=None, section=None):
	"""Get students for a given class and section."""
	if not student_class:
		return []

	filters = {"student_class": student_class}
	if section:
		filters["section"] = section

	# Use only fields that exist on Student doctype
	students = frappe.get_all(
		"Student",
		filters=filters,
		fields=["name", "full_name"],
		order_by="full_name asc"
	)

	# Normalize to consistent keys
	for s in students:
		s["student_name"] = s.get("full_name") or s.get("name")

	return students
