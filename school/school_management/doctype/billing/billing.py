import frappe
from frappe.model.document import Document

class Billing(Document):

    def validate(self):
        self.update_student_count()
        self.calculate_amounts()

    def update_student_count(self):
        filters = {"student_class": self.student_class}
        if self.section:
            filters["section"] = self.section
        self.number_of_students = frappe.db.count("Student", filters=filters)

    def calculate_amounts(self):
        total = 0
        for item in self.items:
            item.amount = (item.rate or 0) * (item.qty or 1)
            total += item.amount
        self.total_amount = total

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
        filters = {"student_class": self.student_class}
        if self.section:
            filters["section"] = self.section

        students = frappe.get_all("Student", filters=filters, fields=["name", "full_name"])

        if not students:
            frappe.throw("No students found for the selected class/section.")

        company = frappe.defaults.get_global_default("company")
        created = 0
        skipped = 0

        for student in students:
            if not student.full_name:
                skipped += 1
                continue

            try:
                # Auto-create customer if not exists
                self.ensure_customer_exists(student.full_name)

                invoice = frappe.new_doc("Sales Invoice")
                invoice.customer = student.full_name
                invoice.fees_structure = self.fees_structure
                invoice.billing_reference = self.name
                invoice.company = company
                invoice.posting_date = self.date or frappe.utils.today()
                invoice.due_date = self.date or frappe.utils.today()
                invoice.set_posting_time = 1

                for item in self.items:
                    invoice.append("items", {
                        "item_code": item.item_code,
                        "item_name": item.item_name,
                        "qty": item.qty or 1,
                        "rate": item.rate or 0,
                        "amount": item.amount or 0,
                    })

                invoice.flags.ignore_permissions = True
                invoice.insert()
                invoice.submit()
                created += 1

            except Exception as e:
                frappe.log_error(
                    title=f"Invoice creation failed for {student.full_name}",
                    message=str(e)
                )
                skipped += 1

        frappe.db.commit()
        frappe.msgprint(
            f"✓ {created} Sales Invoice(s) created successfully. {skipped} skipped.",
            title="Billing Submitted"
        )
