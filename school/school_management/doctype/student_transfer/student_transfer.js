// Copyright (c) 2026, Havano and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Transfer", {

    refresh(frm) {
        // Filter student field to only show Active students
        frm.set_query("student", function () {
            return {
                filters: {
                    transfer_status: ["in", ["Active", "", null]],
                },
            };
        });

        if (frm.doc.student && frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Check Outstanding Balance"), function () {
                frappe.call({
                    method: "school.school_management.doctype.student_transfer.student_transfer.get_student_outstanding",
                    args: { student: frm.doc.student },
                    callback(r) {
                        if (r.message) {
                            let bal = r.message.outstanding;
                            if (bal > 0) {
                                frappe.msgprint({
                                    title: __("Outstanding Balance"),
                                    message: __(`Student has an outstanding balance of <b>${bal}</b>. Clear dues before transferring.`),
                                    indicator: "red",
                                });
                            } else {
                                frappe.msgprint({
                                    title: __("No Outstanding Balance"),
                                    message: __("Student has no outstanding balance. Safe to transfer."),
                                    indicator: "green",
                                });
                            }
                        }
                    },
                });
            });
        }

        // Status banner
        if (frm.doc.status === "Transferred") {
            frm.set_intro(__("This student has been transferred."), "blue");
        } else if (frm.doc.status === "Inactive") {
            frm.set_intro(__("This student has been marked inactive."), "orange");
        }

        // Make fetched fields read-only
        ["full_name", "student_reg_no", "student_class", "section", "school",
            "date_of_birth", "gender", "student_phone_number"].forEach(function (f) {
                frm.set_df_property(f, "read_only", 1);
            });
    },

    student(frm) {
        if (!frm.doc.student) return;

        // Check outstanding on student selection
        frappe.call({
            method: "school.school_management.doctype.student_transfer.student_transfer.get_student_outstanding",
            args: { student: frm.doc.student },
            callback(r) {
                if (r.message && r.message.outstanding > 0) {
                    frappe.show_alert({
                        message: __(`Student has outstanding balance of ${r.message.outstanding}. Transfer will be blocked.`),
                        indicator: "red",
                    });
                } else {
                    frappe.show_alert({
                        message: __("No outstanding balance."),
                        indicator: "green",
                    });
                }
            },
        });

        // Default transfer date to today
        if (!frm.doc.transfer_date) {
            frm.set_value("transfer_date", frappe.datetime.get_today());
        }
    },
});