import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today

class Scheme(Document):
    def validate(self):
        self.auto_fetch_teacher()
        self.validate_and_populate_schemes()

    def auto_fetch_teacher(self):
        # Auto-fetch current teacher if not set
        if not self.teacher:
            teacher = frappe.db.get_value("Teacher", {"portal_email": frappe.session.user}, "name")
            if teacher:
                self.teacher = teacher

    def validate_and_populate_schemes(self):
        user = frappe.session.user
        is_admin_or_mgr = (user == "Administrator" or "System Manager" in frappe.get_roles(user))

        if not self.schemes:
            frappe.throw("Please add at least one scheme row to the table before saving.")

        for row in self.schemes:
            # 1. Fetch HOD from Subject's Department
            if row.subject:
                dept = frappe.db.get_value("Subject", row.subject, "department")
                if dept:
                    hod = frappe.db.get_value("Department", dept, "hod")
                    if hod:
                        row.hod = hod
                    
                    # 2. Enforce lock and deadline rules (System Manager / Administrator bypassed)
                    if not is_admin_or_mgr:
                        dept_doc = frappe.get_doc("Department", dept)

                        # Check if locked
                        if dept_doc.lock_schemes_submission:
                            frappe.throw(
                                f"Row {row.idx}: Scheme submission for department '{dept}' "
                                "has been locked by the HOD."
                            )

                        # Check if deadline passed
                        if dept_doc.submission_deadline:
                            if getdate(today()) > getdate(dept_doc.submission_deadline):
                                frappe.throw(
                                    f"Row {row.idx}: The scheme submission deadline "
                                    f"({dept_doc.submission_deadline}) for department '{dept}' has passed."
                                )
                else:
                    frappe.throw(
                        f"Row {row.idx}: The subject '{row.subject}' is not assigned to any Department. "
                        "Please assign a department to this subject first."
                    )


def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    # Administrators and System Managers have full visibility
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return ""

    # Find the Teacher ID associated with this user
    teacher = frappe.db.get_value("Teacher", {"portal_email": user}, "name")
    if not teacher:
        return "1=0"

    # Find departments where this teacher is HOD
    hod_departments = frappe.get_all("Department", filters={"hod": teacher}, pluck="name")

    if hod_departments:
        # HOD can view:
        # 1. Their own schemes (where they are the teacher)
        # 2. Schemes where at least one child table row subject belongs to their department(s)
        subjects = frappe.get_all("Subject", filters={"department": ["in", hod_departments]}, pluck="name")
        if subjects:
            subject_list = ", ".join(frappe.db.escape(s) for s in subjects)
            # Find parent scheme document names that contain any row with these subjects
            subquery = f"SELECT parent FROM `tabScheme Entry` WHERE subject IN ({subject_list})"
            return f"(`tabScheme`.teacher = {frappe.db.escape(teacher)} OR `tabScheme`.name IN ({subquery}))"
        else:
            return f"`tabScheme`.teacher = {frappe.db.escape(teacher)}"
    else:
        # Regular teachers can only view their own schemes
        return f"`tabScheme`.teacher = {frappe.db.escape(teacher)}"


def has_permission(doc, ptype="read", user=None):
    if not user:
        user = frappe.session.user

    # Administrators and System Managers have full permissions
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return True

    # Find the Teacher ID associated with this user
    teacher = frappe.db.get_value("Teacher", {"portal_email": user}, "name")
    if not teacher:
        return False

    # During document creation (insert), allow the teacher to insert
    if ptype == "create":
        return True

    # A teacher can always read/write/delete their own schemes
    if doc.teacher == teacher or not doc.teacher:
        return True

    # For other people's schemes, if checking read permission:
    if ptype == "read" and doc.schemes:
        for row in doc.schemes:
            if row.subject:
                dept = frappe.db.get_value("Subject", row.subject, "department")
                if dept:
                    hod = frappe.db.get_value("Department", dept, "hod")
                    # If the user is the HOD of any row's subject department, they can view it
                    if hod == teacher:
                        return True

    return False
