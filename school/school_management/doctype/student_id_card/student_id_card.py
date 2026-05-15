# Copyright (c) 2026, Ashley and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class StudentIDCard(Document):
	def before_save(self):
		"""Fetch school name from Cost Center when saved."""
		if self.school_name:
			cost_center = frappe.get_doc("Cost Center", self.school_name)
			self.school_display_name = cost_center.cost_center_name or self.school_name

	def get_school_display_name(self):
		"""Return a human-friendly school name from Cost Center."""
		if self.school_name:
			return (
				frappe.db.get_value("Cost Center", self.school_name, "cost_center_name") or self.school_name
			)
		return ""

	def get_school_logo(self):
		"""Fetch school logo from Cost Center or Company."""
		if not self.school_name:
			return None

		# Try to fetch custom_logo from Cost Center
		# We use get_value with a list of fields to avoid errors if the field is missing
		try:
			logo = frappe.db.get_value("Cost Center", self.school_name, "custom_logo")
		except Exception:
			logo = None

		if not logo:
			# Fallback: Get logo from Company associated with this Cost Center
			company = frappe.db.get_value("Cost Center", self.school_name, "company")
			if company:
				logo = frappe.db.get_value("Company", company, "company_logo")

		if not logo:
			# Fallback: Get logo from Website Settings
			logo = frappe.db.get_single_value("Website Settings", "app_logo")

		return logo


@frappe.whitelist()
def get_students(student_class=None, section=None):
	"""Fetch students filtered by Class and Section."""
	filters = {}
	if student_class:
		filters["student_class"] = student_class
	if section:
		filters["section"] = section

	students = frappe.get_list(
		"Student",
		filters=filters,
		fields=[
			"name",
			"full_name",
			"student_class",
			"section",
			"house",
			"date_of_birth",
			"gender",
			"date_of_admission",
			"student_image",
		],
	)
	return students
