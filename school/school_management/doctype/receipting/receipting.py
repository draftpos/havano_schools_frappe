import frappe
from frappe.model.document import Document
from frappe.utils import flt, today


class Receipting(Document):
	def validate(self):
		self.calculate_totals()

	def calculate_totals(self):
		total_outstanding = 0
		total_allocated = 0
		receipt_currency = self.currency or "USD"
		rate = flt(self.exchange_rate) or 1.0

		for row in self.invoice:
			inv_currency = row.invoice_currency or "USD"
			out = flt(row.outstanding)

			if receipt_currency != inv_currency:
				if receipt_currency == "ZWG" and inv_currency == "USD":
					out = out * rate
				elif receipt_currency == "USD" and inv_currency == "ZWG":
					out = out / rate

			total_outstanding += out
			total_allocated += flt(row.allocated)

		self.total_outstanding = total_outstanding
		self.total_allocated = total_allocated
		self.total_balance = total_outstanding - total_allocated

	def on_submit(self):
		if flt(self.total_allocated) <= 0:
			frappe.throw("Allocation amount must be greater than 0.")
		self.create_payment_entry()

	def create_payment_entry(self):
		# Prevent duplicate payment entries
		existing = frappe.get_all(
			"Payment Entry", filters={"reference_no": self.name, "docstatus": ["!=", 2]}, limit=1
		)
		if existing:
			frappe.msgprint("Payment Entry already exists for this receipt. Skipping.")
			return

		student_full_name = frappe.db.get_value("Student", self.student_name, "full_name")
		company = frappe.defaults.get_global_default("company") or frappe.get_all("Company")[0].name
		company_currency = frappe.db.get_value("Company", company, "default_currency")

		paid_from = frappe.db.get_value("Company", company, "default_receivable_account")

		paid_to_currency = self.currency or company_currency
		paid_from_currency = frappe.db.get_value("Account", paid_from, "account_currency") or company_currency

		pe = frappe.new_doc("Payment Entry")
		pe.payment_type = "Receive"
		pe.party_type = "Customer"
		pe.party = student_full_name
		pe.company = company
		pe.posting_date = self.date or today()
		pe.paid_from = paid_from
		pe.paid_to = self.account
		pe.paid_from_account_currency = paid_from_currency
		pe.paid_to_account_currency = paid_to_currency

		# Receipt Currency is the "Received" currency
		pe.received_amount = flt(self.total_allocated)

		# Convert allocated to Receivable currency (USD) for paid_amount
		if paid_from_currency != paid_to_currency:
			if paid_to_currency == "ZWG" and paid_from_currency == "USD":
				pe.paid_amount = (
					flt(self.total_allocated) / flt(self.exchange_rate) if flt(self.exchange_rate) else 0
				)
				pe.target_exchange_rate = flt(self.exchange_rate)
			elif paid_to_currency == "USD" and paid_from_currency == "ZWG":
				pe.paid_amount = flt(self.total_allocated) * flt(self.exchange_rate)
				pe.source_exchange_rate = flt(self.exchange_rate)
		else:
			pe.paid_amount = flt(self.total_allocated)
			pe.source_exchange_rate = 1.0
			pe.target_exchange_rate = 1.0

		pe.reference_no = self.name
		pe.reference_date = self.date or today()

		total_allocated_in_refs = 0

		# Group allocations by invoice
		invoice_allocations = {}
		for row in self.invoice:
			if row.invoice_number and flt(row.allocated) > 0:
				inv_currency = row.invoice_currency or "USD"
				allocated_in_inv_cur = flt(row.allocated)
				if paid_to_currency != inv_currency:
					if paid_to_currency == "ZWG" and inv_currency == "USD":
						allocated_in_inv_cur = (
							flt(row.allocated) / flt(self.exchange_rate) if flt(self.exchange_rate) else 0
						)
					elif paid_to_currency == "USD" and inv_currency == "ZWG":
						allocated_in_inv_cur = flt(row.allocated) * flt(self.exchange_rate)

				invoice_allocations[row.invoice_number] = (
					invoice_allocations.get(row.invoice_number, 0) + allocated_in_inv_cur
				)

		for inv_name, allocated_amount in invoice_allocations.items():
			actual_outstanding = frappe.db.get_value("Sales Invoice", inv_name, "outstanding_amount")
			allocated = min(allocated_amount, flt(actual_outstanding))
			if allocated > 0:
				pe.append(
					"references",
					{
						"reference_doctype": "Sales Invoice",
						"reference_name": inv_name,
						"allocated_amount": allocated,
						"due_date": frappe.db.get_value("Sales Invoice", inv_name, "due_date"),
						"total_amount": frappe.db.get_value("Sales Invoice", inv_name, "grand_total"),
						"outstanding_amount": actual_outstanding,
					},
				)
				total_allocated_in_refs += allocated

		# Ensure difference/unallocated amounts are zero so GL posts cleanly
		pe.total_allocated_amount = total_allocated_in_refs
		pe.unallocated_amount = 0
		pe.write_off_amount = 0
		pe.difference_amount = 0

		# Insert without skipping validate so set_missing_values runs properly
		pe.flags.ignore_permissions = True
		pe.flags.ignore_mandatory = True
		pe.insert(ignore_permissions=True)

		# Recalculate after insert
		pe.run_method("set_missing_values")
		pe.run_method("set_amounts")

		# Force amounts clean before submit
		pe.unallocated_amount = 0
		pe.write_off_amount = 0
		pe.difference_amount = 0

		# Submit — Frappe handles GL entries + invoice outstanding updates automatically
		pe.flags.ignore_permissions = True
		pe.flags.ignore_mandatory = True
		pe.submit()
		frappe.db.commit()

		frappe.msgprint(f"Payment Entry {pe.name} created and GL entries posted successfully.")

		# Handle opening balance payments ONLY — Frappe does NOT handle this automatically
		for row in self.invoice:
			if not row.invoice_number and row.fee_item == "Opening Balance":
				current_ob = frappe.db.get_value("Student", self.student_name, "opening_balance")
				new_ob = flt(current_ob) - flt(row.allocated)
				frappe.db.set_value("Student", self.student_name, "opening_balance", new_ob)

		frappe.db.commit()
