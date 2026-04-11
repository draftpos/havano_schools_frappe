import frappe
from frappe.model.document import Document

class TestSchedule(Document):
    pass

@frappe.whitelist()
def get_teacher_subjects(student_class=""):
    teacher_email = frappe.session.user
    # Get subjects assigned to this teacher
    filters = {"parent": teacher_email}
    if student_class:
        filters["class_name"] = student_class
    items = frappe.get_all(
        "Teacher Subject Assignment Item",
        filters=filters,
        fields=["subject"],
        ignore_permissions=True
    )
    subjects = list(set([i["subject"] for i in items if i["subject"]]))
    return subjects

@frappe.whitelist()
def get_students(student_class, section=""):
    filters = {"student_class": student_class}
    if section:
        filters["section"] = section
    students = frappe.get_all(
        "Student",
        filters=filters,
        fields=["student_reg_no", "full_name"],
        order_by="full_name asc"
    )
    return students
