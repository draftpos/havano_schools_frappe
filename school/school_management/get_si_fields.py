import frappe
import json

def get_si_fields():
    meta = frappe.get_meta("Sales Invoice")
    fields = [f.fieldname for f in meta.fields]
    with open('/tmp/si_fields.json', 'w') as f:
        json.dump(fields, f)
