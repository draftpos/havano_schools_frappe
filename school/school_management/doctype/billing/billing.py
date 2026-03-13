import frappe
from frappe.model.document import Document

class Billing(Document):

    def validate(self):
        self.update_student_count()
        self.calculate_amounts()

    def update_student_count(self):
        if self.student:
            self.number_of_students = 1
            return
        filters = {}
        if self.student_class:
            filters["student_class"] = self.student_class
        if self.section:
            filters["section"] = self.section
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
        if not filters:
            self.number_of_students = 0
            return
        self.number_of_students = frappe.db.count("Student", filters=filters)

    def calculate_amounts(self):
        for item in self.items:
            item.amount = (item.rate or 0) * (item.qty or 1)

    def on_submit(self):
        self.create_student_invoices()

    def ensure_customer_exists(self, full_name):
        if not frappe.db.exists("Customer", full_name):
            customer = frappe.get_doc({
                "doctype":       "Customer",
                "customer_name": full_name,
                "customer_type": "Individual",
                "customer_group": frappe.db.get_single_value("Selling Settings", "customer_group") or "All Customer Groups",
                "territory":     frappe.db.get_single_value("Selling Settings", "territory") or "All Territories",
            })
            customer.flags.ignore_permissions = True
            customer.insert()
        return full_name

    def create_student_invoices(self):
        if self.student:
            student_doc = frappe.get_doc("Student", self.student)
            students = [{"name": student_doc.name, "full_name": student_doc.full_name}]
        else:
            filters = {}
            if self.student_class:
                filters["student_class"] = self.student_class
            if self.section:
                filters["section"] = self.section
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
            if not filters:
                frappe.throw("Please select at least one filter to bill students.")
            students = frappe.get_all("Student", filters=filters, fields=["name", "full_name"])

        if not students:
            frappe.throw("No students found for the selected filters.")

        company = frappe.defaults.get_global_default("company")
        created = 0
        skipped = 0

        for student in students:
            if not student.full_name:
                skipped += 1
                continue
            try:
                self.ensure_customer_exists(student.full_name)

                invoice = frappe.new_doc("Sales Invoice")
                invoice.customer          = student.full_name
                invoice.fees_structure    = self.fees_structure
                invoice.billing_reference = self.name
                invoice.company           = company
                invoice.posting_date      = self.date or frappe.utils.today()
                invoice.due_date          = self.date or frappe.utils.today()
                invoice.set_posting_time  = 1
                invoice.cost_center       = self.cost_center
                invoice.academic_term     = self.term
                invoice.academic_year     = self.year

                for item in self.items:
                    invoice.append("items", {
                        "item_code":   item.item_code,
                        "item_name":   item.item_name,
                        "qty":         item.qty or 1,
                        "rate":        item.rate or 0,
                        "amount":      item.amount or 0,
                        "cost_center": self.cost_center,
                    })

                invoice.flags.ignore_permissions = True
                invoice.insert()
                invoice.submit()
                created += 1

            except Exception as e:
                frappe.log_error(
                    title=f"Invoice creation failed for {student.full_name}",
                    message=frappe.get_traceback()
                )
                skipped += 1

        frappe.db.commit()
        frappe.msgprint(
            f"✓ {created} Sales Invoice(s) created. {skipped} skipped.",
            title="Billing Submitted"
        )