import jinja2

env = jinja2.Environment()
try:
    with open('/home/ashley/frappe-bench-v15/apps/school/school/school_management/print_format/term_exam_report_premium/term_exam_report_premium.html', 'r') as f:
        env.parse(f.read())
    print("Syntax OK")
except Exception as e:
    print("Syntax Error:", e)
