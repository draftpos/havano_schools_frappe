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
    
    frappe.db.commit()
    print("Update complete!")

if __name__ == '__main__':
    update_existing_student_names()
