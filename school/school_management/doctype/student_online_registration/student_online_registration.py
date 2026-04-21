# -*- coding: utf-8 -*-
# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class StudentOnlineRegistration(Document):
    
    def before_insert(self):
        if not self.enrollment_status:
            self.enrollment_status = "Pending"
        # Set full name
        self.full_name = "{} {} {}".format(
            self.first_name or "",
            self.second_name or "",
            self.last_name or ""
        ).strip()
    
    def validate(self):
        # If approving, ensure section is selected
        if self.enrollment_status == "Approved" and not self.approved_section:
            frappe.throw(_("Please select an approved section before approving the registration"))
    
    def after_insert(self):
        # Auto-create student if status is Approved
        if self.enrollment_status == "Approved" and not self.student_created:
            self.create_student_record()
    
    def on_update(self):
        # When status changes to Approved, create student
        if self.enrollment_status == "Approved" and not self.student_created:
            self.create_student_record()
        
        # Send email notification when status changes to Approved or Rejected
        if self.enrollment_status in ("Approved", "Rejected"):
            self.send_status_email()
    
    def send_status_email(self):
        """Send an email to the student notifying them of their enrollment decision."""
        recipient = self.portal_email
        if not recipient:
            frappe.log_error(
                "No portal email found for registration {0}. Status email not sent.".format(self.name)
            )
            return

        student_name = self.full_name or "{} {}".format(self.first_name or "", self.last_name or "").strip()

        if self.enrollment_status == "Approved":
            subject = _("Your School Registration Has Been Approved")
            message = _("""
                <p>Dear {student_name},</p>

                <p>We are pleased to inform you that your online registration (<strong>{reg_no}</strong>)
                has been <strong>approved</strong>.</p>

                <p><strong>Details:</strong></p>
                <ul>
                    <li><strong>Class:</strong> {student_class}</li>
                    <li><strong>Assigned Section:</strong> {approved_section}</li>
                    <li><strong>School:</strong> {school}</li>
                </ul>

                <p>Please report to the school administration office to complete any remaining
                formalities and collect your admission documents.</p>

                <p>We look forward to welcoming you!</p>

                <p>Regards,<br/>School Administration</p>
            """).format(
                student_name=student_name,
                reg_no=self.name,
                student_class=self.student_class or "N/A",
                approved_section=self.approved_section or "To Be Assigned",
                school=self.school or "N/A"
            )

        else:  # Rejected
            subject = _("Update on Your School Registration")
            message = _("""
                <p>Dear {student_name},</p>

                <p>Thank you for submitting your registration (<strong>{reg_no}</strong>).
                After careful review, we regret to inform you that your application has
                been <strong>rejected</strong>.</p>

                {remarks_section}

                <p>If you believe this decision was made in error or would like further
                information, please contact the school administration office.</p>

                <p>Regards,<br/>School Administration</p>
            """).format(
                student_name=student_name,
                reg_no=self.name,
                remarks_section=(
                    "<p><strong>Reason:</strong> {}</p>".format(self.approval_remarks)
                    if self.approval_remarks else ""
                )
            )

        try:
            frappe.sendmail(
                recipients=[recipient],
                subject=subject,
                message=message,
                now=True
            )
        except Exception as e:
            frappe.log_error(
                "Failed to send status email for registration {0}: {1}".format(self.name, str(e))
            )

    def generate_student_reg_no(self):
        """Generate a unique student registration number"""
        # Get current year
        year = frappe.utils.nowdate().split('-')[0]
        
        # Get the latest registration number for this year
        last_reg = frappe.db.sql("""
            SELECT student_reg_no FROM `tabStudent` 
            WHERE student_reg_no LIKE '%s-%%' 
            ORDER BY student_reg_no DESC LIMIT 1
        """ % year, as_dict=True)
        
        if last_reg:
            # Extract the number part and increment
            last_number = int(last_reg[0].student_reg_no.split('-')[1])
            new_number = last_number + 1
        else:
            new_number = 1
        
        # Format: YYYY-00001
        return "{}-{:05d}".format(year, new_number)
    
    def create_student_record(self):
        """Create student record from registration"""
        try:
            # Check if student already exists
            existing_student = frappe.db.exists("Student", {
                "first_name": self.first_name,
                "last_name": self.last_name,
                "student_email": self.portal_email
            })
            
            if existing_student:
                self.created_student = existing_student
                self.student_created = 1
                frappe.db.commit()
                frappe.msgprint(_("Student already exists: {0}").format(existing_student))
                return existing_student
            
            # Generate student registration number
            student_reg_no = self.generate_student_reg_no()
            
            # Create new student with ALL fields from registration
            student_dict = {
                "doctype": "Student",
                "student_reg_no": student_reg_no,
                "school": self.school,  # MANDATORY - from registration
                "first_name": self.first_name,
                "last_name": self.last_name,
                "student_class": self.student_class,  # MANDATORY - from registration
                "enrolled_in_class": self.student_class,
                "enrolled_in_section": self.approved_section,
                "student_type": self.student_type,
                "portal_email": self.portal_email,
                "portal_password": self.portal_password,
                "student_mobile_number": self.student_phone_number,
                "date_of_birth": self.date_of_birth,
                "gender": self.gender,
                "religion": self.religion,
                "date_of_admission": self.date_of_admission or frappe.utils.today()
            }
            
            # Add middle name if exists
            if self.second_name:
                student_dict["middle_name"] = self.second_name
            
            # Add national identification if exists
            if self.national_identification_number:
                student_dict["national_identification_number"] = self.national_identification_number
            
            # Add local identification if exists
            if self.local_identification_number:
                student_dict["local_identification_number"] = self.local_identification_number
            
            # Add previous school details if exists
            if self.previous_school_details:
                student_dict["previous_school_details"] = self.previous_school_details
            
            # Add medical history if exists
            if self.medical_history:
                student_dict["medical_history"] = self.medical_history
            
            # Add current address if exists
            if self.current_address:
                student_dict["current_address"] = self.current_address
            
            # Add permanent address if exists
            if self.permanent_address:
                student_dict["permanent_address"] = self.permanent_address
            
            student = frappe.get_doc(student_dict)
            student.insert()
            
            # Update registration record
            self.created_student = student.name
            self.student_created = 1
            frappe.db.commit()
            
            frappe.msgprint(_("Student {0} created successfully! Student Reg No: {1}").format(student.name, student_reg_no))
            return student.name
            
        except Exception as e:
            frappe.log_error("Failed to create student from registration {0}: {1}".format(self.name, str(e)))
            frappe.msgprint(_("Failed to create student: {0}").format(str(e)), alert=True)
            raise
