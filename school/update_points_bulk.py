import frappe

def run():
	grade_points = {}
	settings = frappe.get_doc('School Settings')
	for row in settings.get('a_level_grade_points', []):
		if row.grade:
			grade_points[str(row.grade).upper().strip()] = row.points

	reports = frappe.get_all('Term Exam Report', fields=['name', 'student_class'])
	updated = 0
	
	# Helper to check if class is A-Level (copied from term_exam_report.py to be safe)
	def is_alevel(class_name):
		if not class_name:
			return False
		cn = class_name.lower()
		return any(k in cn for k in ['a level', 'form 5', 'form 6', 'lower 6', 'upper 6', 'l6', 'u6'])

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
	print(f'\n======================================================')
	print(f'✅ Successfully updated {updated} existing result records!')
	print(f'======================================================\n')
