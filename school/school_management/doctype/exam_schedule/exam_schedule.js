frappe.ui.form.on("Exam Schedule", {
    refresh(frm) {
        filter_subject_by_teacher(frm);
        _render_student_search_exam(frm);
    },
    student_class(frm) {
        filter_subject_by_teacher(frm);
        if (frm.doc.student_class) {
            fetch_students(frm);
        }
    },
    section(frm) {
        if (frm.doc.student_class) {
            fetch_students(frm);
        }
    }
});

function filter_subject_by_teacher(frm) {
    frappe.call({
        method: "school.school_management.doctype.exam_schedule.exam_schedule.get_teacher_subjects",
        args: {
            student_class: frm.doc.student_class || ""
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                frm.set_query("subject", function() {
                    return {
                        filters: [["name", "in", r.message]]
                    };
                });
            } else {
                frm.set_query("subject", function() {
                    return { filters: [] };
                });
            }
        }
    });
}

function fetch_students(frm) {
    frm.clear_table("exam_items");
    frm.refresh_field("exam_items");
    frappe.call({
        method: "school.school_management.doctype.exam_schedule.exam_schedule.get_students",
        args: {
            student_class: frm.doc.student_class,
            section: frm.doc.section || ""
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                r.message.forEach(function(student) {
                    let row = frm.add_child("exam_items");
                    row.student_admission_no = student.name;
                    row.student_name = student.full_name || student.name;
                });
                frm.refresh_field("exam_items");
                frappe.msgprint(__("Fetched " + r.message.length + " students"));
                // Re-render search after table is populated
                setTimeout(function() { _render_student_search_exam(frm); }, 300);
            } else {
                frappe.msgprint(__("No students found for selected class/section"));
            }
        }
    });
}

// ─── Live search box above the exam_items table ───────────────────────────────
function _render_student_search_exam(frm) {
    var grid = frm.fields_dict['exam_items'] && frm.fields_dict['exam_items'].grid;
    if (!grid) return;

    var $gridWrapper = $(grid.wrapper);
    var searchId = 'es-student-search';

    // Remove old instance to avoid duplicates on refresh
    $gridWrapper.find('#' + searchId + '-wrap').remove();

    var $searchWrap = $('<div id="' + searchId + '-wrap" style="'
        + 'display:flex;align-items:center;gap:8px;'
        + 'padding:8px 0 6px;margin-bottom:4px;">'
        + '<span style="font-size:13px;font-weight:600;color:#1e3a5f;white-space:nowrap;">'
        + '&#128269; Search Student:</span>'
        + '<input id="' + searchId + '" type="text" placeholder="Type student full name to filter rows\u2026" '
        + 'style="flex:1;max-width:380px;height:32px;padding:4px 10px;'
        + 'border:1.5px solid #d1d5db;border-radius:6px;font-size:13px;'
        + 'color:#0f172a;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.06);"/>'
        + '<span id="' + searchId + '-count" style="font-size:11px;color:#64748b;"></span>'
        + '</div>');

    $gridWrapper.prepend($searchWrap);

    $searchWrap.find('#' + searchId).on('input', function () {
        var q = $(this).val().trim().toLowerCase();
        var total = 0, visible = 0;

        $gridWrapper.find('.grid-row').each(function () {
            var $row = $(this);
            var rowName = ($row.find('[data-fieldname="student_name"] .static-area').text()
                || $row.find('[data-fieldname="student_name"] input').val()
                || $row.find('[data-fieldname="student_admission_no"] .static-area').text()
                || '').toLowerCase();
            total++;
            if (!q || rowName.includes(q)) {
                $row.show();
                visible++;
            } else {
                $row.hide();
            }
        });

        $('#' + searchId + '-count').text(q ? (visible + ' / ' + total + ' rows') : (total + ' rows'));
    });
}
