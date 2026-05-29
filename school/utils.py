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

    student_filters = {'transfer_status': 'Active'}
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
        data['invoices'] = frappe.get_all('Sales Invoice',
            filters=invoice_filters,
            fields=['grand_total','outstanding_amount','status','customer','posting_date','cost_center'],
            limit=None)
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
            f = {'student_class': c['name'], 'transfer_status': 'Active'}
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
        data['academic_terms'] = frappe.get_all('Term', fields=['name'], limit=100)
    except:
        try: data['academic_terms'] = frappe.get_all('Academic Term', fields=['name'], limit=100)
        except: data['academic_terms'] = []

    # Detect current active term (using is_active)
    current_term = None
    try:
        active_terms = frappe.get_all('Term', filters={'is_active': 1}, fields=['name'], limit=1)
        if active_terms:
            current_term = active_terms[0]['name']
    except:
        try:
            active_terms = frappe.get_all('Academic Term', filters={'is_active': 1}, fields=['name'], limit=1)
            if active_terms:
                current_term = active_terms[0]['name']
        except:
            current_term = None
    data['current_term'] = current_term
    try:
        data['academic_years'] = frappe.get_all('Academic Year', fields=['name'], limit=100)
    except: data['academic_years'] = []
    try:
        data['subjects'] = frappe.get_all('Subject', fields=['name', 'subject_name'], limit=200)
    except: data['subjects'] = []
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

@frappe.whitelist(allow_guest=False)
def get_exam_analysis_data(cost_center=None, academic_year=None, term=None, student_class=None, subject=None):
    # Retrieve all submitted Term Exam Reports matching the filters
    filters = {"docstatus": 1}
    if cost_center:
        filters["cost_center"] = cost_center
    if academic_year:
        filters["academic_year"] = academic_year
    if term:
        filters["term"] = term
    if student_class:
        filters["student_class"] = student_class

    reports = frappe.get_all("Term Exam Report", filters=filters, fields=["name", "cost_center", "academic_year", "term", "student_class"])
    if not reports:
        return {
            "average_score": 0,
            "pass_rate": 0,
            "total_students": 0,
            "total_exams": 0,
            "grade_distribution": {},
            "subject_performance": [],
            "class_performance": [],
            "top_students": [],
            "support_students": []
        }

    report_names = [r.name for r in reports]
    
    # Base filter for child rows
    item_filters = {"parent": ["in", report_names]}
    if subject:
        item_filters["subject"] = subject

    items = frappe.get_all(
        "Term Exam Result Item",
        filters=item_filters,
        fields=["parent", "student", "student_name", "subject", "marks_obtained", "max_marks", "percentage", "grade", "status"]
    )
    if not items:
        return {
            "average_score": 0,
            "pass_rate": 0,
            "total_students": 0,
            "total_exams": 0,
            "grade_distribution": {},
            "subject_performance": [],
            "class_performance": [],
            "top_students": [],
            "support_students": []
        }

    # Map reports by name for easy class/cost-center lookups
    report_map = {r.name: r for r in reports}

    # Standard calculations
    total_obtained = 0
    total_max = 0
    pass_count = 0
    valid_count = 0
    unique_students = set()

    grade_counts = {}
    subject_stats = {}
    class_stats = {}
    student_stats = {}

    for item in items:
        unique_students.add(item.student)
        
        # Track overall marks
        if item.marks_obtained is not None and item.max_marks:
            total_obtained += item.marks_obtained
            total_max += item.max_marks
            valid_count += 1
            if item.status == "Pass":
                pass_count += 1

        # Track grades
        if item.grade:
            grade_counts[item.grade] = grade_counts.get(item.grade, 0) + 1

        # Track subject performance
        sub = item.subject
        if sub:
            if sub not in subject_stats:
                subject_stats[sub] = {"obtained": 0, "max": 0, "pass": 0, "total": 0, "highest": 0, "lowest": 100}
            if item.marks_obtained is not None and item.max_marks:
                pct = (item.marks_obtained / item.max_marks) * 100
                subject_stats[sub]["obtained"] += item.marks_obtained
                subject_stats[sub]["max"] += item.max_marks
                subject_stats[sub]["total"] += 1
                if item.status == "Pass":
                    subject_stats[sub]["pass"] += 1
                if pct > subject_stats[sub]["highest"]:
                    subject_stats[sub]["highest"] = pct
                if pct < subject_stats[sub]["lowest"]:
                    subject_stats[sub]["lowest"] = pct

        # Lookup class via parent report
        rep = report_map.get(item.parent)
        cls = rep.student_class if rep else None
        if cls:
            if cls not in class_stats:
                class_stats[cls] = {"obtained": 0, "max": 0, "pass": 0, "total": 0}
            if item.marks_obtained is not None and item.max_marks:
                class_stats[cls]["obtained"] += item.marks_obtained
                class_stats[cls]["max"] += item.max_marks
                class_stats[cls]["total"] += 1
                if item.status == "Pass":
                    class_stats[cls]["pass"] += 1

        # Track student average for leaderboard and support lists
        stu = item.student
        if stu:
            if stu not in student_stats:
                student_stats[stu] = {
                    "name": item.student_name or stu,
                    "class": cls or "—",
                    "obtained": 0,
                    "max": 0,
                    "fails": [],
                    "total": 0
                }
            if item.marks_obtained is not None and item.max_marks:
                student_stats[stu]["obtained"] += item.marks_obtained
                student_stats[stu]["max"] += item.max_marks
                student_stats[stu]["total"] += 1
                if item.status == "Failed":
                    student_stats[stu]["fails"].append(sub)

    # Compile Final Averages
    avg_score = round((total_obtained / total_max * 100), 1) if total_max > 0 else 0
    overall_pass = round((pass_count / valid_count * 100), 1) if valid_count > 0 else 0

    # Aggregate Subject-wise metrics
    subject_perf = []
    for sub, stats in subject_stats.items():
        avg = round((stats["obtained"] / stats["max"] * 100), 1) if stats["max"] > 0 else 0
        pr = round((stats["pass"] / stats["total"] * 100), 1) if stats["total"] > 0 else 0
        # Fetch subject teacher
        try:
            teacher = frappe.db.get_value("Teacher Subject Assignment", {"subject": sub}, "teacher") or "—"
        except:
            teacher = "—"
        subject_perf.append({
            "subject": sub,
            "teacher": teacher,
            "average": avg,
            "pass_rate": pr,
            "highest": round(stats["highest"], 1) if stats["highest"] != 0 else 0,
            "lowest": round(stats["lowest"], 1) if stats["lowest"] != 100 else 0
        })

    # Aggregate Class-wise metrics
    class_perf = []
    for cls, stats in class_stats.items():
        avg = round((stats["obtained"] / stats["max"] * 100), 1) if stats["max"] > 0 else 0
        pr = round((stats["pass"] / stats["total"] * 100), 1) if stats["total"] > 0 else 0
        class_perf.append({
            "class_name": cls,
            "average": avg,
            "pass_rate": pr
        })

    # Sort students by average percentage
    all_students_summary = []
    for stu, stats in student_stats.items():
        avg = round((stats["obtained"] / stats["max"] * 100), 1) if stats["max"] > 0 else 0
        all_students_summary.append({
            "student": stu,
            "name": stats["name"],
            "class_name": stats["class"] or "—",
            "average": avg,
            "fails": stats["fails"]
        })

    # Leaderboard (Top 10)
    top_students = sorted(all_students_summary, key=lambda x: x["average"], reverse=True)[:10]

    # Support / Academic Interventions (under 50% or failed at least one subject)
    support_students = [
        s for s in all_students_summary 
        if s["average"] < 50 or len(s["fails"]) > 0
    ]
    support_students = sorted(support_students, key=lambda x: (len(x["fails"]), x["average"]), reverse=True)[:10]

    return {
        "average_score": avg_score,
        "pass_rate": overall_pass,
        "total_students": len(unique_students),
        "total_exams": len(items),
        "grade_distribution": grade_counts,
        "subject_performance": sorted(subject_perf, key=lambda x: x["average"], reverse=True),
        "class_performance": sorted(class_perf, key=lambda x: x["average"], reverse=True),
        "top_students": top_students,
        "support_students": support_students
    }
