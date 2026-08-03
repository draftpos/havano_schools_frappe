import frappe

def check():
    students = frappe.db.sql('SELECT name, first_name, last_name, full_name, student_reg_no FROM tabStudent LIMIT 10', as_dict=True)
    print("----- STUDENT DATA -----")
    for s in students:
        print(s)
    print("------------------------")
