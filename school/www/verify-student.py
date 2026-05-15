import frappe

def get_context(context):
    student_id = frappe.form_dict.get('id')
    if not student_id:
        context.error = "No Student ID provided."
        return

    if not frappe.db.exists("Student", student_id):
        context.error = "Student record not found."
        return

    student = frappe.get_doc("Student", student_id)

    # Fetch school info from Cost Center
    school_info = {}
    if student.school:
        cost_center = frappe.get_doc("Cost Center", student.school)
        school_info['name'] = cost_center.cost_center_name or student.school
        
        # Try to get logo
        try:
            logo = frappe.db.get_value("Cost Center", student.school, "custom_logo")
        except Exception:
            logo = None
            
        if not logo:
            company = frappe.db.get_value("Cost Center", student.school, "company")
            if company:
                logo = frappe.db.get_value("Company", company, "company_logo")
        
        if not logo:
            logo = frappe.db.get_single_value("Website Settings", "app_logo")
            
        school_info['logo'] = logo

    context.student = student
    context.school = school_info
