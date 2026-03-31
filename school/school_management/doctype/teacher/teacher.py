# Copyright (c) 2026, Administrator and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document

class Teacher(Document):

    def before_save(self):
        self.full_name = f"{self.first_name or ''} {self.last_name or ''}".strip()

    def after_insert(self):
        if self.create_user and self.portal_email:
            self.create_teacher_user()

    def on_update(self):
        if self.create_user and self.portal_email:
            self.create_teacher_user()

    def create_teacher_user(self):
        if not self.create_user or not self.portal_email:
            return

        try:
            if frappe.db.exists("User", self.portal_email):
                # Update existing user — ensure Teacher and Website User roles
                user = frappe.get_doc("User", self.portal_email)
                role_names = [r.role for r in user.roles]
                for role in ["Website User", "Teacher"]:
                    if role not in role_names:
                        user.append("roles", {"role": role})
                user.flags.ignore_permissions = True
                user.save(ignore_permissions=True)
                frappe.db.commit()
                frappe.msgprint(
                    f"Portal user updated for {self.full_name} ({self.portal_email})",
                    indicator="blue",
                    alert=True
                )
                return

            # Create new user
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

            # Send password reset email
            reset_key = user.reset_password()
            frappe.sendmail(
                recipients=[self.portal_email],
                sender="makoniashleytadiswa@gmail.com",
                subject="Your Teacher Portal Access",
                message="""<p>Dear {name},</p>
<p>Your teacher portal account has been created.</p>
<p>Email: {email}</p>
<p>Please click below to set your password:</p>
<p><a href="{url}/update-password?key={key}">Set Password & Login</a></p>
<p>Regards,<br>School Administration</p>""".format(
                    name=self.full_name,
                    email=self.portal_email,
                    url=frappe.utils.get_url(),
                    key=reset_key
                )
            )
            frappe.db.commit()
            frappe.msgprint(
                f"Portal user created for {self.full_name} ({self.portal_email})",
                indicator="green",
                alert=True
            )

        except Exception:
            frappe.log_error(
                title=f"Teacher portal user creation failed for {self.portal_email}",
                message=frappe.get_traceback()
            )