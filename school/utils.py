import frappe
import subprocess
import os
import frappe

def redirect_to_portal():
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = "/student-portal"
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
