import frappe
from school.api import get_billing_summary
frappe.init(site='erp1422.havano.cloud')
frappe.connect()
frappe.session.user = 'Administrator'
try:
    print(get_billing_summary('RIVERSIDECD00012'))
except Exception as e:
    import traceback
    traceback.print_exc()
