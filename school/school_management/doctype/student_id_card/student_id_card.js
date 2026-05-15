frappe.ui.form.on("Student ID Card", {
	student_class(frm) {
		fetch_students(frm);
	},
	section(frm) {
		fetch_students(frm);
	},
});

// Logic for child table fields
frappe.ui.form.on("Student ID Card Item", {
	students_add(frm, cdt, cdn) {
		// Set default validity when a row is manually added
		frappe.model.set_value(cdt, cdn, "valid_from", frappe.datetime.get_today());
		frappe.model.set_value(cdt, cdn, "valid_until", frappe.datetime.add_months(frappe.datetime.get_today(), 48));
	},
	valid_from(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		if (row.valid_from) {
			frappe.model.set_value(cdt, cdn, "valid_until", frappe.datetime.add_months(row.valid_from, 48));
		}
	},
});

function fetch_students(frm) {
	if (!frm.doc.student_class) return;

	frappe.call({
		method: "school.school_management.doctype.student_id_card.student_id_card.get_students",
		args: {
			student_class: frm.doc.student_class,
			section: frm.doc.section,
		},
		callback: function (r) {
			if (r.message) {
				frm.clear_table("students");
				r.message.forEach((student) => {
					let child = frm.add_child("students");
					child.student_reg_no = student.name;
					// Fetch from logic in JSON will handle most fields, 
					// but we set them manually for immediate feedback and consistency.
					child.student_id = student.name;
					child.full_name = student.full_name;
					child.student_class = student.student_class;
					child.section = student.section;
					child.house = student.house;
					child.date_of_birth = student.date_of_birth;
					child.sex = student.gender;
					child.date_of_admission = student.date_of_admission;
					child.passport_image = student.student_image;

					// Set validity for 4 years from today by default
					child.valid_from = frappe.datetime.get_today();
					child.valid_until = frappe.datetime.add_months(child.valid_from, 48);
				});
				frm.refresh_field("students");
			}
		},
	});
}
