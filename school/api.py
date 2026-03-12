import frappe

@frappe.whitelist()
def get_exam_results():
    user = frappe.session.user

    # Get student record for logged in user
    student = frappe.db.get_value("Student",
        {"portal_email": user},
        ["name", "student_class", "section", "full_name"], as_dict=True)

    if not student:
        return []

    # Filter exam results by student class
    results = frappe.db.sql("""
        SELECT name, source_doc, student_class, subject, date, total_students
        FROM `tabExam Result`
        WHERE student_class = %s
        ORDER BY date DESC
    """, student.student_class, as_dict=True)

    output = []
    for r in results:
        es = frappe.db.sql("""
            SELECT exam, exam_type, max_marks, min_marks
            FROM `tabExam Schedule`
            WHERE name = %s
        """, r.source_doc, as_dict=True)
        es = es[0] if es else {}

        exam_name = frappe.db.get_value("Exam", es.get("exam"), "exam_name") or r.source_doc
        subject_name = frappe.db.get_value("Subject", r.subject, "subject_name") or r.subject
        class_name = frappe.db.get_value("Student Class", r.student_class, "class_name") or r.student_class

        # Get only this student's score using their admission number (name field)
        scores = frappe.db.sql("""
            SELECT student_admission_no, student_full_name, marks_obtained, status
            FROM `tabTest Schedule Item`
            WHERE parent = %s
            AND student_admission_no = %s
            ORDER BY idx ASC
        """, (r.name, student.name), as_dict=True)

        # Only include this result if student has a score entry
        if scores:
            output.append({
                "name": r.name,
                "exam_name": exam_name,
                "subject_name": subject_name,
                "class_name": class_name,
                "date": str(r.date),
                "total_students": r.total_students,
                "exam_type": es.get("exam_type", "-"),
                "max_marks": es.get("max_marks", 100),
                "scores": scores
            })

    return output


@frappe.whitelist()
def get_class_test_results():
    user = frappe.session.user
    if user == "Administrator" or user == "Guest":
        return {"error": "Please log in as a student"}

    # Get student record for logged in user
    student = frappe.db.get_value("Student",
        {"portal_email": user},
        ["name", "student_class", "section", "full_name"], as_dict=True)

    if not student:
        return {"error": "No student record found for " + user}

    # Filter class results by student class
    results = frappe.db.sql("""
        SELECT name, source_doc, student_class, subject, date, total_students
        FROM `tabClass Result`
        WHERE student_class = %s
        ORDER BY date DESC
    """, student.student_class, as_dict=True)

    output = []
    for r in results:
        ts = frappe.db.sql("""
            SELECT test_name, test_type, max_marks, min_marks
            FROM `tabTest Schedule`
            WHERE name = %s
        """, r.source_doc, as_dict=True)
        ts = ts[0] if ts else {}

        test_display_name = frappe.db.get_value("Inclass Test", ts.get("test_name"), "exam_name") or r.source_doc
        subject_name = frappe.db.get_value("Subject", r.subject, "subject_name") or r.subject
        class_name = frappe.db.get_value("Student Class", r.student_class, "class_name") or r.student_class

        # Only get this student's score
        scores = frappe.db.sql("""
            SELECT student_admission_no, student_full_name, marks_obtained, status
            FROM `tabTest Schedule Item`
            WHERE parent = %s
            AND student_admission_no = %s
            ORDER BY idx ASC
        """, (r.name, student.name), as_dict=True)

        if scores:
            output.append({
                "name": r.name,
                "exam_name": test_display_name,
                "subject_name": subject_name,
                "class_name": class_name,
                "date": str(r.date),
                "total_students": r.total_students,
                "exam_type": ts.get("test_type", "-"),
                "max_marks": ts.get("max_marks", 100),
                "scores": scores
            })

    return output

@frappe.whitelist()
def get_homework_results():
    user = frappe.session.user
    if user == "Administrator" or user == "Guest":
        return []

    student = frappe.db.get_value("Student",
        {"portal_email": user},
        ["name", "student_class", "section", "full_name"], as_dict=True)

    if not student:
        return []

    schedules = frappe.db.sql("""
        SELECT name, test_name, test_type, student_class, subject, date,
               max_marks, number_of_students
        FROM `tabHome Schedule`
        WHERE student_class = %s
        ORDER BY date DESC
    """, student.student_class, as_dict=True)

    output = []
    for r in schedules:
        homework_name = frappe.db.get_value("Homework", r.test_name, "home_name") or r.test_name
        homework_type = frappe.db.get_value("Homework Type", r.test_type, "homework_type_name") or r.test_type
        subject_name = frappe.db.get_value("Subject", r.subject, "subject_name") or r.subject
        class_name = frappe.db.get_value("Student Class", r.student_class, "class_name") or r.student_class

        scores = frappe.db.sql("""
            SELECT student_admission_no, student_full_name, marks_obtained, status
            FROM `tabHome Schedule Item`
            WHERE parent = %s
            AND student_admission_no = %s
        """, (r.name, student.name), as_dict=True)

        if scores:
            output.append({
                "name": r.name,
                "homework_name": homework_name,
                "homework_type": homework_type,
                "subject_name": subject_name,
                "class_name": class_name,
                "date": str(r.date),
                "total_students": r.number_of_students,
                "max_marks": r.max_marks or 100,
                "scores": scores
            })

    return output

@frappe.whitelist()
def get_billing_summary():
    user = frappe.session.user
    if user == "Administrator" or user == "Guest":
        return []

    student = frappe.db.get_value("Student",
        {"portal_email": user},
        ["name", "full_name", "student_class"], as_dict=True)

    if not student:
        return []

    # Get invoices by student full_name as customer
    invoices = frappe.db.sql("""
        SELECT name, posting_date, due_date, grand_total,
               outstanding_amount, status
        FROM `tabSales Invoice`
        WHERE customer = %s
        ORDER BY posting_date DESC
    """, student.full_name, as_dict=True)

    for inv in invoices:
        inv['posting_date'] = str(inv['posting_date'])
        inv['due_date'] = str(inv['due_date'])
        # Get invoice items
        items = frappe.db.sql("""
            SELECT item_name, qty, rate, amount
            FROM `tabSales Invoice Item`
            WHERE parent = %s
        """, inv['name'], as_dict=True)
        inv['items'] = items

    # Get receipts by student name
    receipts = frappe.db.sql("""
        SELECT r.name, r.date, r.total_allocated,
               r.total_outstanding, r.payment_method, r.docstatus
        FROM `tabReceipting` r
        WHERE r.student_name = %s
        ORDER BY r.date DESC
    """, student.name, as_dict=True)

    for rec in receipts:
        rec['date'] = str(rec['date'])
        items = frappe.db.sql("""
            SELECT invoice_number, fees_structure, total, allocated
            FROM `tabReceipt Item`
            WHERE parent = %s
        """, rec['name'], as_dict=True)
        rec['items'] = items

    return {
        "student": student,
        "invoices": invoices,
        "receipts": receipts
    }


@frappe.whitelist()
def get_home_schedules():
    user = frappe.session.user
    if user in ("Administrator", "Guest"):
        return []
    student = frappe.db.get_value("Student", {"portal_email": user},
        ["name", "student_class", "section", "full_name"], as_dict=True)
    if not student:
        return []
    schedules = frappe.db.sql("""
        SELECT name, test_name, test_type, student_class, subject,
               date, start_time, max_marks, min_marks, total_questions,
               number_of_students, room_number, remarks
        FROM `tabHome Schedule`
        WHERE student_class = %s
        ORDER BY date DESC
    """, student.student_class, as_dict=True)
    output = []
    for s in schedules:
        s["date"] = str(s["date"])
        s["start_time"] = str(s["start_time"]) if s["start_time"] else "-"
        s["homework_name"] = frappe.db.get_value("Homework", s["test_name"], "home_name") or s["test_name"]
        s["homework_type"] = frappe.db.get_value("Homework Type", s["test_type"], "homework_type_name") or s["test_type"]
        s["subject_name"] = frappe.db.get_value("Subject", s["subject"], "subject_name") or s["subject"]
        s["class_name"] = frappe.db.get_value("Student Class", s["student_class"], "class_name") or s["student_class"]
        output.append(s)
    return output


@frappe.whitelist()
def get_test_schedules():
    user = frappe.session.user
    if user in ("Administrator", "Guest"):
        return []
    student = frappe.db.get_value("Student", {"portal_email": user},
        ["name", "student_class", "section", "full_name"], as_dict=True)
    if not student:
        return []
    schedules = frappe.db.sql("""
        SELECT name, test_name, test_type, student_class, subject,
               date, start_time, max_marks, min_marks, total_questions,
               number_of_students, room_number, remarks
        FROM `tabTest Schedule`
        WHERE student_class = %s
        ORDER BY date DESC
    """, student.student_class, as_dict=True)
    output = []
    for s in schedules:
        s["date"] = str(s["date"])
        s["start_time"] = str(s["start_time"]) if s["start_time"] else "-"
        s["test_display_name"] = frappe.db.get_value("Inclass Test", s["test_name"], "exam_name") or s["test_name"]
        s["subject_name"] = frappe.db.get_value("Subject", s["subject"], "subject_name") or s["subject"]
        s["class_name"] = frappe.db.get_value("Student Class", s["student_class"], "class_name") or s["student_class"]
        output.append(s)
    return output


@frappe.whitelist()
def get_exam_schedules():
    user = frappe.session.user
    if user in ("Administrator", "Guest"):
        return []
    student = frappe.db.get_value("Student", {"portal_email": user},
        ["name", "student_class", "section", "full_name"], as_dict=True)
    if not student:
        return []
    schedules = frappe.db.sql("""
        SELECT name, exam, exam_type, student_class, subject,
               date, start_time, max_marks, min_marks, total_questions,
               number_of_students, room_number, remarks, title
        FROM `tabExam Schedule`
        WHERE student_class = %s
        ORDER BY date DESC
    """, student.student_class, as_dict=True)
    output = []
    for s in schedules:
        s["date"] = str(s["date"])
        s["start_time"] = str(s["start_time"]) if s["start_time"] else "-"
        s["exam_name"] = frappe.db.get_value("Exam", s["exam"], "exam_name") or s["exam"]
        s["subject_name"] = frappe.db.get_value("Subject", s["subject"], "subject_name") or s["subject"]
        s["class_name"] = frappe.db.get_value("Student Class", s["student_class"], "class_name") or s["student_class"]
        output.append(s)
    return output


@frappe.whitelist()
def get_my_account():
    user = frappe.session.user
    if user in ("Administrator", "Guest"):
        return []

    student = frappe.db.get_value("Student",
        {"portal_email": user},
        ["name", "first_name", "second_name", "last_name", "full_name",
         "student_reg_no", "student_class", "section", "house",
         "date_of_admission", "portal_email"], as_dict=True)

    if not student:
        return []

    student["class_name"] = frappe.db.get_value("Student Class", student.student_class, "class_name") or student.student_class
    student["section_name"] = student.section or "-"
    student["date_of_admission"] = str(student.date_of_admission) if student.date_of_admission else "-"

    return student

@frappe.whitelist()
def get_student_invoices(student):
    student_doc = frappe.get_doc("Student", student)
    full_name = student_doc.full_name

    customer = frappe.db.get_value("Customer", {"customer_name": full_name}, "name")
    if not customer:
        result = frappe.db.sql(
            "SELECT name FROM `tabCustomer` WHERE LOWER(customer_name) = LOWER(%s) LIMIT 1",
            full_name, as_dict=True
        )
        customer = result[0].name if result else None

    if not customer:
        return []

    invoices = frappe.db.sql("""
        SELECT si.name, si.grand_total, si.outstanding_amount,
               COALESCE(fs.structure_name, si.fees_structure, si.remarks, '') as fees_structure
        FROM `tabSales Invoice` si
        LEFT JOIN `tabFees Structure` fs ON fs.name = si.fees_structure
        WHERE si.customer = %s
        AND si.docstatus = 1
        AND si.outstanding_amount > 0
        AND si.status NOT IN ('Paid', 'Return', 'Credit Note Issued')
        ORDER BY si.posting_date DESC
    """, customer, as_dict=True)

    return invoices
