import json
import os

file_path = '/home/ashley/frappe-bench-v15/apps/school/school/school_management/doctype/student/student.json'

with open(file_path, 'r') as f:
    data = json.load(f)

# Update student_class reqd
for field in data['fields']:
    if field.get('fieldname') == 'student_class':
        field['reqd'] = 0
        break

# Add status field
status_field = {
    "default": "Active",
    "fieldname": "status",
    "fieldtype": "Select",
    "label": "Status",
    "options": "Active\nInactive"
}

# Find index of student_type in fields to insert after
insert_idx = -1
for i, field in enumerate(data['fields']):
    if field.get('fieldname') == 'student_type':
        insert_idx = i + 1
        break

if insert_idx != -1:
    # Check if already exists
    if not any(f.get('fieldname') == 'status' for f in data['fields']):
        data['fields'].insert(insert_idx, status_field)

# Update field_order
if 'status' not in data['field_order']:
    fo_idx = -1
    if 'student_type' in data['field_order']:
        fo_idx = data['field_order'].index('student_type') + 1
    
    if fo_idx != -1:
        data['field_order'].insert(fo_idx, 'status')
    else:
        data['field_order'].append('status')

with open(file_path, 'w') as f:
    json.dump(data, f, indent=1)

print("Successfully updated student.json")
