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
		# Guard 1: Check if a PE already exists for THIS receipt
		existing_pes = frappe.get_all(
			"Payment Entry",
			filters={"reference_no": self.name, "docstatus": ["!=", 2]},
			fields=["name", "received_amount", "docstatus"]
		)
		if existing_pes:
			if len(existing_pes) == 1 and flt(existing_pes[0].received_amount) == flt(self.total_allocated) and existing_pes[0].docstatus == 1:
				frappe.msgprint(f"Payment Entry {existing_pes[0].name} already exists and matches receipt. Skipping.")
				return

		# Guard 2: Check if any invoice in this receipt is already fully paid
		# by a Payment Entry from a DIFFERENT receipt
		for row in self.invoice:
			if not row.invoice_number or flt(row.allocated) <= 0:
				continue
			sinv_outstanding = frappe.db.get_value("Sales Invoice", row.invoice_number, "outstanding_amount")
			if flt(sinv_outstanding) <= 0:
				frappe.throw(
					f"Invoice {row.invoice_number} is already fully paid (outstanding = {sinv_outstanding}). "
					f"Cannot create a duplicate payment. Please cancel this receipt."
				)

			# Also check for any submitted PE referencing this invoice from a different receipt
			conflicting = frappe.db.sql("""
				SELECT pe.name, pe.reference_no
				FROM `tabPayment Entry` pe
				JOIN `tabPayment Entry Reference` per ON per.parent = pe.name
				WHERE per.reference_name = %s
				AND per.reference_doctype = 'Sales Invoice'
				AND pe.docstatus = 1
				AND pe.reference_no != %s
			""", (row.invoice_number, self.name), as_dict=True)

			if conflicting:
				conflict_names = ", ".join([f"{c.name} (from {c.reference_no})" for c in conflicting])
				frappe.throw(
					f"Invoice {row.invoice_number} already has a submitted Payment Entry from another receipt: "
					f"{conflict_names}. Cannot create duplicate payment."
				)

		# If duplicates or mismatches exist for THIS receipt, clean them first
		if existing_pes:
			frappe.msgprint("Discrepancy found in Payment Entries for this receipt. Cleaning and recreating...")
			for pe in existing_pes:
				try:
					pe_doc = frappe.get_doc("Payment Entry", pe.name)
					pe_doc.flags.ignore_permissions = True
					if pe_doc.docstatus == 1:
						pe_doc.cancel()
					pe_doc.delete()
				except Exception:
					frappe.log_error(
						title=f"Failed to cancel/delete PE {pe.name} for Receipt {self.name}",
						message=frappe.get_traceback()
					)

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

	def verify_and_reconcile_payment_entry(self):
		if self.docstatus != 1:
			return {"status": "skipped", "message": "Receipting document must be submitted to reconcile."}

		# Safety check: do not recreate if the invoice is already paid by another receipt
		for row in self.invoice:
			if not row.get("invoice_number") or flt(row.get("allocated", 0)) <= 0:
				continue
			conflicting = frappe.db.sql("""
				SELECT pe.name, pe.reference_no
				FROM `tabPayment Entry` pe
				JOIN `tabPayment Entry Reference` per ON per.parent = pe.name
				WHERE per.reference_name = %s
				AND per.reference_doctype = 'Sales Invoice'
				AND pe.docstatus = 1
				AND pe.reference_no != %s
			""", (row.invoice_number, self.name), as_dict=True)

			if conflicting:
				return {
					"status": "skipped",
					"message": f"Invoice {row.invoice_number} already paid by {conflicting[0].reference_no}. Skipping reconciliation to prevent duplicate."
				}

		# Fetch all Payment Entries associated with this receipt (reference_no)
		pes = frappe.get_all(
			"Payment Entry",
			filters={"reference_no": self.name, "docstatus": ["!=", 2]},
			fields=["name", "docstatus", "received_amount"]
		)

		has_error = False
		error_message = ""

		if len(pes) > 1:
			has_error = True
			error_message = f"Duplicate Payment Entries found: {[pe.name for pe in pes]}"
		elif len(pes) == 1:
			pe = pes[0]
			if flt(pe.received_amount) != flt(self.total_allocated):
				has_error = True
				error_message = f"Amount mismatch: Payment Entry received {pe.received_amount} vs Receipting allocated {self.total_allocated}"
			elif pe.docstatus != 1:
				has_error = True
				error_message = f"Payment Entry {pe.name} is not submitted (draft status)."
		else:
			has_error = True
			error_message = "No active Payment Entry found."

		if has_error:
			# Cancel and delete existing bad/duplicate Payment Entries
			for pe in pes:
				try:
					pe_doc = frappe.get_doc("Payment Entry", pe.name)
					pe_doc.flags.ignore_permissions = True
					if pe_doc.docstatus == 1:
						pe_doc.cancel()
					pe_doc.delete()
				except Exception as e:
					frappe.log_error(
						title=f"Reconcile failed to cancel/delete bad Payment Entry {pe.name} for Receipt {self.name}",
						message=frappe.get_traceback()
					)
			
			# Recreate clean Payment Entry
			try:
				self.create_payment_entry()
				frappe.db.commit()
				return {"status": "recreated", "message": f"Successfully deleted bad/duplicate Payment Entries and recreated one clean. Reason: {error_message}"}
			except Exception as e:
				frappe.log_error(
					title=f"Reconcile failed to recreate Payment Entry for Receipt {self.name}",
					message=frappe.get_traceback()
				)
				return {"status": "error", "message": f"Discrepancy found ({error_message}), but recreation failed: {str(e)}"}

		return {"status": "ok", "message": f"Payment Entry {pes[0].name} is fully reconciled and verified."}


@frappe.whitelist()
def reconcile_receipt(receipt_name):
	"""
	Whitelisted API to verify and reconcile a specific Receipting record.
	Validates the existence, uniqueness, correctness, and status of its Payment Entry.
	Deletes any duplicates or bad records and recreates them clean.
	"""
	try:
		doc = frappe.get_doc("Receipting", receipt_name)
		return doc.verify_and_reconcile_payment_entry()
	except Exception as e:
		frappe.log_error(
			title=f"API Reconcile Receipt {receipt_name} failed",
			message=frappe.get_traceback()
		)
		return {"status": "error", "message": str(e)}
