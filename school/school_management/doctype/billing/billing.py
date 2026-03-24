# Copyright (c) 2026, Ashley and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today, flt

class Billing(Document):

    def validate(self):
        # Ensure rates and quantities are calculated before saving
        self.calculate_amounts()
        # Update the student count based on selected filters
        self.update_student_count()

    def update_student_count(self):
        """Counts how many students match the current filters."""
        if self.student:
            self.number_of_students = 1
            return

        filters = self.get_student_filters()
        
        if not filters:
            self.number_of_students = 0
            return

        self.number_of_students = frappe.db.count("Student", filters=filters)

    def calculate_amounts(self):
        """Calculates item totals and the document total amount."""
        total = 0
        for item in self.items:
            item.qty = flt(item.qty) or 1.0
            item.rate = flt(item.rate) or 0.0
            item.amount = item.qty * item.rate
            total += item.amount
        self.total_amount = total

    def get_student_filters(self):
        """Helper to build the filter dictionary for Student queries."""
        filters = {}
        # Prioritize 'section' but fall back to 'section1' if used
        active_section = self.section or self.section1
        
        # MODIFIED: Section is independent - no class requirement
        if self.student_class:   filters["student_class"] = self.student_class
        if active_section:       filters["section"] = active_section
        if self.cost_center:     filters["school"] = self.cost_center  # Mapping cost_center to Student.school
        if self.category_1:      filters["category_1"] = self.category_1
        if self.category_2:      filters["category_2"] = self.category_2
        if self.category_3:      filters["category_3"] = self.category_3
        if self.area:            filters["area"] = self.area
        if self.territory:       filters["territory"] = self.territory
        if self.fees_category:   filters["fees_category"] = self.fees_category
        
        return filters

    def on_submit(self):
        """Trigger invoice creation once the Billing record is submitted."""
        self.create_student_invoices()

    def ensure_customer_exists(self, full_name):
        """Checks if a Customer exists by name; creates one if not."""
        if not frappe.db.exists("Customer", full_name):
            customer = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": full_name,
                "customer_type": "Individual",
                "customer_group": frappe.db.get_single_value("Selling Settings", "customer_group") or "All Customer Groups",
                "territory": frappe.db.get_single_value("Selling Settings", "territory") or "All Territories",
            })
            customer.flags.ignore_permissions = True
            customer.insert()
        return full_name

    def create_student_invoices(self):
        """Generates a Sales Invoice for every student matching the filters."""
        students = []
        if self.student:
            student_doc = frappe.get_doc("Student", self.student)
            students = [{"name": student_doc.name, "full_name": student_doc.full_name}]
        else:
            filters = self.get_student_filters()
            if not filters:
                frappe.throw("Please select at least one filter to bill students.")
            
            students = frappe.get_all("Student", filters=filters, fields=["name", "full_name"])

        if not students:
            frappe.throw("No students found for the selected filters.")

        company = frappe.defaults.get_global_default("company")
        created = 0
        skipped = 0

        for s in students:
            # Handle both dict (get_all) and doc objects
            full_name = s.get("full_name") if isinstance(s, dict) else getattr(s, "full_name", None)
            
            if not full_name:
                skipped += 1
                continue

            try:
                self.ensure_customer_exists(full_name)

                invoice = frappe.new_doc("Sales Invoice")
                invoice.customer = full_name
                invoice.fees_structure = self.fees_structure
                # Custom fields for tracking back to this billing run
                invoice.update({
                    "billing_reference": self.name,
                    "company": company,
                    "posting_date": self.date or today(),
                    "due_date": self.date or today(),
                    "set_posting_time": 1,
                    "cost_center": self.cost_center,
                    "academic_term": self.term,
                    "academic_year": self.year
                })

                for item in self.items:
                    invoice.append("items", {
                        "item_code": item.item_code,
                        "item_name": item.item_name,
                        "qty": item.qty or 1,
                        "rate": item.rate or 0,
                        "amount": item.amount or 0,
                        "cost_center": self.cost_center,
                    })

                invoice.flags.ignore_permissions = True
                invoice.insert()
                invoice.submit()
                created += 1

            except Exception:
                frappe.log_error(
                    title=f"Invoice creation failed for {full_name}",
                    message=frappe.get_traceback()
                )
                skipped += 1

        frappe.db.commit()
        frappe.msgprint(
            f"✓ {created} Sales Invoice(s) created. {skipped} skipped.",
            title="Billing Process Complete"
        )