import json

file_path = '/home/ashley/frappe-bench-v15/apps/school/school/fixtures/custom_docperm.json'
with open(file_path, 'r') as f:
    perms = json.load(f)

for p in perms:
    if p.get('role') == 'School User':
        p['read'] = 1
        p['write'] = 1
        p['create'] = 1
        p['delete'] = 1
        p['print'] = 1
        p['email'] = 1
        p['report'] = 1
        p['share'] = 1
        
        submittables = ['Billing', 'Receipting', 'Sales Invoice', 'Payment Entry', 'Journal Entry', 'Purchase Invoice', 'Sales Order', 'Promote', 'Staff Attendance']
        if p.get('parent') in submittables:
            p['submit'] = 1
            p['cancel'] = 1
            p['amend'] = 1

with open(file_path, 'w') as f:
    json.dump(perms, f, indent=1)
print('Updated custom_docperm.json')
