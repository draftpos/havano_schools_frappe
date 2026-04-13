frappe.ui.form.on('Term Exam Report', {

	// ─── Auto-update student count when class or section changes ───────────────

	student_class: function(frm) {
		frm.trigger('update_student_count');
	},

	section: function(frm) {
		frm.trigger('update_student_count');
	},

	update_student_count: function(frm) {
		if (!frm.doc.student_class) {
			frm.set_value('total_students', 0);
			return;
		}

		frappe.call({
			method: 'school.school_management.doctype.term_exam_report.term_exam_report.get_student_count',
			args: {
				student_class: frm.doc.student_class,
				section: frm.doc.section || ''
			},
			callback: function(r) {
				if (r.message !== undefined) {
					frm.set_value('total_students', r.message.students);
					frm.set_value('total_subjects', r.message.subjects);
				}
			}
		});
	},

	// ─── Fetch Results ─────────────────────────────────────────────────────────

	fetch_results: function(frm) {
		if (!frm.doc.term || !frm.doc.student_class) {
			frappe.msgprint(__('Please set Term and Class first.'));
			return;
		}

		if (frm.doc.__islocal) {
			frappe.msgprint(__('Please save the document first before fetching results.'));
			return;
		}

		frappe.confirm(
			__('This will replace all existing results in the table. Continue?'),
			function() {
				frappe.show_progress(__('Fetching Results'), 0, 100, __('Fetching student marks...'));

				frappe.call({
					method: 'school.school_management.doctype.term_exam_report.term_exam_report.fetch_results',
					args: { report_name: frm.doc.name },
					callback: function(r) {
						frappe.hide_progress();
						if (r.message) {
							const data = r.message;
							frm.clear_table('term_exam_results');

							data.rows.forEach(function(row) {
								let child = frm.add_child('term_exam_results');
								child.student        = row.student;
								child.student_name   = row.student_name;
								child.subject        = row.subject;
								child.exam           = row.exam;
								child.marks_obtained = row.marks_obtained;
								child.max_marks      = row.max_marks;
								child.percentage     = row.percentage;
								child.grade          = row.grade;
								child.status         = row.status;
								child.remarks        = row.remarks;
							});

							frm.set_value('total_students', data.total_students);
							frm.set_value('total_subjects', data.total_subjects);
							frm.refresh_field('term_exam_results');

							frappe.msgprint(
								__('Fetched {0} students × {1} subjects = {2} rows.',
									[data.total_students, data.total_subjects, data.rows.length]),
								__('Results Fetched')
							);
						}
					},
					error: function() {
						frappe.hide_progress();
					}
				});
			}
		);
	},

	// ─── Toolbar buttons ───────────────────────────────────────────────────────

	refresh: function(frm) {
		if (frm.doc.__islocal) return;

		// !! Change this to match your exact Print Format name in Frappe !!
		const PRINT_FORMAT = 'Term Exam Report Card';

		const printUrl = '/printview?'
			+ 'doctype=' + encodeURIComponent(frm.doc.doctype)
			+ '&name='   + encodeURIComponent(frm.doc.name)
			+ '&format=' + encodeURIComponent(PRINT_FORMAT)
			+ '&no_letterhead=0';

		// ── Open Report Cards ────────────────────────────────────────────────
		// Opens the print format page — student selector bar is built into the template
		frm.add_custom_button(__('📋 Open Report Cards'), function() {
			if (!_has_results(frm)) return;
			window.open(printUrl, '_blank');
		}, __('Reports'));

		// ── Print All Students ───────────────────────────────────────────────
		// Opens print format then auto-triggers the template's printAll() via hash
		frm.add_custom_button(__('🖨 Print All Students'), function() {
			if (!_has_results(frm)) return;
			const win = window.open(printUrl + '#printall', '_blank');
			if (!win) frappe.msgprint(__('Popup blocked. Please allow popups for this site and try again.'));
		}, __('Reports'));

		// ── Download All Students ────────────────────────────────────────────
		// One tab per student — template auto-prints when #autoprint hash is present.
		// User saves each as PDF via the browser's "Save as PDF" option.
		frm.add_custom_button(__('⬇ Download All Students'), function() {
			if (!_has_results(frm)) return;

			// Gather unique students from the child table
			const studentMap = {};
			(frm.doc.term_exam_results || []).forEach(function(row) {
				if (row.student && !studentMap[row.student]) {
					studentMap[row.student] = row.student_name || row.student;
				}
			});
			const studentIds = Object.keys(studentMap);
			const total      = studentIds.length;

			frappe.confirm(
				__('This will open {0} browser print dialog(s) — one per student. '
				 + 'In each dialog choose "Save as PDF" to download the file. '
				 + 'Your browser must allow pop-ups. Continue?', [total]),
				function() {
					frappe.show_progress(__('Opening Reports'), 0, total, __('Starting...'));

					studentIds.forEach(function(sid, index) {
						// Stagger tab openings so each has time to load before the next
						setTimeout(function() {
							frappe.show_progress(
								__('Opening Reports'), index + 1, total,
								__('Opening: {0}', [studentMap[sid]])
							);

							// Pass student_filter in URL — template reads it to show only that student
							// and auto-triggers window.print() when #autoprint hash is present
							const url = printUrl
								+ '&student_filter=' + encodeURIComponent(sid)
								+ '#autoprint';

							const win = window.open(url, '_blank');
							if (!win) {
								frappe.hide_progress();
								frappe.msgprint(__(
									'Pop-up blocked after {0} window(s). '
									+ 'Please allow pop-ups and try again.', [index]
								));
								return;
							}

							if (index === total - 1) {
								setTimeout(function() {
									frappe.hide_progress();
									frappe.msgprint(
										__('Opened {0} print dialog(s). '
										 + 'Use "Save as PDF" in each to save individual files.', [total]),
										__('Done')
									);
								}, 800);
							}
						}, index * 1500); // 1.5 s gap per tab
					});
				}
			);
		}, __('Reports'));
	}
});

// ─── Internal helper ──────────────────────────────────────────────────────────
function _has_results(frm) {
	if (!frm.doc.term_exam_results || frm.doc.term_exam_results.length === 0) {
		frappe.msgprint(__('No results found. Please fetch results first.'));
		return false;
	}
	return true;
}