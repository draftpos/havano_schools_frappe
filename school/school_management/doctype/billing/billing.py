import frappe

class Billing(frappe.model.document.Document):

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
        frappe.msgprint(f"Billing submitted for {self.number_of_students} students.")
