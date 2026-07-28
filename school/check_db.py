import frappe

def check_db():
    rows = frappe.db.get_all("Admin Comment O Level", fields=["name", "parent", "parenttype", "parentfield", "comment_type", "comment"])
    for row in rows:
        print(row)

if __name__ == "__main__":
    frappe.init(site="v15.local")
    frappe.connect()
    check_db()
