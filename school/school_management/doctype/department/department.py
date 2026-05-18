import frappe
from frappe.model.document import Document

class Department(Document):
    def validate(self):
        self.validate_hod_settings()

    def validate_hod_settings(self):
        # If this is not a new document, check if locking or deadline fields have changed
        if not self.is_new():
            old_doc = self.get_doc_before_save()
            if old_doc:
                locking_changed = (self.lock_schemes_submission != old_doc.lock_schemes_submission) or \
                                  (self.lock_exam_marks != old_doc.lock_exam_marks) or \
                                  (self.submission_deadline != old_doc.submission_deadline)
                
                if locking_changed:
                    user = frappe.session.user
                    if user != "Administrator" and "System Manager" not in frappe.get_roles(user):
                        # Find the Teacher ID associated with the current user's email
                        teacher = frappe.db.get_value("Teacher", {"portal_email": user}, "name")
                        if not teacher or teacher not in [self.hod, old_doc.hod]:
                            frappe.throw("Only the Head of Department (HOD) or a System Manager can lock submissions, lock exam marks, or change the deadline.")
