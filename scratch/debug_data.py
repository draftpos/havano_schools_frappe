import frappe

def run():
    frappe.connect()
    print("--- Students ---")
    students = frappe.db.get_all("Student", fields=["name", "school", "cost_center"], limit=5)
    for s in students:
        print(s)
    
    print("\n--- Teachers ---")
    teachers = frappe.db.get_all("Teacher", fields=["name", "cost_center", "portal_email"], limit=5)
    for t in teachers:
        print(t)
    
    frappe.destroy()

if __name__ == "__main__":
    import os
    import sys
    
    # Add frappe-bench/apps/frappe to sys.path if needed
    # Assuming we run with 'bench execute' or similar
    run()
