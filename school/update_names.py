import frappe

def update_existing_student_names():
    # Update Term Exam Result Item
    print("Updating Term Exam Result Item...")
    frappe.db.sql("""
        UPDATE `tabTerm Exam Result Item` t
        JOIN `tabStudent` s ON t.student = s.name
        SET t.student_name = s.full_name
        WHERE (t.student_name IS NULL OR t.student_name = '' OR t.student_name = t.student)
    """)
    
    # Also update Exam Schedule Item if needed
    print("Updating Exam Schedule Item...")
    frappe.db.sql("""
        UPDATE `tabExam Schedule Item` t
        JOIN `tabStudent` s ON t.student_admission_no = s.name
        SET t.student_full_name = s.full_name
        WHERE (t.student_full_name IS NULL OR t.student_full_name = '' OR t.student_full_name = t.student_admission_no)
    """)
    
    frappe.db.commit()
    print("Update complete!")

if __name__ == '__main__':
    update_existing_student_names()
