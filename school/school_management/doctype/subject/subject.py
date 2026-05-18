import frappe
from frappe.model.document import Document

class Subject(Document):
	pass


def has_permission(doc, ptype="read", user=None):
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)
    
    # Administrators and System Managers and School Users have standard permissions
    if user == "Administrator" or "System Manager" in roles or "School User" in roles:
        return True

    # Find the Teacher ID associated with this user
    teacher = frappe.db.get_value("Teacher", {"portal_email": user}, "name")
    if not teacher:
        teacher = frappe.db.get_value("Teacher", {"email": user}, "name")
    
    if not teacher:
        return False

    # Check if the teacher is an HOD of any department
    hod_departments = frappe.get_all("Department", filters={"hod": teacher}, pluck="name")
    
    if hod_departments:
        # HODs have rights only to subjects belonging to their department(s)
        if doc.department:
            return doc.department in hod_departments
        return False

    # For standard teachers: check if the subject is assigned to them in Teacher Subject Assignment
    assigned = frappe.db.get_all("Teacher Subject Assignment Item", filters={"parent": teacher}, pluck="subject")
    if assigned:
        return doc.name in assigned

    return False
