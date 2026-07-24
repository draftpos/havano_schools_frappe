# Copyright (c) 2026, Ashley and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
import json


def get_grade_from_db(percentage, class_name=None):
	"""Look up grade/status from Grading Score Item in DB — no hardcoded fallback."""
	if percentage is None:
		return "", "", 0
	cn = (class_name or "").lower()
	use_unit = any(k in cn for k in ["primary", "ecd", "grade", "nursery"])
	target_field = "unit_grading_items" if use_unit else "grading_items"
	try:
		items = frappe.db.sql("""
			SELECT grade, unit, status, from_percent, to_percent
			FROM `tabGrading Score Item`
			WHERE parentfield = %s
			ORDER BY from_percent DESC
		""", (target_field,), as_dict=True)
		for item in items:
			to_pct = item.to_percent if item.to_percent is not None else 100
			if percentage >= item.from_percent and percentage <= to_pct:
				if use_unit and item.get("unit"):
					return item.unit, item.status or "", 0
				if item.get("grade"):
					return item.grade, item.status or "", 0
	except Exception as e:
		frappe.log_error(f"get_grade_from_db error: {e}", "Grade Lookup")
	return "", "", 0


class HomeSchedule(Document):
	def validate(self):
		self.calculate_grades()

	def calculate_grades(self):
		if not self.max_marks:
			frappe.throw(_("Max Marks is required for grade calculation"))
		for item in self.home_items:
			if item.marks_obtained is not None:
				perc = (item.marks_obtained / self.max_marks) * 100
				class_name = self.get("student_class") or self.get("class_name") or ""
				grade, status, _ = get_grade_from_db(perc, class_name)
				item.grade = grade
				item.status = status
