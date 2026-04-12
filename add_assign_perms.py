import json
import datetime
import uuid

file_path = '/home/ashley/frappe-bench-v15/apps/school/school/fixtures/custom_docperm.json'
with open(file_path, 'r') as f:
    perms = json.load(f)

t = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def add_perm(parent):
    for p in perms:
        if p.get('parent') == parent and p.get('role') == 'School User':
            p['modified'] = t
            p['read'] = 1
            p['write'] = 1
            p['create'] = 1
            p['delete'] = 1
            p['print'] = 1
            p['email'] = 1
            p['report'] = 1
            p['share'] = 1
            p['submit'] = 1
            p['cancel'] = 1
            p['amend'] = 1
            return
            
    perms.append({
        "doctype": "Custom DocPerm",
        "name": str(uuid.uuid4())[:10],
        "parent": parent,
        "role": "School User",
        "permlevel": 0,
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 1,
        "print": 1,
        "email": 1,
        "report": 1,
        "share": 1,
        "submit": 1,
        "cancel": 1,
        "amend": 1,
        "if_owner": 0,
        "export": 1,
        "modified": t,
        "docstatus": 0
    })

add_perm("Assign Class to Teacher")
add_perm("Assign Subjects to Teacher")

with open(file_path, 'w') as f:
    json.dump(perms, f, indent=1)
print('Added/updated permissions')
