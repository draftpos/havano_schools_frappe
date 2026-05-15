import frappe
import subprocess
import os

def redirect_to_portal():
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/portal-login"
        return
    
    roles = frappe.get_roles(user)
    
    # Matching logic from get_user_redirect in api.py
    user_key = user.strip().lower()
    
    if "System Manager" in roles or "Administrator" in roles:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/app"
    elif frappe.db.exists("Teacher", {"portal_email": user_key}) or frappe.db.exists("Teacher", {"employee_email": user_key}) or frappe.db.exists("Teacher", {"email": user_key}):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/assets/school/html/teacher-portal.html"
    elif frappe.db.exists("Parent", {"portal_email": user_key}):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/assets/school/html/parent-portal.html"
    elif frappe.db.exists("Student", {"portal_email": user_key}):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/assets/school/html/student-portal.html"
    elif "School User" in roles or "Accounts User" in roles or "Accounts Manager" in roles or "HR User" in roles or "HR Manager" in roles:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/app"
    elif frappe.db.get_roles and any(r not in ["Guest", "All"] for r in roles):
        # Any user with a real role goes to /app
        backend_roles = [r for r in roles if r not in ["Guest", "All", "Student", "Student Portal"]]
        if backend_roles:
            frappe.local.response["type"] = "redirect"
            frappe.local.response["location"] = "/app"
        else:
            frappe.local.response["type"] = "redirect"
            frappe.local.response["location"] = "/assets/school/html/student-portal.html"
    else:
        # Final fallback to student portal if no specific match
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/assets/school/html/student-portal.html"

SCHOOL_MODULES = ["School Management"]

def export_doctype_on_save(doc, method=None):
    if doc.module not in SCHOOL_MODULES:
        return
    _run_export()

def export_client_script_on_save(doc, method=None):
    _run_export()

def export_server_script_on_save(doc, method=None):
    _run_export()

def _run_export():
    try:
        bench_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
        )
        subprocess.Popen(
            ["bench", "--site", frappe.local.site, "export-fixtures", "--app", "school"],
            cwd=bench_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        frappe.log_error(str(e), "Auto Export Fixtures Failed")

@frappe.whitelist(allow_guest=False)
def get_dashboard_data(cost_center=None, fee_structure=None, academic_term=None, academic_year=None, date=None, student_class=None, section=None):
    data = {}

    student_filters = {}
    invoice_filters = {'docstatus': 1}
    if cost_center:
        student_filters['cost_center'] = cost_center
        invoice_filters['cost_center'] = cost_center
    if fee_structure:
        invoice_filters['fees_structure'] = fee_structure
    meta = frappe.get_meta('Sales Invoice')
    if academic_term:
        if meta.has_field('academic_term'):
            invoice_filters['academic_term'] = academic_term
        elif meta.has_field('custom_academic_term'):
            invoice_filters['custom_academic_term'] = academic_term
    if academic_year:
        if meta.has_field('academic_year'):
            invoice_filters['academic_year'] = academic_year
        elif meta.has_field('custom_academic_year'):
            invoice_filters['custom_academic_year'] = academic_year
    if date:
        invoice_filters['posting_date'] = date
    if student_class:
        if meta.has_field('student_class'):
            invoice_filters['student_class'] = student_class
        elif meta.has_field('custom_student_class'):
            invoice_filters['custom_student_class'] = student_class
    if section:
        if meta.has_field('section'):
            invoice_filters['section'] = section
        elif meta.has_field('custom_section'):
            invoice_filters['custom_section'] = section
        elif meta.has_field('custom_student_section'):
            invoice_filters['custom_student_section'] = section

    try: data['students'] = frappe.db.count('Student', filters=student_filters)
    except: data['students'] = 0
    try: data['exams'] = frappe.db.count('Exam Schedule')
    except: data['exams'] = 0
    try: data['tests'] = frappe.db.count('Test Schedule')
    except: data['tests'] = 0
    try: data['homework'] = frappe.db.count('Home Schedule')
    except: data['homework'] = 0
    try:
        first_inv = frappe.get_all('Sales Invoice', limit=1)
        if first_inv:
            frappe.log_error(str(frappe.get_meta('Sales Invoice').fields), "Sales Invoice Fields")
        data['invoices'] = frappe.get_all('Sales Invoice',
            filters=invoice_filters,
            fields=['grand_total','outstanding_amount','status','customer','posting_date','cost_center'],
            limit=0)
    except Exception as e: 
        frappe.log_error(str(e), "Invoices Fetch Error")
        data['invoices'] = []
    try:
        data['opening_balance_total'] = 0
        data['opening_balance_students'] = []
    except:
        data['opening_balance_total'] = 0
        data['opening_balance_students'] = []
    try:
        all_classes = frappe.get_all('Student Class', fields=['name','class_name'], limit=100)
        for c in all_classes:
            f = {'student_class': c['name']}
            if cost_center: f['cost_center'] = cost_center
            c['student_count'] = frappe.db.count('Student', filters=f)
        data['classes'] = all_classes
    except: data['classes'] = []
    try:
        data['cost_centers'] = frappe.get_all('Cost Center',
            filters={'is_group': 0},
            fields=['name'], limit=100)
    except: data['cost_centers'] = []
    try:
        data['fee_structures'] = frappe.get_all('Fees Structure', fields=['name'], limit=100)
    except: data['fee_structures'] = []
    try:
        data['academic_terms'] = frappe.get_all('Academic Term', fields=['name'], limit=100)
    except: data['academic_terms'] = []
    try:
        data['academic_years'] = frappe.get_all('Academic Year', fields=['name'], limit=100)
    except: data['academic_years'] = []
    try:
        data['sections'] = frappe.get_all('Section', fields=['name'], limit=100)
    except: data['sections'] = []
    try:
        data['student_classes'] = frappe.get_all('Student Class', fields=['name'], limit=100)
    except: data['student_classes'] = []
    try:
        data['exams_list'] = frappe.get_all('Exam Schedule',
            fields=['name','title','subject','date'], limit=6, order_by='date asc')
    except: data['exams_list'] = []
    try:
        data['homework_list'] = frappe.get_all('Home Schedule',
            fields=['name','subject','student_class','date'], limit=6, order_by='date desc')
    except: data['homework_list'] = []
    try:
        user = frappe.get_doc('User', frappe.session.user)
        data['user'] = {'full_name': user.full_name}
    except: data['user'] = {'full_name': 'Administrator'}
    return data
