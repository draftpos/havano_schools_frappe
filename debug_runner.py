import frappe
import sys

def run():
    frappe.init(site="v15.local")
    frappe.connect()
    print("--- Testing API Methods ---")
    
    # We need to import the api module manually if needed, or it's already in path
    try:
        from school.api import get_teacher_students_list, get_teacher_classes_list, get_teacher_subjects_list, get_teacher_sections_list
    except Exception as e:
        print(f"Error importing API: {e}")
        return

    # Let's find a teacher user
    teacher_user = frappe.db.get_value("Teacher", {"user": ["is", "set"]}, "user")
    if not teacher_user:
        teacher_user = frappe.db.get_value("Teacher", {"portal_email": ["is", "set"]}, "portal_email")
    if not teacher_user:
        teacher_user = frappe.db.get_value("User", {"name": ["like", "%teacher%"]}, "name")
        
    if not teacher_user:
        print("Could not find a teacher user to test with.")
        return
        
    print(f"Testing with user: {teacher_user}")
    frappe.set_user(teacher_user)
    
    teacher = frappe.db.get_value("Teacher", {"portal_email": teacher_user}, ["name", "cost_center"], as_dict=True)
    if not teacher:
        teacher = frappe.db.get_value("Teacher", {"employee_user_id": teacher_user}, ["name", "cost_center"], as_dict=True)
        
    if teacher:
        print(f"Teacher Document: {teacher.name}, Cost Center: {teacher.cost_center}")
    else:
        print("Teacher document not found for user.")
        return

    try:
        students = get_teacher_students_list()
        print(f"\n--- Students (Total: {len(students)}) ---")
        for s in students[:5]:
            print(f"{s.get('name')} - School/Cost Center: {s.get('school')} / {s.get('cost_center')}")
        if len(students) > 5:
            print("...")
    except Exception as e:
        print(f"Error fetching students: {e}")

    try:
        classes = get_teacher_classes_list()
        print(f"\n--- Classes (Total: {len(classes)}) ---")
        for c in classes[:5]:
            print(f"{c.get('name')} - Cost Center: {c.get('cost_center', 'N/A')}")
        if len(classes) > 5:
            print("...")
    except Exception as e:
        print(f"Error fetching classes: {e}")
        
    try:
        subjects = get_teacher_subjects_list()
        print(f"\n--- Subjects (Total: {len(subjects)}) ---")
        for sub in subjects[:5]:
            print(f"{sub.get('name')} - Cost Center: {sub.get('cost_center', 'N/A')}")
        if len(subjects) > 5:
            print("...")
    except Exception as e:
        print(f"Error fetching subjects: {e}")

    try:
        sections = get_teacher_sections_list()
        print(f"\n--- Sections (Total: {len(sections)}) ---")
        for sec in sections[:5]:
            print(f"{sec.get('name')} - Cost Center: {sec.get('cost_center', 'N/A')}")
        if len(sections) > 5:
            print("...")
    except Exception as e:
        print(f"Error fetching sections: {e}")
        
if __name__ == "__main__":
    run()
