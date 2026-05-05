import frappe
from school.api import get_teacher_students_list

def run():
    print("--- Testing get_teacher_students_list ---")
    
    # We need a user session
    # Let's find a teacher user
    teacher_user = frappe.db.get_value("Teacher", {"name": "TCH-001"}, "portal_email")
    if not teacher_user:
        print("Teacher TCH-001 not found, trying first teacher...")
        teacher_user = frappe.db.get_value("Teacher", {}, "portal_email")
    
    if not teacher_user:
        print("No teachers found.")
        return

    print(f"Testing as user: {teacher_user}")
    frappe.set_user(teacher_user)
    
    students = get_teacher_students_list()
    print(f"Total students found: {len(students)}")
    for s in students[:5]:
        print(f"Student: {s['full_name']}, School: {s.get('school')}")

    # Now let's try to simulate a cost center assignment
    print("\n--- Simulating Cost Center Filter ---")
    # I'll manually set a cost center on the assignment record for this teacher
    teacher_name = frappe.db.get_value("Teacher", {"portal_email": teacher_user}, "name")
    
    # Find an assignment
    assignment = frappe.db.get_value("Teacher Class Assignment Item", {"parent": teacher_name}, ["name", "class_name", "section"], as_dict=True)
    if assignment:
        print(f"Found assignment: {assignment}")
        # Let's see what happens if we set a non-existent cost center
        # We can't easily mock frappe.db.sql but we can see if it filters
        pass
    else:
        print("No assignments found for this teacher.")

if __name__ == "__main__":
    run()
