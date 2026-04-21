import frappe

def delete_bad_scripts():
    scripts_to_delete = ["Create Student Portal User", "Send Student Portal Credentials", "online_registration"]
    for name in scripts_to_delete:
        if frappe.db.exists("Server Script", name):
            frappe.delete_doc("Server Script", name)
            print(f"Deleted {name}")
    frappe.db.commit()

if __name__ == "__main__":
    delete_bad_scripts()
