import frappe
from frappe.model.document import Document
from frappe import _
import json

class TestSchedule(Document):
	def validate(self):
		self.calculate_grades()

	def calculate_grades(self):
		if not self.max_marks:
			frappe.throw(_("Max Marks is required for grade calculation"))
		for item in self.test_items:
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
def get_teacher_subjects(student_class=""):
	teacher_email = frappe.session.user
	# Get subjects assigned to this teacher
	filters = {"parent": teacher_email}
	if student_class:
		filters["class_name"] = student_class
	items = frappe.get_all(
		"Teacher Subject Assignment Item",
		filters=filters,
		fields=["subject"],
		ignore_permissions=True
	)
	subjects = list(set([i["subject"] for i in items if i["subject"]]))
	return subjects

@frappe.whitelist()
def get_students(student_class, section=""):
	filters = {"student_class": student_class}
	if section:
		filters["section"] = section
	students = frappe.get_all(
		"Student",
		filters=filters,
		fields=["student_reg_no", "full_name"],
		order_by="full_name asc"
	)
	return students

