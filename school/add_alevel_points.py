import frappe

def run():
	# Create A Level Grade Point DocType
	if not frappe.db.exists("DocType", "A Level Grade Point"):
		doc = frappe.get_doc({
			"doctype": "DocType",
			"name": "A Level Grade Point",
			"module": "School Management",
			"custom": 0,
			"istable": 1,
			"editable_grid": 1,
			"fields": [
				{
					"fieldname": "grade",
					"fieldtype": "Data",
					"in_list_view": 1,
					"label": "Grade",
					"reqd": 1
				},
				{
					"fieldname": "points",
					"fieldtype": "Float",
					"in_list_view": 1,
					"label": "Points",
					"reqd": 1
				}
			]
		})
		doc.insert(ignore_permissions=True)
		print("Created A Level Grade Point DocType")

	# Add field to School Settings
	school_settings = frappe.get_doc("DocType", "School Settings")
	fields = school_settings.fields
	
	if not any(f.fieldname == "a_level_settings_section" for f in fields):
		school_settings.append("fields", {
			"fieldname": "a_level_settings_section",
			"fieldtype": "Section Break",
			"label": "A-Level Grading Points"
		})
	
	if not any(f.fieldname == "a_level_grade_points" for f in fields):
		school_settings.append("fields", {
			"fieldname": "a_level_grade_points",
			"fieldtype": "Table",
			"label": "A-Level Grade Points Mapping",
			"options": "A Level Grade Point"
		})
		school_settings.save(ignore_permissions=True)
		print("Updated School Settings DocType")

	# Add points field to Term Exam Result Item
	result_item = frappe.get_doc("DocType", "Term Exam Result Item")
	if not any(f.fieldname == "points" for f in result_item.fields):
		# Insert points before grade
		idx_grade = next((i for i, f in enumerate(result_item.fields) if f.fieldname == "grade"), -1)
		if idx_grade != -1:
			result_item.insert("fields", {
				"fieldname": "points",
				"fieldtype": "Float",
				"label": "Points",
				"read_only": 1,
				"allow_on_submit": 1,
				"in_list_view": 1
			}, idx_grade)
		else:
			result_item.append("fields", {
				"fieldname": "points",
				"fieldtype": "Float",
				"label": "Points",
				"read_only": 1,
				"allow_on_submit": 1,
				"in_list_view": 1
			})
			
		# Ensure fields are ordered
		for i, f in enumerate(result_item.fields):
			f.idx = i + 1
			
		result_item.save(ignore_permissions=True)
		print("Updated Term Exam Result Item DocType")

	frappe.db.commit()
	print("Done!")
