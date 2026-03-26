# Copyright (c) 2026, Ashley and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today, flt
from frappe import _

class Billing(Document):

    def validate(self):
        self.calculate_amounts()
        self.update_student_count()

    def update_student_count(self):
        if self.student:
            self.number_of_students = 1
            return

        filters = self.get_student_filters()
        
        if not filters:
            self.number_of_students = 0
            return

        self.number_of_students = frappe.db.count("Student", filters=filters)

    def calculate_amounts(self):
        total = 0
        for item in self.items:
            item.qty = flt(item.qty) or 1.0
            item.rate = flt(item.rate) or 0.0
            item.amount = item.qty * item.rate
            total += item.amount
        self.total_amount = total

    def get_student_filters(self):
        filters = {}
        
        if self.student_class:
            filters["student_class"] = self.student_class
        if self.section:
            filters["section"] = self.section
        if self.status:
            filters["student_type"] = self.status
        if self.cost_center:
            filters["school"] = self.cost_center
        if self.category_1:
            filters["category_1"] = self.category_1
        if self.category_2:
            filters["category_2"] = self.category_2
        if self.category_3:
            filters["category_3"] = self.category_3
        if self.area:
            filters["area"] = self.area
        if self.territory:
            filters["territory"] = self.territory
        if self.fees_category:
            filters["fees_category"] = self.fees_category
        
        return filters

    def on_submit(self):
        self.create_student_invoices()

    def ensure_customer_exists(self, full_name):
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
            full_name = s.get("full_name") if isinstance(s, dict) else getattr(s, "full_name", None)
            
            if not full_name:
                skipped += 1
                continue

            try:
                self.ensure_customer_exists(full_name)

                invoice = frappe.new_doc("Sales Invoice")
                invoice.customer = full_name
                invoice.fees_structure = self.fees_structure
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
            _("✓ {0} Sales Invoice(s) created. {1} skipped.").format(created, skipped),
            title="Billing Process Complete"
        )

@frappe.whitelist()
def get_student_count(student_class=None, section=None, status=None, cost_center=None, category_1=None, category_2=None, category_3=None, area=None, territory=None, fees_category=None):
    filters = {}
    if student_class:
        filters["student_class"] = student_class
    if section:
        filters["section"] = section
    if status:
        filters["student_type"] = status
    if cost_center:
        filters["school"] = cost_center
    if category_1:
        filters["category_1"] = category_1
    if category_2:
        filters["category_2"] = category_2
    if category_3:
        filters["category_3"] = category_3
    if area:
        filters["area"] = area
    if territory:
        filters["territory"] = territory
    if fees_category:
        filters["fees_category"] = fees_category
    count = frappe.db.count("Student", filters=filters)
    return {"count": count}

# Commented out as per request
# @frappe.whitelist()
# def get_fees_structure_by_status(status):
#     settings = frappe.get_single("School Settings")
#     for m in (settings.student_status_mappings or []):
#         if m.status == status:
#             return m.fees_structure
#     return None



