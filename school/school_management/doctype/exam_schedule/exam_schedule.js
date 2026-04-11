frappe.ui.form.on("Exam Schedule", {
    refresh(frm) {
        filter_subject_by_teacher(frm);
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
                    row.student_admission_no = student.student_reg_no;
                    row.student_name = student.full_name;
                });
                frm.refresh_field("exam_items");
                frappe.msgprint(__("Fetched " + r.message.length + " students"));
            } else {
                frappe.msgprint(__("No students found for selected class/section"));
            }
        }
    });
}
