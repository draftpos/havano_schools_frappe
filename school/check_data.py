import frappe

def check_data():
    settings = frappe.get_doc("School Settings")
    print("O Level Comments count:", len(settings.get("o_level_admin_comments", [])))
    print("A Level Comments count:", len(settings.get("a_level_admin_comments", [])))
    print("O Level table data:")
    for row in settings.get("o_level_admin_comments", []):
        print(" - ", row.comment_type, " : ", row.comment)

if __name__ == "__main__":
    frappe.init(site="v15.local")
    frappe.connect()
    check_data()
