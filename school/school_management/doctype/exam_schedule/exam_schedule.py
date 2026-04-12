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

