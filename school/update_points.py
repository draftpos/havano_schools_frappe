import frappe
from school.school_management.doctype.term_exam_report.term_exam_report import is_alevel

def run():
	grade_points = {}
	settings = frappe.get_doc('School Settings')
	for row in settings.get('a_level_grade_points', []):
		if row.grade:
			grade_points[str(row.grade).upper().strip()] = row.points

	reports = frappe.get_all('Term Exam Report', fields=['name', 'student_class'])
	updated = 0
	for report in reports:
		if is_alevel(report.student_class):
			items = frappe.get_all('Term Exam Result Item', filters={'parent': report.name}, fields=['name', 'grade', 'points'])
			for item in items:
				if item.grade:
					g_str = str(item.grade).upper().strip()
					pts = grade_points.get(g_str, 0.0)
					if item.points != pts:
						frappe.db.set_value('Term Exam Result Item', item.name, 'points', pts)
						updated += 1

	frappe.db.commit()
	print(f'Updated {updated} records.')
