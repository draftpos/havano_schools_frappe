# Copyright (c) 2026, Administrator and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document

class Teacher(Document):
    def before_save(self):
        self.full_name = f"{self.first_name or ''} {self.last_name or ''}".strip()

    def after_insert(self):
        self.create_teacher_user()

    def on_update(self):
        if self.create_user and self.portal_email:
            self.create_teacher_user()

    def create_teacher_user(self):
        if not self.create_user or not self.portal_email:
            return

        if frappe.db.exists("User", self.portal_email):
            # Update existing user roles if needed
            user = frappe.get_doc("User", self.portal_email)
            role_names = [r.role for r in user.roles]
            if "Teacher" not in role_names:
                user.append("roles", {"role": "Teacher"})
                user.save(ignore_permissions=True)
                frappe.db.commit()
            return

        # Create new user
        user = frappe.get_doc({
            "doctype": "User",
            "email": self.portal_email,
            "first_name": self.first_name,
            "last_name": self.last_name or "",
            "enabled": 1,
            "user_type": "System User",
            "send_welcome_email": 1,
            "roles": [{"role": "Teacher"}]
        })
        user.insert(ignore_permissions=True)
        frappe.db.commit()
        frappe.msgprint(f"Portal user created for {self.full_name} ({self.portal_email})")
