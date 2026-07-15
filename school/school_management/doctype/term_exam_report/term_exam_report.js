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

		// Removed read-only enforcement so teacher_comment can be edited in grid
		// if (frm.fields_dict.term_exam_results && frm.fields_dict.term_exam_results.grid) {
		// 	frm.fields_dict.term_exam_results.grid.update_docfield_property('teacher_comment', 'read_only', 1);
		// 	frm.fields_dict.term_exam_results.grid.update_docfield_property('admin_comment', 'read_only', 1);
		// }

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

		// ── View Top Students ────────────────────────────────────────────────
		frm.add_custom_button(__('🏆 View Top Students'), function () {
			if (!_has_results(frm)) return;
			_open_top_students_popup(frm);
		}, __('Reports'));

		// ── Import Excel ───────────────────────────────────────────────────────
		frm.add_custom_button(__('Import Excel'), function () {
			var d = new frappe.ui.Dialog({
				title: 'Import Results from Excel',
				fields: [
					{
						fieldname: 'template_html',
						fieldtype: 'HTML',
						options: '<div style="margin-bottom: 15px;"><a href="/api/method/school.school_management.doctype.term_exam_report.term_exam_report.download_excel_template" target="_blank" class="btn btn-default btn-xs"><i class="fa fa-download"></i> Download Excel Template</a></div>'
					},
					{
						label: 'Excel File (.xlsx)',
						fieldname: 'excel_file',
						fieldtype: 'Attach',
						reqd: 1
					}
				],
				primary_action_label: 'Import',
				primary_action: function(values) {
					d.hide();
					frappe.call({
						method: 'school.school_management.doctype.term_exam_report.term_exam_report.import_results_from_excel',
						args: {
							report_name: frm.doc.name,
							file_url: values.excel_file
						},
						freeze: true,
						freeze_message: "Importing Results...",
						callback: function(r) {
							if (!r.exc) {
								frappe.msgprint("Results imported successfully.");
								frm.reload_doc();
							}
						}
					});
				}
			});
			d.show();
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
	// Build unique student list from child table rows
	var studentIds = [];
	(frm.doc.term_exam_results || []).forEach(function (row) {
		if (row.student && !studentIds.includes(row.student)) {
			studentIds.push(row.student);
		}
	});

	var fieldWrapper = frm.fields_dict['student_selector_html'];
	if (!fieldWrapper) return;
	var $wrapper = $(fieldWrapper.$wrapper || fieldWrapper.wrapper);

	if (!studentIds.length) {
		$wrapper.html(
			'<div style="padding:10px 0;color:#94a3b8;font-size:13px;">'
			+ '— Fetch results first to view individual student report cards —'
			+ '</div>'
		);
		return;
	}

	// Fetch student names from database to guarantee actual names
	frappe.call({
		method: 'frappe.client.get_list',
		args: {
			doctype: 'Student',
			filters: { name: ['in', studentIds] },
			fields: ['name', 'full_name']
		},
		callback: function (r) {
			var studentMap = {};
			if (r.message) {
				r.message.forEach(s => {
					studentMap[s.name] = s.full_name || s.name;
				});
			}
			// Fallback for any missing
			studentIds.forEach(id => {
				if (!studentMap[id]) studentMap[id] = id;
			});

			var opts = '<option value="">— Select a student to view their report card —</option>';
			// Sort alphabetically by name
			studentIds.sort(function(a, b) {
				return studentMap[a].localeCompare(studentMap[b]);
			});

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
	});
}

// ─── Open Frappe Dialog modal with embedded Print Format & Comment Fields ───
function _open_student_popup(frm, studentId, studentName) {
	// Extract existing comments for this student
	let row = (frm.doc.term_exam_results || []).find(r => r.student === studentId);
	let teacher_comment = row ? (row.teacher_comment || '') : '';
	let admin_comment = row ? (row.admin_comment || '') : '';

	// Use the well-designed custom portal page for the popup report
	var popupUrl = '/term-exam-results'
		+ '?student=' + encodeURIComponent(studentId)
		+ '&report_name=' + encodeURIComponent(frm.doc.name)
		+ '&term=' + encodeURIComponent(frm.doc.term || '')
		+ '&from=admin';

	var d = new frappe.ui.Dialog({
		title: '📝 Manage Comments & View Report — ' + (studentName || studentId),
		size: 'extra-large',
		fields: [
			{
				fieldname: 'report_iframe',
				fieldtype: 'HTML',
				options: '<iframe src="' + popupUrl + '" id="student-report-iframe" style="width:100%;height:65vh;border:1px solid #d1d5db;border-radius:6px;display:block;" allowfullscreen></iframe>'
			}
		],
		primary_action_label: '&#10003; Done — Close',
		primary_action: function () {
			d.hide();
		}
	});

	d.show();

	// Maximise dialog width
	d.$wrapper.find('.modal-dialog').css({
		'max-width': '92vw',
		'width': '92vw'
	});
}

// ─── Internal helper ──────────────────────────────────────────────────────────
function _has_results(frm) {
	if (!frm.doc.term_exam_results || frm.doc.term_exam_results.length === 0) {
		frappe.msgprint(__('No results found. Please fetch results first.'));
		return false;
	}
	return true;
}

// ─── Top Students Report Popup ──────────────────────────────────────────────
function _open_top_students_popup(frm) {
	var d = new frappe.ui.Dialog({
		title: '🏆 Top Students Report',
		size: 'large',
		fields: [
			{
				label: 'Show Top',
				fieldname: 'top_limit',
				fieldtype: 'Select',
				options: '10\n20\n30\nAll',
				default: '10',
				onchange: function() {
					render_top_students();
				}
			},
			{
				fieldname: 'report_html',
				fieldtype: 'HTML'
			}
		],
		primary_action_label: 'Close',
		primary_action: function () {
			d.hide();
		}
	});

	function render_top_students() {
		let limit = d.get_value('top_limit');
		d.fields_dict.report_html.$wrapper.html('<div class="text-center text-muted" style="padding: 20px;">Fetching...</div>');
		frappe.call({
			method: 'school.school_management.doctype.term_exam_report.term_exam_report.get_top_students_html',
			args: {
				report_name: frm.doc.name,
				limit: limit
			},
			callback: function(r) {
				if (r.message) {
					d.fields_dict.report_html.$wrapper.html(r.message);
				}
			}
		});
	}

	d.show();
	render_top_students();
	
	d.$wrapper.find('.modal-footer').prepend('<button class="btn btn-default btn-sm pull-left mr-2" id="print-top-btn" style="margin-right: 10px;">🖨 Print</button>');
	d.$wrapper.find('.modal-footer').prepend('<button class="btn btn-primary btn-sm pull-left mr-2" id="pdf-top-btn" style="margin-right: 10px;">⬇ Download PDF</button>');
	
	d.$wrapper.find('#print-top-btn').on('click', function() {
		var content = d.fields_dict.report_html.$wrapper.html();
		var printWindow = window.open('', '_blank');
		printWindow.document.write('<html><head><title>Top Students Report</title>');
		printWindow.document.write('<style>body { font-family: sans-serif; padding: 20px; } table { width: 100%; border-collapse: collapse; margin-top: 15px; } th, td { border: 1px solid #ddd; padding: 8px; text-align: left; } th { background-color: #f2f2f2; } h4 { margin-top: 30px; }</style>');
		printWindow.document.write('</head><body>');
		printWindow.document.write('<h2>🏆 Top Students - ' + (frm.doc.student_class || '') + '</h2>');
		printWindow.document.write('<h3>Term: ' + (frm.doc.term || '') + '</h3>');
		printWindow.document.write(content);
		printWindow.document.write('</body></html>');
		printWindow.document.close();
		setTimeout(function() {
			printWindow.print();
		}, 500);
	});
	
	d.$wrapper.find('#pdf-top-btn').on('click', function() {
		var limit = d.get_value('top_limit');
		var url = frappe.urllib.get_full_url(
			"/api/method/school.school_management.doctype.term_exam_report.term_exam_report.download_top_students_pdf" +
			"?report_name=" + encodeURIComponent(frm.doc.name) +
			"&limit=" + encodeURIComponent(limit)
		);
		window.open(url, '_blank');
	});
}