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
    # Admin/System Manager always go to ERPNext dashboard first
    if "System Manager" in roles or "Administrator" in roles:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/app"
    elif frappe.db.exists("Student", {"portal_email": user}):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/assets/school/html/student-portal.html"
    elif "School User" in roles:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/app"
    else:
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
def get_dashboard_data():
    data = {}
    try: data['students'] = frappe.db.count('Student')
    except: data['students'] = 0
    try: data['exams'] = frappe.db.count('Exam Schedule')
    except: data['exams'] = 0
    try: data['tests'] = frappe.db.count('Test Schedule')
    except: data['tests'] = 0
    try: data['homework'] = frappe.db.count('Home Schedule')
    except: data['homework'] = 0
    try:
        data['invoices'] = frappe.get_all('Sales Invoice',
            filters={'docstatus': 1},
            fields=['grand_total','outstanding_amount','status','customer','posting_date'],
            limit=0)
    except: data['invoices'] = []
    try:
        opening_students = frappe.get_all('Student',
            filters={'has_opening_balance': 1},
            fields=['full_name', 'opening_balance', 'opening_balance_date'])
        data['opening_balance_total'] = sum(s.opening_balance or 0 for s in opening_students)
    except:
        data['opening_balance_total'] = 0
    try: data['classes'] = frappe.get_all('Student Class', fields=['name','class_name'], limit=20)
    except: data['classes'] = []
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
