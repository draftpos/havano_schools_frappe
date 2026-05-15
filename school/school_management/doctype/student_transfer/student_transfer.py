# Copyright (c) 2026, Havano and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class StudentTransfer(Document):
	def validate(self):
		self.validate_student()
		self.validate_outstanding_balance()
		self.fetch_student_details()

	def validate_student(self):
		if not self.student:
			frappe.throw(_("Please select a student."))

		current_status = frappe.db.get_value("Student", self.student, "transfer_status") or "Active"
		if current_status in ("Transferred", "Inactive"):
			frappe.throw(
				_(f"Student {self.student} is already marked as {current_status}. Cannot transfer again.")
			)

	def validate_outstanding_balance(self):
		"""Block transfer if student has outstanding invoices"""
		outstanding = frappe.db.sql(
			"""
            SELECT SUM(si.outstanding_amount)
            FROM `tabSales Invoice` si
            JOIN `tabCustomer` c ON c.name = si.customer
            WHERE c.custom_class = %s
              AND si.docstatus = 1
              AND si.outstanding_amount > 0
        """,
			self.student,
		)

		balance = outstanding[0][0] if outstanding and outstanding[0][0] else 0

		if balance > 0:
			frappe.throw(
				_(
					f"Cannot transfer {self.student}. Outstanding balance of {frappe.format_value(balance, 'Currency')} exists. "
					f"Please clear all dues before transferring."
				)
			)

	def fetch_student_details(self):
		if not self.student:
			return
		student = frappe.get_doc("Student", self.student)
		self.full_name = student.full_name or f"{student.first_name or ''} {student.last_name or ''}".strip()
		self.student_reg_no = student.student_reg_no
		self.student_class = student.student_class
		self.section = student.section
		self.school = student.school
		self.date_of_birth = student.date_of_birth
		self.gender = student.gender
		self.student_phone_number = student.student_phone_number

	def before_submit(self):
		"""Snapshot original class/section so cancel can restore them"""
		student = frappe.db.get_value("Student", self.student, ["student_class", "section"], as_dict=True)
		self.student_class = student.student_class
		self.section = student.section

	def on_submit(self):
		self.apply_transfer()

	def on_cancel(self):
		self.reverse_transfer()

	def apply_transfer(self):
		"""Mark student as Transferred/Inactive and remove from class/section"""
		student_name = frappe.db.get_value("Student", self.student, "full_name") or self.student
		status = self.status or "Transferred"

		frappe.db.set_value(
			"Student",
			self.student,
			{
				"transfer_status": status,
				"student_class": None,
				"section": None,
			},
		)

		frappe.db.set_value(
			"Customer",
			{"custom_class": self.student},
			{
				"custom_student_class": "",
				"custom_student_section": "",
			},
		)

		frappe.msgprint(
			_(f"Student {student_name} marked as {status} and removed from class/section."),
			indicator="green",
			alert=True,
		)

	def reverse_transfer(self):
		"""Restore student status and class/section on cancel"""
		frappe.db.set_value(
			"Student",
			self.student,
			{
				"transfer_status": "Active",
				"student_class": self.student_class,
				"section": self.section,
			},
		)

		frappe.db.set_value(
			"Customer",
			{"custom_class": self.student},
			{
				"custom_student_class": self.student_class or "",
				"custom_student_section": self.section or "",
			},
		)

		frappe.msgprint(
			_(f"Transfer reversed. {self.student} restored to Active."),
			indicator="blue",
			alert=True,
		)


@frappe.whitelist()
def get_student_outstanding(student):
	"""Check if student has outstanding balance"""
	outstanding = frappe.db.sql(
		"""
        SELECT SUM(si.outstanding_amount)
        FROM `tabSales Invoice` si
        JOIN `tabCustomer` c ON c.name = si.customer
        WHERE c.custom_class = %s
          AND si.docstatus = 1
          AND si.outstanding_amount > 0
    """,
		student,
	)

	balance = outstanding[0][0] if outstanding and outstanding[0][0] else 0
	return {"outstanding": float(balance)}
