import frappe

def execute():
    # 1. Add fetch_from property
    print("Setting fetch_from property...")
    if frappe.db.exists("Custom Field", "Sales Invoice-student_class"):
        frappe.db.set_value("Custom Field", "Sales Invoice-student_class", "fetch_from", "billing_reference.student_class")
        frappe.clear_cache(doctype="Sales Invoice")
        print("Fetch from rule applied.")
    else:
        print("Custom Field 'Sales Invoice-student_class' does not exist in this site database.")

    # 2. Fix Sales Invoices
    print("Fixing Sales Invoices...")
    try:
        billing_dt = frappe.get_meta("Sales Invoice").get_field("billing_reference").options
        if billing_dt:
            invoices = frappe.get_all("Sales Invoice", filters={"billing_reference": ["is", "set"]}, fields=["name", "billing_reference"])
            
            fixed_inv = 0
            for inv in invoices:
                correct_class = frappe.db.get_value(billing_dt, inv.billing_reference, "student_class")
                current_class = frappe.db.get_value("Sales Invoice", inv.name, "student_class")
                if correct_class and current_class != correct_class:
                    frappe.db.set_value("Sales Invoice", inv.name, "student_class", correct_class)
                    fixed_inv += 1
                    
            print(f"Fixed {fixed_inv} Sales Invoices.")
    except Exception as e:
        print(f"Could not fix Sales Invoices: {e}")

    # 3. Fix Student Master
    print("Fixing Student Master...")
    try:
        invoices = frappe.get_all("Sales Invoice", 
            filters={"posting_date": [">", "2026-01-01"], "billing_reference": ["is", "set"]}, 
            fields=["customer", "student_class"]
        )
        
        updated_count = 0
        for inv in invoices:
            if inv.customer and inv.student_class:
                current_master_class = frappe.db.get_value("Student", inv.customer, "student_class")
                if current_master_class != inv.student_class:
                    frappe.db.set_value("Student", inv.customer, "student_class", inv.student_class)
                    updated_count += 1
                
        print(f"Updated {updated_count} Student master records.")
    except Exception as e:
        print(f"Could not fix Student Master: {e}")
        
    frappe.db.commit()
    print("Transaction committed successfully.")
