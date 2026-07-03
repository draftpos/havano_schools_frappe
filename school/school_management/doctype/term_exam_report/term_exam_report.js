frappe.ui.form.on('Term Exam Report', {

	// ─── Auto-update student count when class or section changes ───────────────

	student_class: function (frm) {
		frm.trigger('update_student_count');
	},

	section: function (frm) {
		frm.trigger('update_student_count');
	},

	update_student_count: function (frm) {
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
			callback: function (r) {
				if (r.message !== undefined) {
					frm.set_value('total_students', r.message.students);
					frm.set_value('total_subjects', r.message.subjects);
				}
			}
		});
	},

	// ─── Fetch Results ─────────────────────────────────────────────────────────

	fetch_results: function (frm) {
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
			function () {
				frappe.show_progress(__('Fetching Results'), 0, 100, __('Fetching student marks...'));

				frappe.call({
					method: 'school.school_management.doctype.term_exam_report.term_exam_report.fetch_results',
					args: { report_name: frm.doc.name },
					callback: function (r) {
						frappe.hide_progress();
						if (r.message) {
							const data = r.message;
							frm.clear_table('term_exam_results');

							data.rows.forEach(function (row) {
								let child = frm.add_child('term_exam_results');
								child.student         = row.student;
								child.student_name    = row.student_name;
								child.subject         = row.subject;
								child.exam            = row.exam;
								child.marks_obtained  = row.marks_obtained;
								child.max_marks       = row.max_marks;
								child.percentage      = row.percentage;
								child.grade           = row.grade;
								child.status          = row.status;
								child.remarks         = row.remarks;
								// ── Carry teacher comment from Exam Schedule Item ──
								child.teacher_comment = row.teacher_comment || '';
							});

							frm.set_value('total_students', data.total_students);
							frm.set_value('total_subjects', data.total_subjects);
							frm.refresh_field('term_exam_results');

							frappe.msgprint(
								__('Fetched {0} students × {1} subjects = {2} rows.',
									[data.total_students, data.total_subjects, data.rows.length]),
								__('Results Fetched')
							);

							// Rebuild the student selector dropdown after fresh fetch
							_render_student_dropdown(frm);
						}
					},
					error: function () {
						frappe.hide_progress();
					}
				});
			}
		);
	},

	// ─── Toolbar buttons ───────────────────────────────────────────────────────

	refresh: function (frm) {
		if (frm.doc.__islocal) return;

		// !! Change this to match your exact Print Format name in Frappe !!
		const PRINT_FORMAT = 'Term Exam Report Card';

		const printUrl = '/printview?'
			+ 'doctype=' + encodeURIComponent(frm.doc.doctype)
			+ '&name=' + encodeURIComponent(frm.doc.name)
			+ '&format=' + encodeURIComponent(PRINT_FORMAT)
			+ '&no_letterhead=0';

		// ── Open Report Cards ────────────────────────────────────────────────
		// Opens the print format page — student selector bar is built into the template
		frm.add_custom_button(__('📋 Open Report Cards'), function () {
			if (!_has_results(frm)) return;
			window.open(printUrl, '_blank');
		}, __('Reports'));

		// ── Print All Students ───────────────────────────────────────────────
		// Opens print format then auto-triggers the template's printAll() via hash
		frm.add_custom_button(__('🖨 Print All Students'), function () {
			if (!_has_results(frm)) return;
			const win = window.open(printUrl + '#printall', '_blank');
			if (!win) frappe.msgprint(__('Popup blocked. Please allow popups for this site and try again.'));
		}, __('Reports'));

		// ── Download All Students ────────────────────────────────────────────
		// One tab per student — template auto-prints when #autoprint hash is present.
		// User saves each as PDF via the browser's "Save as PDF" option.
		frm.add_custom_button(__('⬇ Download All Students'), function () {
			if (!_has_results(frm)) return;

			// Gather unique students from the child table
			const studentMap = {};
			(frm.doc.term_exam_results || []).forEach(function (row) {
				if (row.student && !studentMap[row.student]) {
					studentMap[row.student] = row.student_name || row.student;
				}
			});
			const studentIds = Object.keys(studentMap);
			const total = studentIds.length;

			frappe.confirm(
				__('This will open {0} browser print dialog(s) — one per student. '
					+ 'In each dialog choose "Save as PDF" to download the file. '
					+ 'Your browser must allow pop-ups. Continue?', [total]),
				function () {
					frappe.show_progress(__('Opening Reports'), 0, total, __('Starting...'));

					studentIds.forEach(function (sid, index) {
						// Stagger tab openings so each has time to load before the next
						setTimeout(function () {
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
								setTimeout(function () {
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

		// ── Render student selector dropdown ─────────────────────────────────
		_render_student_dropdown(frm);
	},

	term_exam_results_add: function (frm, cdt, cdn) {
		// Just a placeholder if needed
	}
});

frappe.ui.form.on('Term Exam Result Item', {
	admin_comment: function (frm, cdt, cdn) {
		// When admin_comment is updated in one row, update all other rows for the same student
		let row = frappe.get_doc(cdt, cdn);
		if (row.student && row.admin_comment) {
			(frm.doc.term_exam_results || []).forEach(function (item) {
				if (item.student === row.student && item.name !== row.name) {
					frappe.model.set_value(item.doctype, item.name, 'admin_comment', row.admin_comment);
				}
			});
			frm.refresh_field('term_exam_results');
		}
	},

	form_render: function (frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		if (row.student) {
			frm.fields_dict.term_exam_results.grid.add_custom_button(__('View Portal Results'), function () {
				const student = row.student;
				const term = frm.doc.term;
				// Find the first exam for this student in the table
				let exam = row.exam;
				if (!exam) {
					const firstExamRow = (frm.doc.term_exam_results || []).find(r => r.student === student && r.exam);
					exam = firstExamRow ? firstExamRow.exam : '';
				}

				if (!student || !term || !exam) {
					frappe.msgprint(__('Missing Student, Term or Exam information.'));
					return;
				}

				const url = `/term-exam-results?student=${encodeURIComponent(student)}&term=${encodeURIComponent(term)}&exam=${encodeURIComponent(exam)}&report_name=${encodeURIComponent(frm.doc.name)}`;
				window.open(url, '_blank');
			}, cdn);
		}
	}
});

// ─── Render student selector dropdown ────────────────────────────────────────
function _render_student_dropdown(frm) {
	// Build unique student map from child table rows
	var studentMap = {};
	(frm.doc.term_exam_results || []).forEach(function (row) {
		if (row.student && !studentMap[row.student]) {
			studentMap[row.student] = row.student_name || row.student;
		}
	});

	var studentIds = Object.keys(studentMap);

	var fieldWrapper = frm.fields_dict['student_selector_html'];
	if (!fieldWrapper) return;

	// Try different possible wrapper targets depending on Frappe version
	var $wrapper = $(fieldWrapper.$wrapper || fieldWrapper.wrapper);

	if (!studentIds.length) {
		$wrapper.html(
			'<div style="padding:10px 0;color:#94a3b8;font-size:13px;">'
			+ '— Fetch results first to view individual student report cards —'
			+ '</div>'
		);
		return;
	}

	// Build <select> options
	var opts = '<option value="">— Select a student to view their report card —</option>';
	studentIds.forEach(function (sid) {
		opts += '<option value="' + sid + '">'
			+ frappe.utils.escape_html(studentMap[sid])
			+ ' &nbsp;(' + frappe.utils.escape_html(sid) + ')'
			+ '</option>';
	});

	$wrapper.html(
		'<div style="display:flex;align-items:center;gap:12px;padding:12px 0 6px;">'
		+ '<label style="font-weight:600;color:#1e3a5f;white-space:nowrap;font-size:13px;min-width:fit-content;">'
		+ '&#128065; View Student Report Card:'
		+ '</label>'
		+ '<select id="student-report-selector" style="'
		+ 'flex:1;max-width:420px;height:36px;padding:4px 12px;'
		+ 'border:1.5px solid #d1d5db;border-radius:6px;'
		+ 'font-size:13px;background:#fff;cursor:pointer;color:#0f172a;'
		+ 'box-shadow:0 1px 3px rgba(0,0,0,.06);'
		+ '">' + opts + '</select>'
		+ '<span style="font-size:11px;color:#64748b;">'
		+ studentIds.length + ' student' + (studentIds.length !== 1 ? 's' : '')
		+ '</span>'
		+ '</div>'
	);

	// Wire up change → popup
	$wrapper.find('#student-report-selector').on('change', function () {
		var sid = $(this).val();
		if (!sid) return;
		_open_student_popup(frm, sid, studentMap[sid]);
		// Reset dropdown back to placeholder so it can be re-selected
		$(this).val('');
	});
}

// ─── Open Frappe Print Format in new window ─────────────────────────────────
function _open_student_popup(frm, studentId, studentName) {
	const PRINT_FORMAT = 'Term Exam Report Card'; // Or Term Exam Report Premium if that's the one they use
	const printUrl = '/printview?'
		+ 'doctype=' + encodeURIComponent(frm.doc.doctype)
		+ '&name=' + encodeURIComponent(frm.doc.name)
		+ '&format=' + encodeURIComponent(PRINT_FORMAT)
		+ '&no_letterhead=0'
		+ '&student_filter=' + encodeURIComponent(studentId);

	window.open(printUrl, '_blank');
}

// ─── Internal helper ──────────────────────────────────────────────────────────
function _has_results(frm) {
	if (!frm.doc.term_exam_results || frm.doc.term_exam_results.length === 0) {
		frappe.msgprint(__('No results found. Please fetch results first.'));
		return false;
	}
	return true;
}