import json
import datetime

file_path = '/home/ashley/frappe-bench-v15/apps/school/school/fixtures/custom_docperm.json'
with open(file_path, 'r') as f:
    perms = json.load(f)

t = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
for p in perms:
    if p.get('role') == 'School User':
        p['modified'] = t

with open(file_path, 'w') as f:
    json.dump(perms, f, indent=1)
print('Updated timestamps')
