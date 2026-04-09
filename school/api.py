import frappe
from frappe import _

@frappe.whitelist()
def get_billing_summary(student=None):
    """
    Returns a unified view of Invoices and Receipting for the student portal.
    """
    user = frappe.session.user
    if user in ("Administrator", "Guest"):
        return {"error": "Invalid User"}

    if not student:
        student = frappe.db.get_value("Student", {"portal_email": user}, ["name", "full_name"], as_dict=True)
    else:
        student = frappe.db.get_value("Student", student, ["name", "full_name"], as_dict=True)
    if not student:
        return {"error": "Student record not found"}

    invoices = frappe.db.sql("""
        SELECT name, posting_date, due_date, grand_total, outstanding_amount, status,
               cost_center, fees_structure
        FROM `tabSales Invoice`
        WHERE customer_name = %s 
        ORDER BY posting_date DESC
    """, student.full_name, as_dict=True)

    for inv in invoices:
        inv['posting_date'] = str(inv['posting_date'])
        inv['due_date'] = str(inv['due_date'])
        inv['items'] = frappe.get_all("Sales Invoice Item", 
                                      filters={"parent": inv['name']}, 
                                      fields=["item_name", "qty", "rate", "amount"])

    receipts = frappe.db.sql("""
        SELECT name, date, total_outstanding, total_allocated, total_balance, account, docstatus
        FROM `tabReceipting` 
        WHERE student_name = %s 
        ORDER BY date DESC
    """, student.name, as_dict=True)

    for rec in receipts:
        rec['date'] = str(rec['date'])
        rec['items'] = frappe.get_all("Receipt Item", 
                                      filters={"parent": rec['name']}, 
                                      fields=["invoice_number", "fees_structure", "outstanding", "allocated"])

    return {
        "student": student, 
        "invoices": invoices, 
        "receipts": receipts
    }


@frappe.whitelist()
def get_student_invoices(student):
    """
    Used by the Receipting Form to auto-load outstanding invoices.
    """
    if not student:
        return []

    full_name = frappe.db.get_value("Student", student, "full_name")
    customer = frappe.db.get_value("Customer", {"customer_name": full_name}, "name")
    
    if not customer:
        customer = frappe.db.get_value("Customer", student, "name")

    if not customer:
        return []
    
    invoices = frappe.get_all("Sales Invoice",
        filters={
            "customer": customer, 
            "docstatus": 1, 
            "outstanding_amount": [">", 0]
        },
        fields=["name", "grand_total", "outstanding_amount", "fees_structure", "posting_date"],
        order_by="posting_date desc")
    
    for inv in invoices:
        inv["posting_date"] = str(inv["posting_date"])
        
    return invoices


@frappe.whitelist()
def get_my_account():
    user = frappe.session.user
    if user in ("Administrator", "Guest"): return []
    student = frappe.db.get_value("Student", {"portal_email": user},
        ["name", "first_name", "second_name", "last_name", "full_name",
         "student_reg_no", "student_class", "section", "house",
         "date_of_admission", "portal_email", "student_category"], as_dict=True)
    if student:
        student["class_name"] = frappe.db.get_value("Student Class", student.student_class, "class_name") or student.student_class
        student["date_of_admission"] = str(student.date_of_admission) if student.date_of_admission else "-"
    return student


@frappe.whitelist()
def get_portal_dashboard():
    user = frappe.session.user
    if user in ("Administrator", "Guest"):
        return {"error": "Not authorized"}
    student = frappe.db.get_value("Student", {"portal_email": user},
        ["name", "first_name", "second_name", "last_name", "full_name",
         "student_reg_no", "student_class", "section", "house", "student_image"], as_dict=True)
    if not student:
        return {"error": "Student not found"}
    sname = student.name
    s_class   = student.student_class or ""
    s_section = student.section or ""
    s_reg_no  = student.student_reg_no or sname

    class_filters   = {"student_class": s_class} if s_class else {}
    section_filters = {"student_class": s_class, "section": s_section} if s_class and s_section else class_filters

    exam_schedules = frappe.db.count("Exam Schedule",  section_filters) if s_class else 0
    home_schedules = frappe.db.count("Home Schedule",  section_filters) if s_class else 0
    test_schedules = frappe.db.count("Test Schedule",  section_filters) if s_class else 0
    exam_results   = frappe.db.count("Exam Schedule Item", {"student_admission_no": s_reg_no}) if frappe.db.exists("DocType", "Exam Schedule Item") else 0
    inclass_tests  = frappe.db.count("Inclass Test",   {}) if frappe.db.exists("DocType", "Inclass Test") else 0
    homework       = frappe.db.count("Home Schedule Item", {"student_admission_no": s_reg_no}) if frappe.db.exists("DocType", "Home Schedule Item") else 0
    billing_summary = frappe.db.sql("""
        SELECT SUM(outstanding_amount) as balance
        FROM `tabSales Invoice`
        WHERE customer_name = %s AND docstatus = 1
    """, student.full_name, as_dict=True)
    balance = billing_summary[0].balance if billing_summary and billing_summary[0].balance else 0
    class_name = frappe.db.get_value("Student Class", student.student_class, "class_name") or student.student_class or ""
    return {
        "student": {
            "name":       sname,
            "full_name":  student.full_name or f"{student.first_name or ''} {student.last_name or ''}".strip(),
            "reg_no":     student.student_reg_no or "",
            "class_name": class_name,
            "section":    student.section or "",
            "house":      student.house or "",
            "image":      student.student_image or "",
            "initials":   (student.first_name or "S")[0].upper()
        },
        "counts": {
            "exam_schedules": exam_schedules,
            "home_schedules": home_schedules,
            "test_schedules": test_schedules,
            "exam_results":   exam_results,
            "inclass_tests":  inclass_tests,
            "homework":       homework,
            "balance":        float(balance)
        }
    }


@frappe.whitelist()
def get_exam_schedules(student=None):
    user = frappe.session.user
    if user in ("Administrator", "Guest"): return []
    if not student:
        student = frappe.db.get_value("Student", {"portal_email": user},
            ["name", "student_reg_no", "student_class", "section"], as_dict=True)
    else:
        student = frappe.db.get_value("Student", student,
            ["name", "student_reg_no", "student_class", "section"], as_dict=True)
    if not student: return []
    s_reg_no  = student.student_reg_no or student.name
    s_class   = student.student_class or ""
    s_section = student.section or ""
    schedules = frappe.get_all("Exam Schedule",
        filters={"student_class": s_class, "section": s_section},
        fields=["name","title","subject","date","start_time","max_marks","min_marks",
                "total_questions","room_number","number_of_students","exam_type"],
        order_by="date asc") if s_class else []
    marks_map = {}
    if schedules:
        items = frappe.db.sql("""
            SELECT parent, marks_obtained, status
            FROM `tabExam Schedule Item`
            WHERE student_admission_no = %s
        """, s_reg_no, as_dict=True)
        marks_map = {i.parent: i for i in items}
    result = []
    for s in schedules:
        sub_name = frappe.db.get_value("Subject", s.subject, "subject_name") or s.subject or ""
        item = marks_map.get(s.name, {})
        result.append({
            "exam_name":        s.title or sub_name,
            "subject_name":     sub_name,
            "class_name":       s_class,
            "date":             str(s.date) if s.date else "",
            "start_time":       str(s.start_time) if s.start_time else "",
            "exam_type":        s.exam_type or "",
            "max_marks":        s.max_marks or 0,
            "min_marks":        s.min_marks or 0,
            "total_questions":  s.total_questions or 0,
            "room_number":      s.room_number or "",
            "number_of_students": s.number_of_students or 0,
            "marks_obtained":   item.get("marks_obtained", "") if item else "",
            "status":           item.get("status", "") if item else "",
            "remarks":          "",
        })
    return result


@frappe.whitelist()
def get_home_schedules(student=None):
    user = frappe.session.user
    if user in ("Administrator", "Guest"): return []
    if not student:
        student = frappe.db.get_value("Student", {"portal_email": user},
            ["name","student_reg_no","student_class","section"], as_dict=True)
    else:
        student = frappe.db.get_value("Student", student,
            ["name","student_reg_no","student_class","section"], as_dict=True)
    if not student: return []
    s_reg_no  = student.student_reg_no or student.name
    s_class   = student.student_class or ""
    s_section = student.section or ""
    schedules = frappe.get_all("Home Schedule",
        filters={"student_class": s_class, "section": s_section},
        fields=["name","test_name","subject","date","start_time","max_marks","min_marks"],
        order_by="date asc") if s_class else []
    marks_map = {}
    if schedules:
        items = frappe.db.sql("""
            SELECT parent, marks_obtained, status
            FROM `tabHome Schedule Item`
            WHERE student_admission_no = %s
        """, s_reg_no, as_dict=True)
        marks_map = {i.parent: i for i in items}
    result = []
    for s in schedules:
        sub_name = frappe.db.get_value("Subject", s.subject, "subject_name") or s.subject or ""
        hw_name  = frappe.db.get_value("Homework", s.test_name, "home_name") or s.test_name or ""
        item = marks_map.get(s.name, {})
        result.append({
            "exam_name":       hw_name,
            "subject_name":    sub_name,
            "class_name":      s_class,
            "date":            str(s.date) if s.date else "",
            "start_time":      str(s.start_time) if s.start_time else "",
            "max_marks":       s.max_marks or 0,
            "min_marks":       s.min_marks or 0,
            "marks_obtained":  item.get("marks_obtained","") if item else "",
            "status":          item.get("status","") if item else "",
            "remarks":         "",
        })
    return result


@frappe.whitelist()
def get_test_schedules(student=None):
    user = frappe.session.user
    if user in ("Administrator", "Guest"): return []
    if not student:
        student = frappe.db.get_value("Student", {"portal_email": user},
            ["name","student_reg_no","student_class","section"], as_dict=True)
    else:
        student = frappe.db.get_value("Student", student,
            ["name","student_reg_no","student_class","section"], as_dict=True)
    if not student: return []
    s_reg_no  = student.student_reg_no or student.name
    s_class   = student.student_class or ""
    s_section = student.section or ""
    schedules = frappe.get_all("Test Schedule",
        filters={"student_class": s_class, "section": s_section},
        fields=["name","test_name","subject","date","start_time","max_marks","min_marks"],
        order_by="date asc") if s_class else []
    marks_map = {}
    if schedules:
        items = frappe.db.sql("""
            SELECT parent, marks_obtained, status
            FROM `tabTest Schedule Item`
            WHERE student_admission_no = %s
        """, s_reg_no, as_dict=True)
        marks_map = {i.parent: i for i in items}
    result = []
    for s in schedules:
        sub_name  = frappe.db.get_value("Subject", s.subject, "subject_name") or s.subject or ""
        test_name = frappe.db.get_value("Inclass Test", s.test_name, "exam_name") or s.test_name or ""
        item = marks_map.get(s.name, {})
        result.append({
            "exam_name":       test_name,
            "subject_name":    sub_name,
            "class_name":      s_class,
            "date":            str(s.date) if s.date else "",
            "start_time":      str(s.start_time) if s.start_time else "",
            "max_marks":       s.max_marks or 0,
            "min_marks":       s.min_marks or 0,
            "marks_obtained":  item.get("marks_obtained","") if item else "",
            "status":          item.get("status","") if item else "",
            "remarks":         "",
        })
    return result


@frappe.whitelist()
def get_exam_results(student=None):
    user = frappe.session.user
    if user in ("Administrator", "Guest"): return []
    if not student:
        student = frappe.db.get_value("Student", {"portal_email": user},
            ["name","full_name","student_reg_no","student_class","section"], as_dict=True)
    else:
        student = frappe.db.get_value("Student", student,
            ["name","full_name","student_reg_no","student_class","section"], as_dict=True)
    if not student: return []
    s_reg_no   = student.student_reg_no or student.name
    s_class    = student.student_class or ""
    full_name  = student.full_name or ""
    rows = frappe.db.sql("""
        SELECT esi.parent as schedule_name, esi.marks_obtained, esi.status,
               es.title, es.subject, es.date, es.max_marks, es.min_marks,
               es.exam_type, es.number_of_students
        FROM `tabExam Schedule Item` esi
        JOIN `tabExam Schedule` es ON es.name = esi.parent
        WHERE esi.student_admission_no = %s
        ORDER BY es.date DESC
    """, s_reg_no, as_dict=True)
    result = []
    for r in rows:
        sub_name = frappe.db.get_value("Subject", r.subject, "subject_name") or r.subject or ""
        result.append({
            "exam_name":      r.title or sub_name,
            "subject_name":   sub_name,
            "class_name":     s_class,
            "date":           str(r.date) if r.date else "",
            "max_marks":      r.max_marks or 0,
            "min_marks":      r.min_marks or 0,
            "exam_type":      r.exam_type or "",
            "total_students": r.number_of_students or 0,
            "scores": [{
                "student_full_name":    full_name,
                "student_admission_no": s_reg_no,
                "marks_obtained":       r.marks_obtained or 0,
                "status":               r.status or "",
            }]
        })
    return result


@frappe.whitelist()
def get_inclass_tests():
    return get_class_test_results()

@frappe.whitelist()
def get_class_test_results(student=None):
    user = frappe.session.user
    if user in ("Administrator", "Guest"): return []
    if not student:
        student = frappe.db.get_value("Student", {"portal_email": user},
            ["name","full_name","student_reg_no","student_class","section"], as_dict=True)
    else:
        student = frappe.db.get_value("Student", student,
            ["name","full_name","student_reg_no","student_class","section"], as_dict=True)
    if not student: return []
    s_reg_no  = student.student_reg_no or student.name
    s_class   = student.student_class or ""
    full_name = student.full_name or ""
    rows = frappe.db.sql("""
        SELECT tsi.parent as schedule_name, tsi.marks_obtained, tsi.status,
               ts.test_name, ts.subject, ts.date, ts.max_marks, ts.min_marks,
               ts.number_of_students
        FROM `tabTest Schedule Item` tsi
        JOIN `tabTest Schedule` ts ON ts.name = tsi.parent
        WHERE tsi.student_admission_no = %s
        ORDER BY ts.date DESC
    """, s_reg_no, as_dict=True)
    result = []
    for r in rows:
        sub_name  = frappe.db.get_value("Subject", r.subject, "subject_name") or r.subject or ""
        test_name = frappe.db.get_value("Inclass Test", r.test_name, "exam_name") or r.test_name or ""
        result.append({
            "exam_name":      test_name,
            "subject_name":   sub_name,
            "class_name":     s_class,
            "date":           str(r.date) if r.date else "",
            "max_marks":      r.max_marks or 0,
            "min_marks":      r.min_marks or 0,
            "exam_type":      "",
            "total_students": r.number_of_students or 0,
            "scores": [{
                "student_full_name":    full_name,
                "student_admission_no": s_reg_no,
                "marks_obtained":       r.marks_obtained or 0,
                "status":               r.status or "",
            }]
        })
    return result


@frappe.whitelist()
def get_homework_results(student=None):
    user = frappe.session.user
    if user in ("Administrator", "Guest"): return []
    if not student:
        student = frappe.db.get_value("Student", {"portal_email": user},
            ["name","full_name","student_reg_no","student_class","section"], as_dict=True)
    else:
        student = frappe.db.get_value("Student", student,
            ["name","full_name","student_reg_no","student_class","section"], as_dict=True)
    if not student: return []
    s_reg_no  = student.student_reg_no or student.name
    s_class   = student.student_class or ""
    full_name = student.full_name or ""
    rows = frappe.db.sql("""
        SELECT hsi.parent as schedule_name, hsi.marks_obtained, hsi.status,
               hs.test_name, hs.subject, hs.date, hs.max_marks, hs.min_marks,
               hs.number_of_students
        FROM `tabHome Schedule Item` hsi
        JOIN `tabHome Schedule` hs ON hs.name = hsi.parent
        WHERE hsi.student_admission_no = %s
        ORDER BY hs.date DESC
    """, s_reg_no, as_dict=True)
    result = []
    for r in rows:
        sub_name  = frappe.db.get_value("Subject", r.subject, "subject_name") or r.subject or ""
        hw_name   = frappe.db.get_value("Homework", r.test_name, "home_name") or r.test_name or ""
        hw_type   = frappe.db.get_value("Homework", r.test_name, "homework_type") or ""
        result.append({
            "homework_name":  hw_name,
            "subject_name":   sub_name,
            "class_name":     s_class,
            "date":           str(r.date) if r.date else "",
            "max_marks":      r.max_marks or 0,
            "min_marks":      r.min_marks or 0,
            "homework_type":  hw_type,
            "total_students": r.number_of_students or 0,
            "scores": [{
                "student_full_name":    full_name,
                "student_admission_no": s_reg_no,
                "marks_obtained":       r.marks_obtained or 0,
                "status":               r.status or "",
            }]
        })
    return result


@frappe.whitelist()
def get_teacher_portal_dashboard():
    """API endpoint for teacher portal dashboard data"""
    user = frappe.session.user
    if user in ("Administrator", "Guest"):
        return {"error": "Not authorized"}

    teacher = frappe.db.get_value("Teacher", {"portal_email": user},
        ["name", "teacher_id", "first_name", "last_name", "full_name",
         "department", "date_of_joining", "email", "phone", "teacher_image"], as_dict=True)

    if not teacher:
        return {"error": "Teacher not found"}

    counts = {
        "classes": frappe.db.count("Student Class"),
        "subjects": frappe.db.count("Subject", {"teacher": teacher.name}) if frappe.db.exists("Subject", {"teacher": teacher.name}) else frappe.db.count("Subject"),
        "students": frappe.db.count("Student"),
        "exam_schedules": frappe.db.count("Exam Schedule"),
        "home_schedules": frappe.db.count("Home Schedule"),
        "test_schedules": frappe.db.count("Test Schedule"),
        "courses": frappe.db.count("Course"),
        "sections": frappe.db.count("Section"),
    }

    recent_exams = frappe.get_all("Exam Schedule",
        fields=["name", "exam_name", "subject", "date", "class_name"],
        order_by="date desc", limit=5)

    recent_homework = frappe.get_all("Home Schedule",
        fields=["name", "subject", "student_class", "date"],
        order_by="date desc", limit=5)

    recent_tests = frappe.get_all("Test Schedule",
        fields=["name", "subject", "student_class", "date"],
        order_by="date desc", limit=5)

    return {
        "teacher": teacher,
        "counts": counts,
        "recent_exams": recent_exams,
        "recent_homework": recent_homework,
        "recent_tests": recent_tests
    }


@frappe.whitelist(allow_guest=True)
def get_user_redirect(user=None):
    """Returns where to redirect the logged in user."""
    if not user:
        user = frappe.session.user
        
    if not user or user == "Guest":
        return {"redirect": "/portal-login"}

    user = user.strip().lower()
    roles = frappe.get_roles(user)

    if "System Manager" in roles or "Administrator" in roles:
        return {"redirect": "/app", "role": "admin"}

    # Check portal_email, employee_email, and just email for Teacher for a robust fallback
    if frappe.db.exists("Teacher", {"portal_email": user}) or frappe.db.exists("Teacher", {"employee_email": user}) or frappe.db.exists("Teacher", {"email": user}):
        return {"redirect": "/assets/school/html/teacher-portal.html", "role": "teacher"}

    if frappe.db.exists("Student", {"portal_email": user}):
        return {"redirect": "/assets/school/html/student-portal.html", "role": "student"}

    if frappe.db.exists("Parent", {"portal_email": user}):
        return {"redirect": "/assets/school/html/parent-portal.html", "role": "parent"}

    if "School User" in roles:
        return {"redirect": "/app", "role": "school_user"}

    return {"redirect": "/portal-login", "role": "guest"}


@frappe.whitelist()
def get_fees_balance():
    user = frappe.session.user
    if not user or user == "Guest":
        return {"error": "Not authorized"}

    cost_center = frappe.form_dict.get("cost_center") or None
    student_filters = {}
    if cost_center:
        student_filters["cost_center"] = cost_center

    students = frappe.get_all("Student",
        filters=student_filters,
        fields=["name", "full_name", "student_class", "section", "cost_center", "school"])

    if not students:
        return []

    student_names = [s.full_name for s in students if s.full_name]
    student_map = {s.full_name: s for s in students}

    if not student_names:
        return []

    placeholders = ", ".join(["%s"] * len(student_names))
    receivables = frappe.db.sql("""
        SELECT
            si.customer,
            si.customer_name,
            si.cost_center,
            si.fees_structure,
            SUM(si.grand_total) as total_billed,
            SUM(si.outstanding_amount) as total_outstanding,
            SUM(si.grand_total - si.outstanding_amount) as total_paid
        FROM `tabSales Invoice` si
        WHERE si.customer IN ({placeholders})
          AND si.docstatus = 1
        GROUP BY si.customer, si.cost_center, si.fees_structure
        ORDER BY si.customer ASC
    """.format(placeholders=placeholders), student_names, as_dict=True)

    opening_balances = frappe.db.sql("""
        SELECT
            jea.party,
            SUM(jea.debit_in_account_currency) as opening_balance
        FROM `tabJournal Entry Account` jea
        JOIN `tabJournal Entry` je ON je.name = jea.parent
        WHERE je.voucher_type = 'Opening Entry'
          AND jea.party_type = 'Customer'
          AND jea.party IN ({placeholders})
          AND je.docstatus = 1
        GROUP BY jea.party
    """.format(placeholders=placeholders), student_names, as_dict=True)

    ob_map = {r.party: r.opening_balance for r in opening_balances}

    result = []
    for row in receivables:
        student = student_map.get(row.customer_name) or student_map.get(row.customer) or {}
        ob = ob_map.get(row.customer, 0)
        result.append({
            "student_name": row.customer_name or row.customer,
            "student_class": student.get("student_class") if isinstance(student, dict) else getattr(student, "student_class", ""),
            "section": student.get("section") if isinstance(student, dict) else getattr(student, "section", ""),
            "cost_center": row.cost_center or (student.get("cost_center") if isinstance(student, dict) else getattr(student, "cost_center", "")),
            "fees_structure": row.fees_structure or "",
            "opening_balance": float(ob or 0),
            "total_billed": float(row.total_billed or 0),
            "total_paid": float(row.total_paid or 0),
            "total_outstanding": float(row.total_outstanding or 0) + float(ob or 0),
        })

    return result


# ─────────────────────────────────────────────────────────────
#  PARENT PORTAL APIs
# ─────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_parent_dashboard():
    user = frappe.session.user
    if user in ("Administrator", "Guest"):
        return {"error": "Not authorized"}

    parent = frappe.db.get_value("Parent", {"portal_email": user},
        ["name", "full_name", "mobile_no", "parent_image", "portal_email"], as_dict=True)

    if not parent:
        return {"error": "Parent record not found"}

    parent_data = {
        "full_name": parent.full_name or "",
        "email":     parent.portal_email or user,
        "mobile_no": parent.mobile_no or "",
        "image":     parent.parent_image or "",
        "initials":  _make_initials(parent.full_name or "", "P"),
    }

    child_links = frappe.get_all("Parent Child",
        filters={"parent": parent.name},
        fields=["student"],
        order_by="idx asc")

    children_data = []
    for row in child_links:
        student_name = row.get("student")
        if not student_name:
            continue

        student = frappe.db.get_value("Student", student_name,
            ["name", "first_name", "last_name", "full_name",
             "student_reg_no", "student_class", "section", "house", "student_image"],
            as_dict=True)

        if not student:
            continue

        class_name = frappe.db.get_value("Student Class", student.student_class, "class_name") \
                     or student.student_class or ""

        children_data.append({
            "name":       student.name,
            "full_name":  student.full_name or f"{student.first_name or ''} {student.last_name or ''}".strip(),
            "reg_no":     student.student_reg_no or "",
            "class_name": class_name,
            "section":    student.section or "",
            "house":      student.house or "",
            "image":      student.student_image or "",
            "initials":   _make_initials(student.full_name or student.first_name or "", "S"),
            "counts":     _get_student_counts(student),
        })

    return {
        "parent":   parent_data,
        "children": children_data,
    }


@frappe.whitelist()
def get_parent_billing_summary():
    user = frappe.session.user
    if user in ("Administrator", "Guest"):
        return {"error": "Not authorized"}

    parent = frappe.db.get_value("Parent", {"portal_email": user}, "name")
    if not parent:
        return {"error": "Parent record not found"}

    child_filter = frappe.form_dict.get("child") or None

    child_links = frappe.get_all("Parent Child",
        filters={"parent": parent},
        fields=["student"],
        order_by="idx asc")

    result = []
    for row in child_links:
        student_name = row.get("student")
        if not student_name:
            continue
        if child_filter and student_name != child_filter:
            continue

        student = frappe.db.get_value("Student", student_name,
            ["name", "full_name"], as_dict=True)
        if not student:
            continue

        invoices = frappe.db.sql("""
            SELECT name, posting_date, due_date, grand_total, outstanding_amount,
                   status, cost_center, fees_structure
            FROM `tabSales Invoice`
            WHERE customer_name = %s
            ORDER BY posting_date DESC
        """, student.full_name, as_dict=True)

        for inv in invoices:
            inv['posting_date'] = str(inv['posting_date'])
            inv['due_date']     = str(inv['due_date'])
            inv['items'] = frappe.get_all("Sales Invoice Item",
                filters={"parent": inv['name']},
                fields=["item_name", "qty", "rate", "amount"])

        receipts = frappe.db.sql("""
            SELECT name, date, total_outstanding, total_allocated, total_balance, account, docstatus
            FROM `tabReceipting`
            WHERE student_name = %s
            ORDER BY date DESC
        """, student.name, as_dict=True)

        for rec in receipts:
            rec['date'] = str(rec['date'])
            rec['items'] = frappe.get_all("Receipt Item",
                filters={"parent": rec['name']},
                fields=["invoice_number", "fees_structure", "outstanding", "allocated"])

        result.append({
            "name":      student.name,
            "full_name": student.full_name,
            "invoices":  invoices,
            "receipts":  receipts,
        })

    return {"children": result}


@frappe.whitelist()
def get_parent_schedules():
    user = frappe.session.user
    if user in ("Administrator", "Guest"):
        return {"error": "Not authorized"}

    parent = frappe.db.get_value("Parent", {"portal_email": user}, "name")
    if not parent:
        return {"error": "Parent record not found"}

    child_filter  = frappe.form_dict.get("child") or None
    schedule_type = frappe.form_dict.get("type") or None

    child_links = frappe.get_all("Parent Child",
        filters={"parent": parent},
        fields=["student"],
        order_by="idx asc")

    result = []
    for row in child_links:
        student_name = row.get("student")
        if not student_name:
            continue
        if child_filter and student_name != child_filter:
            continue

        student = frappe.db.get_value("Student", student_name,
            ["name", "full_name", "student_class", "section", "student_reg_no"], as_dict=True)
        if not student:
            continue

        entry = {
            "name":       student.name,
            "full_name":  student.full_name or "",
            "class_name": frappe.db.get_value("Student Class", student.student_class, "class_name") or student.student_class or "",
            "section":    student.section or "",
        }

        if not schedule_type or schedule_type == "exam":
            entry["exam_schedules"] = frappe.get_all("Exam Schedule Item",
                filters={"student": student.name},
                fields=["exam_name", "subject_name", "class_name", "date", "start_time",
                        "exam_type", "max_marks", "min_marks", "total_questions",
                        "room_number", "number_of_students", "remarks"],
                order_by="date asc")

        if not schedule_type or schedule_type == "home":
            entry["home_schedules"] = frappe.get_all("Home Schedule Item",
                filters={"student": student.name},
                fields=["*"],
                order_by="date asc")

        if not schedule_type or schedule_type == "test":
            entry["test_schedules"] = frappe.get_all("Test Schedule Item",
                filters={"student": student.name},
                fields=["*"],
                order_by="date asc")

        result.append(entry)

    return {"children": result}


@frappe.whitelist()
def get_parent_results():
    user = frappe.session.user
    if user in ("Administrator", "Guest"):
        return {"error": "Not authorized"}

    parent = frappe.db.get_value("Parent", {"portal_email": user}, "name")
    if not parent:
        return {"error": "Parent record not found"}

    child_filter = frappe.form_dict.get("child") or None

    child_links = frappe.get_all("Parent Child",
        filters={"parent": parent},
        fields=["student"],
        order_by="idx asc")

    result = []
    for row in child_links:
        student_name = row.get("student")
        if not student_name:
            continue
        if child_filter and student_name != child_filter:
            continue

        student = frappe.db.get_value("Student", student_name,
            ["name", "full_name"], as_dict=True)
        if not student:
            continue

        entry = {
            "name":      student.name,
            "full_name": student.full_name or "",
            "exam_results": frappe.get_all("Exam Result",
                filters={"student": student.name},
                fields=["*"],
                order_by="creation desc"),
            "inclass_tests": frappe.get_all("Inclass Test",
                filters={"student": student.name},
                fields=["*"],
                order_by="creation desc") if frappe.db.exists("DocType", "Inclass Test") else [],
            "homework_results": frappe.get_all("Home Schedule Item",
                filters={"student": student.name},
                fields=["*"],
                order_by="date desc"),
        }

        result.append(entry)

    return {"children": result}


# ─────────────────────────────────────────────────────────────
#  SHARED HELPERS
# ─────────────────────────────────────────────────────────────

def _get_student_counts(student):
    sname     = student.name if hasattr(student, "name") else student["name"]
    s_class   = (student.student_class  if hasattr(student, "student_class")  else student.get("student_class"))  or ""
    s_section = (student.section        if hasattr(student, "section")        else student.get("section"))        or ""
    s_reg_no  = (student.student_reg_no if hasattr(student, "student_reg_no") else student.get("student_reg_no")) or sname
    full_name = (student.full_name      if hasattr(student, "full_name")      else student.get("full_name"))      or ""

    class_filters   = {"student_class": s_class} if s_class else {}
    section_filters = {"student_class": s_class, "section": s_section} if s_class and s_section else class_filters

    exam_schedules = frappe.db.count("Exam Schedule",  section_filters) if s_class else 0
    home_schedules = frappe.db.count("Home Schedule",  section_filters) if s_class else 0
    test_schedules = frappe.db.count("Test Schedule",  section_filters) if s_class else 0
    exam_results   = frappe.db.count("Exam Schedule Item", {"student_admission_no": s_reg_no}) \
                     if frappe.db.exists("DocType", "Exam Schedule Item") else 0
    inclass_tests  = 0
    homework       = frappe.db.count("Home Schedule Item", {"student_admission_no": s_reg_no}) \
                     if frappe.db.exists("DocType", "Home Schedule Item") else 0

    billing = frappe.db.sql("""
        SELECT SUM(outstanding_amount) as balance
        FROM `tabSales Invoice`
        WHERE customer_name = %s AND docstatus = 1
    """, full_name, as_dict=True)
    balance = float(billing[0].balance) if billing and billing[0].balance else 0.0

    return {
        "exam_schedules": exam_schedules or 0,
        "home_schedules": home_schedules or 0,
        "test_schedules": test_schedules or 0,
        "exam_results":   exam_results   or 0,
        "inclass_tests":  inclass_tests  or 0,
        "homework":       homework       or 0,
        "balance":        balance,
    }


def _make_initials(full_name, fallback="?"):
    parts = (full_name or "").strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    elif parts:
        return parts[0][0].upper()
    return fallback


@frappe.whitelist()
def get_student_sidebar_data(student=None):
    user = frappe.session.user
    if user in ("Administrator", "Guest"):
        return {"error": "Not authorized"}

    if student:
        parent = frappe.db.get_value("Parent", {"portal_email": user}, "name")
        if parent:
            if not frappe.db.exists("Parent Child", {"parent": parent, "student": student}):
                return {"error": "Access denied"}
        student = frappe.db.get_value("Student", student,
            ["name", "full_name", "student_reg_no", "student_class", "section",
             "house", "student_image", "first_name"], as_dict=True)
    else:
        student = frappe.db.get_value("Student", {"portal_email": user},
            ["name", "full_name", "student_reg_no", "student_class", "section",
             "house", "student_image", "first_name"], as_dict=True)

    if not student:
        return {"error": "Student not found"}

    s_class   = student.student_class or ""
    s_section = student.section or ""
    s_reg_no  = student.student_reg_no or student.name
    filters   = {"student_class": s_class, "section": s_section}

    exam_schedules = frappe.get_all("Exam Schedule",
        filters=filters,
        fields=["name","title","subject","date","start_time","room_number","max_marks","exam_type"],
        order_by="date asc") if s_class else []

    home_schedules = frappe.get_all("Home Schedule",
        filters=filters,
        fields=["name","test_name","subject","date","start_time","max_marks","min_marks"],
        order_by="date asc") if s_class else []

    test_schedules = frappe.get_all("Test Schedule",
        filters=filters,
        fields=["name","test_name","subject","date","start_time","max_marks","min_marks"],
        order_by="date asc") if s_class else []

    exam_schedule_results = frappe.db.sql("""
        SELECT esi.parent as schedule_name, esi.marks_obtained, esi.status,
               es.subject, es.date, es.max_marks, es.exam_type
        FROM `tabExam Schedule Item` esi
        JOIN `tabExam Schedule` es ON es.name = esi.parent
        WHERE esi.student_admission_no = %s
        ORDER BY es.date DESC
    """, s_reg_no, as_dict=True)

    home_results = frappe.db.sql("""
        SELECT hsi.parent as schedule_name, hsi.marks_obtained, hsi.status,
               hs.subject, hs.date, hs.max_marks
        FROM `tabHome Schedule Item` hsi
        JOIN `tabHome Schedule` hs ON hs.name = hsi.parent
        WHERE hsi.student_admission_no = %s
        ORDER BY hs.date DESC
    """, s_reg_no, as_dict=True)

    test_results = frappe.db.sql("""
        SELECT tsi.parent as schedule_name, tsi.marks_obtained, tsi.status,
               ts.subject, ts.date, ts.max_marks
        FROM `tabTest Schedule Item` tsi
        JOIN `tabTest Schedule` ts ON ts.name = tsi.parent
        WHERE tsi.student_admission_no = %s
        ORDER BY ts.date DESC
    """, s_reg_no, as_dict=True)

    exam_results_raw = frappe.db.sql("""
        SELECT er.name, er.source_doc, er.student_class, er.subject, er.date,
               tsi.marks_obtained, tsi.status
        FROM `tabExam Result` er
        JOIN `tabTest Schedule Item` tsi ON tsi.parent = er.name
        WHERE tsi.student_admission_no = %s
        ORDER BY er.date DESC
    """, s_reg_no, as_dict=True)

    for row in list(exam_schedules)+list(home_schedules)+list(test_schedules)+\
               list(exam_schedule_results)+list(home_results)+list(test_results)+list(exam_results_raw):
        if row.get("date"): row["date"] = str(row["date"])
        if row.get("start_time"): row["start_time"] = str(row["start_time"])

    class_name = frappe.db.get_value("Student Class", s_class, "class_name") or s_class

    return {
        "student": {
            "name":       student.name,
            "full_name":  student.full_name or "",
            "reg_no":     s_reg_no,
            "class_name": class_name,
            "section":    s_section,
            "house":      student.house or "",
            "image":      student.student_image or "",
            "initials":   (student.first_name or "S")[0].upper(),
        },
        "schedules": {
            "exam": exam_schedules,
            "home": home_schedules,
            "test": test_schedules,
        },
        "results": {
            "exam_schedule": exam_schedule_results,
            "exam_result":   exam_results_raw,
            "home":          home_results,
            "test":          test_results,
        },
        "counts": {
            "exam_schedules": len(exam_schedules),
            "home_schedules": len(home_schedules),
            "test_schedules": len(test_schedules),
            "exam_results":   len(exam_schedule_results) + len(exam_results_raw),
            "home_results":   len(home_results),
            "test_results":   len(test_results),
        }
    }


# ─────────────────────────────────────────────────────────────
#  LOGIN PAGE APIs
#  allow_guest=True  → works for ALL visitors before login
#
#  HOW IT WORKS:
#  1. Go to Login Slide Image doctype on your LIVE site
#  2. Create a record, set slide_title, upload image, set enabled=1
#  3. The image is saved to the live server's /files/ folder
#  4. This API reads it from the live DB and returns relative URLs
#  5. The login page shows it to EVERY visitor on ANY device
#
#  No syncing, no scp, no console needed. Just add via the UI on live.
# ─────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def get_login_slides():
    """
    Reads Login Slide Image records from the database.
    Add slides via Frappe UI → they automatically show on login page
    for ALL devices and ALL visitors without any extra steps.
    """
    try:
        slides = frappe.get_all(
            "Login Slide Image",
            filters={"enabled": 1},
            fields=["name", "slide_title", "slide_image", "media_type", "sort_order"],
            order_by="sort_order asc, creation asc"
        )
        result = []
        site_url = frappe.utils.get_url()
        
        for s in slides:
            if not s.slide_image:
                continue
            
            # Use direct file path
            filename = s.slide_image.split('/')[-1]
            url = f"{site_url}/files/{filename}"
            
            result.append({
                "url": url,
                "media_type": s.media_type or "Image",
                "title": s.slide_title or "",
            })
        return result
    except Exception:
        frappe.log_error(title="get_login_slides error", message=frappe.get_traceback())
        return []
@frappe.whitelist(allow_guest=True)
def get_portal_header():
    """
    Returns portal header text from Login Portal Header doctype.
    Edit via Frappe UI → instantly updates for all visitors.
    """
    try:
        if frappe.db.count("Login Portal Header") > 0:
            doc = frappe.get_last_doc("Login Portal Header")
            header = (doc.header_text or "").strip()
            return header if header else "School Portal"
    except Exception:
        frappe.log_error(title="get_portal_header error", message=frappe.get_traceback())
    return "School Portal"


