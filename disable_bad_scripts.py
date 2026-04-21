import frappe

def disable_scripts():
    scripts = frappe.get_all("Server Script", filters={"name": ["like", "%online_registration%"]})
    for s in scripts:
        frappe.db.set_value("Server Script", s.name, "disabled", 1)
        print(f"Disabled {s.name}")
    frappe.db.commit()

if __name__ == "__main__":
    disable_scripts()
