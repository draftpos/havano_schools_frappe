import frappe
from frappe.model.document import Document
from frappe.utils.password import update_password as _update_password

class Teacher(Document):

    def before_save(self):
        self.full_name = f"{self.first_name or ''} {self.last_name or ''}".strip()

    def validate(self):
        # Ensure password doesn't match name/ID
        if self.portal_password and self.name and self.portal_password == self.name:
            frappe.throw("Portal Password cannot be the same as your Teacher ID for security reasons.")

    def after_insert(self):
        if self.create_user and self.portal_email:
            self.create_teacher_user()

    def on_update(self):
        user_fields_changed = self.has_value_changed("portal_email") or self.has_value_changed("portal_password") or self.has_value_changed("create_user")
        if user_fields_changed and self.create_user and self.portal_email:
            self.create_teacher_user()

    def create_teacher_user(self):
        if not self.portal_email or not self.portal_password:
            return

        try:
            is_new = False
            if frappe.db.exists("User", self.portal_email):
                # Update existing user — ensure Teacher and Website User roles
                user = frappe.get_doc("User", self.portal_email)
                role_names = [r.role for r in user.roles]
                for role in ["Website User", "Teacher"]:
                    if role not in role_names:
                        user.append("roles", {"role": role})
                user.flags.ignore_permissions = True
                user.save(ignore_permissions=True)
            else:
                # Create new user
                is_new = True
                user = frappe.get_doc({
                    "doctype": "User",
                    "email": self.portal_email,
                    "first_name": self.first_name or self.full_name,
                    "last_name": self.last_name or "",
                    "enabled": 1,
                    "user_type": "Website User",
                    "send_welcome_email": 0,
                    "roles": [
                        {"role": "Website User"},
                        {"role": "Teacher"}
                    ]
                })
                user.flags.ignore_permissions = True
                user.insert(ignore_permissions=True)

            # Set manual password via official utility
            _update_password(self.portal_email, self.portal_password, logout_all_sessions=False)

            # Send manual portal credentials email
            try:
                frappe.sendmail(
                    recipients=[self.portal_email],
                    subject="Your Teacher Portal Access",
                    message=(
                        f"<p>Dear {self.full_name},</p>"
                        f"<p>Your teacher portal account has been {'created' if is_new else 'updated'}.</p>"
                        f"<hr>"
                        f"<p><b>Username:</b> {self.portal_email}</p>"
                        f"<p><b>Password:</b> {self.portal_password}</p>"
                        f"<p>Please log in here: <a href=\"{frappe.utils.get_url('/portal-login')}\">"
                        f"{frappe.utils.get_url('/portal-login')}</a></p>"
                        f"<p>Regards,<br>School Administration</p>"
                    ),
                )
            except Exception:
                pass

            frappe.msgprint(
                f"Portal user {'created' if is_new else 'updated'} for {self.full_name} ({self.portal_email}) with manual password. Credentials email sent.",
                indicator="green",
                alert=True
            )

        except Exception:
            frappe.log_error(
                title=f"Teacher portal user creation failed for {self.portal_email}",
                message=frappe.get_traceback()
            )

