// Copyright (c) 2026, Havano and contributors
// For license information, please see license.txt

frappe.ui.form.on("School Settings", {
	refresh(frm) {
		frappe.db.get_list('Grading Score Item', {
			fields: ['grade'],
			limit: 0
		}).then(records => {
			if(records && records.length) {
				let unique_grades = [...new Set(records.map(r => r.grade).filter(g => g))];
				unique_grades.sort();
				
				// Make it a Select field dynamically
				let field = frappe.meta.get_docfield('A Level Grade Point', 'grade', frm.doc.name);
				if(field) {
					field.fieldtype = 'Select';
					field.options = ['', ...unique_grades].join('\n');
					frm.refresh_field('a_level_grade_points');
				}
			}
		});
	}
});
