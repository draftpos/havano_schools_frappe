import frappe
from school.school.api import get_term_exam_results

@frappe.whitelist(allow_guest=True)
def debug_report(student=""):
    try:
        # Find a draft F6 report
        reports = frappe.db.get_all("Term Exam Report", filters={"student_class": ["like", "%F6%"]}, limit=1)
        if not reports:
            reports = frappe.db.get_all("Term Exam Report", limit=1)
            
        if not reports:
            return {"error": "No reports found"}
            
        report_name = reports[0].name
        
        if not student:
            # get a student from this report
            items = frappe.db.get_all("Term Exam Result Item", filters={"parent": report_name}, fields=["student"], limit=1)
            if not items:
                return {"error": "No items found in report " + report_name}
            student = items[0].student
            
        res = get_term_exam_results(report_name, student)
        
        items = res.get("items", [])
        if not items:
            return {"error": "get_term_exam_results returned no items for student " + student + " in " + report_name}
            
        return {
            "report_name": report_name,
            "student": student,
            "student_class": res.get("report", {}).get("student_class"),
            "items_count": len(items),
            "first_item_admin_comment": items[0].get("admin_comment"),
            "first_item_grade": items[0].get("grade"),
            "first_item_status": items[0].get("status"),
            "first_item_marks": items[0].get("marks_obtained"),
            "all_items": items
        }
    except Exception as e:
        return {"error": str(e)}
