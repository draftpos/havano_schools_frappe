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
    elif frappe.db.exists("Teacher", {"portal_email": user_key}) or frappe.db.exists("Teacher", {"employee_email": user_key}):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/assets/school/html/teacher-portal.html"
    elif frappe.db.exists("Parent", {"portal_email": user_key}):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/assets/school/html/parent-portal.html"
    elif frappe.db.exists("Student", {"portal_email": user_key}):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/assets/school/html/student-portal.html"
    elif "School User" in roles:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/app"
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
def get_dashboard_data(cost_center=None):
    data = {}

    student_filters = {}
    invoice_filters = {'docstatus': 1}
    if cost_center:
        student_filters['cost_center'] = cost_center
        invoice_filters['cost_center'] = cost_center

    try: data['students'] = frappe.db.count('Student', filters=student_filters)
    except: data['students'] = 0
    try: data['exams'] = frappe.db.count('Exam Schedule')
    except: data['exams'] = 0
    try: data['tests'] = frappe.db.count('Test Schedule')
    except: data['tests'] = 0
    try: data['homework'] = frappe.db.count('Home Schedule')
    except: data['homework'] = 0
    try:
        data['invoices'] = frappe.get_all('Sales Invoice',
            filters=invoice_filters,
            fields=['grand_total','outstanding_amount','status','customer','posting_date','cost_center'],
            limit=0)
    except: data['invoices'] = []
    try:
        # Opening balances now have their own Sales Invoices so no need to add separately
        # Just return 0 to avoid double counting with invoice outstanding
        data['opening_balance_total'] = 0
        data['opening_balance_students'] = []
    except:
        data['opening_balance_total'] = 0
        data['opening_balance_students'] = []
    try:
        student_classes = frappe.get_all('Student Class', fields=['name','class_name'], limit=20)
        for c in student_classes:
            f = {'student_class': c['name']}
            if cost_center: f['cost_center'] = cost_center
            c['student_count'] = frappe.db.count('Student', filters=f)
        data['classes'] = student_classes
    except: data['classes'] = []
    try:
        data['cost_centers'] = frappe.get_all('Cost Center',
            filters={'is_group': 0},
            fields=['name'], limit=50)
    except: data['cost_centers'] = []
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
