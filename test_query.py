import frappe

def execute():
    teachers = frappe.db.get_all('Teacher', fields=['name', 'portal_email'])
    print('Teachers Data Debug:')
    for t in teachers:
        print(f"Name: {t.get('name')}, Portal Email: {t.get('portal_email')}")
