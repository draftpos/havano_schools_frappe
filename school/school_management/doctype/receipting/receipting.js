// Copyright (c) 2026, Ashley and contributors
frappe.ui.form.on("Receipting", {
    refresh(frm) {
        if (frm.doc.__islocal && !frm.doc.date) {
            frm.set_value("date", frappe.datetime.get_today());
        }
        frm.set_query("account", function() {
            return {
                filters: {
                    account_type: ["in", ["Cash", "Bank"]],
                    company: frappe.defaults.get_default("company")
                }
            };
        });
        frm.set_query("student_name", function() {
            let filters = {};
            if (frm.doc.student_class) filters.student_class = frm.doc.student_class;
            if (frm.doc.section) filters.section = frm.doc.section;
            return { filters: filters };
        });
    },
    onload(frm) {
        if (frm.doc.__islocal && !frm.doc.date) {
            frm.set_value("date", frappe.datetime.get_today());
        }
    },
    student_name(frm) {
        if (frm.doc.student_name) {
            frappe.db.get_value("Student", frm.doc.student_name,
                ["full_name", "student_class", "section"],
                function(r) {
                    if (r) {
                        if (r.student_class) frm.set_value("student_class", r.student_class);
                        if (r.section) frm.set_value("section", r.section);
                    }
                }
            );
            load_student_invoices(frm);
        } else {
            frm.clear_table("invoice");
            frm.refresh_field("invoice");
            frm.set_value("total_outstanding", 0);
            frm.set_value("total_allocated", 0);
            frm.set_value("total_balance", 0);
        }
    },
    student_class(frm) {
        frm.set_query("student_name", function() {
            let filters = {};
            if (frm.doc.student_class) filters.student_class = frm.doc.student_class;
            if (frm.doc.section) filters.section = frm.doc.section;
            return { filters: filters };
        });
    },
    section(frm) {
        frm.set_query("student_name", function() {
            let filters = {};
            if (frm.doc.student_class) filters.student_class = frm.doc.student_class;
            if (frm.doc.section) filters.section = frm.doc.section;
            return { filters: filters };
        });
    }
});

frappe.ui.form.on("Receipt Item", {
    allocated(frm, cdt, cdn) {
        calculate_totals(frm);
    },
    invoice_remove(frm) {
        calculate_totals(frm);
    },
});

function load_student_invoices(frm) {
    frm.clear_table("invoice");
    frm.refresh_field("invoice");
    frappe.show_alert({message: "Loading invoices...", indicator: "blue"});

    frappe.db.get_value("Student", frm.doc.student_name,
        ["full_name", "has_opening_balance", "opening_balance"],
        function(student) {
            if (!student) return;

            // Add opening balance row if applicable
            if (student.has_opening_balance && student.opening_balance > 0) {
                let row = frm.add_child("invoice");
                row.invoice_number = "";
                row.fees_structure = "Opening Balance";
                row.total = student.opening_balance;
                row.outstanding = student.opening_balance;
                row.allocated = 0;
            }

            // Load outstanding Sales Invoices
            frappe.call({
                method: "school.api.get_student_invoices",
                args: { student: frm.doc.student_name },
                callback: function(res) {
                    if (res.message && res.message.length) {
                        res.message.forEach(function(inv) {
                            let row = frm.add_child("invoice");
                            row.invoice_number = inv.name;
                            row.fees_structure = inv.fees_structure || inv.remarks || "";
                            row.total = inv.grand_total;
                            row.outstanding = inv.outstanding_amount;
                            row.allocated = 0;
                        });
                        frappe.show_alert({message: res.message.length + " invoice(s) loaded", indicator: "green"});
                    } else {
                        frappe.show_alert({message: "No outstanding invoices found", indicator: "orange"});
                    }
                    frm.refresh_field("invoice");
                    calculate_totals(frm);
                }
            });
        }
    );
}

function calculate_totals(frm) {
    let total_outstanding = 0;
    let total_allocated = 0;
    (frm.doc.invoice || []).forEach(function(row) {
        total_outstanding += row.outstanding || 0;
        total_allocated += row.allocated || 0;
    });
    frm.set_value("total_outstanding", total_outstanding);
    frm.set_value("total_allocated", total_allocated);
    frm.set_value("total_balance", total_outstanding - total_allocated);
}
