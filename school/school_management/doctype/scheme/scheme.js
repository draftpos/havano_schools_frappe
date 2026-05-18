frappe.ui.form.on('Scheme', {
	setup: function(frm) {
		// Only list active student classes in schemes child table
		frm.set_query('student_class', 'schemes', function() {
			return {
				filters: {
					is_active: 1
				}
			};
		});
	}
});

frappe.ui.form.on('Scheme Entry', {
	subject: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.subject) {
			frappe.db.get_value('Subject', row.subject, 'department')
				.then(r => {
					if (r && r.message && r.message.department) {
						let dept = r.message.department;
						frappe.db.get_value('Department', dept, 'hod')
							.then(res => {
								if (res && res.message && res.message.hod) {
									frappe.model.set_value(cdt, cdn, 'hod', res.message.hod);
								} else {
									frappe.model.set_value(cdt, cdn, 'hod', '');
								}
							});
					} else {
						frappe.model.set_value(cdt, cdn, 'hod', '');
					}
				});
		} else {
			frappe.model.set_value(cdt, cdn, 'hod', '');
		}
	}
});
