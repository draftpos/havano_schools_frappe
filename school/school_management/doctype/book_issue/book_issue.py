# Copyright (c) 2026, Ashley and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class BookIssue(Document):
	def validate(self):
		if self.is_new():
			self.update_book_count(deduct=True)
		else:
			old_doc = self.get_doc_before_save()
			if old_doc and old_doc.status != "Returned" and self.status == "Returned":
				self.update_book_count(deduct=False)
			elif old_doc and old_doc.status == "Returned" and self.status != "Returned":
				self.update_book_count(deduct=True)

	def update_book_count(self, deduct=True):
		if self.book_title:
			book = frappe.get_doc("Books", self.book_title)
			if deduct:
				if book.count <= 0:
					frappe.throw(f"No copies of {self.book_title} are currently available.")
				book.count -= 1
			else:
				book.count += 1
			book.save()
