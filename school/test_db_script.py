import frappe

def run():
    settings = frappe.get_doc('School Settings')
    print('A Level Comments:')
    rows = getattr(settings, 'a_level_admin_comments', [])
    if not rows:
        print('NONE!')
    for r in rows:
        print(f'{r.comment_type} -> {r.comment}')
