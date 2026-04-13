# Copyright (c) 2026, Ashley and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class ExamSchedule(Document):
	def validate(self):
		self.calculate_grades()

	def calculate_grades(self):
		if not self.max_marks:
			frappe.throw(_("Max Marks is required for grade calculation"))
		for item in self.exam_items:
			if item.marks_obtained is not None:
				perc = (item.marks_obtained / self.max_marks) * 100
				grading_score = frappe.get_doc("Grading Score", "STD")
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
