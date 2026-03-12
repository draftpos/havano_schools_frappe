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

    },
    onload(frm) {
        if (frm.doc.__islocal && !frm.doc.date) {
            frm.set_value("date", frappe.datetime.get_today());
        }
    },
    student_name(frm) {
        if (frm.doc.student_name) {
            frappe.call({
                method: "frappe.client.get",
                args: { doctype: "Student", name: frm.doc.student_name },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value("student_class", r.message.student_class);
                        frm.set_value("section", r.message.section);
                    }
                }
            });
            load_student_invoices(frm);
        } else {
            frm.clear_table("invoice");
            frm.refresh_field("invoice");
            frm.set_value("total_outstanding", 0);
            frm.set_value("total_allocated", 0);
            frm.set_value("total_balance", 0);
        }
    },
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
    frappe.call({
        method: "frappe.client.get",
        args: { doctype: "Student", name: frm.doc.student_name },
        callback: function(r) {
            if (!r.message) return;
            let student = r.message;
            if (student.has_opening_balance && student.opening_balance > 0) {
                let row = frm.add_child("invoice");
                row.invoice_number = "";
                row.fees_structure = "Opening Balance";
                row.total = student.opening_balance;
                row.outstanding = student.opening_balance;
                row.allocated = 0;
            }
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Sales Invoice",
                    filters: {
                        customer: student.full_name,
                        docstatus: 1,
                        outstanding_amount: [">", 0]
                    },
                    fields: ["name", "grand_total", "outstanding_amount", "remarks", "fees_structure"],
                    order_by: "posting_date asc"
                },
                callback: function(r2) {
                    if (r2.message && r2.message.length > 0) {
                        r2.message.forEach(function(inv) {
                            let row = frm.add_child("invoice");
                            row.invoice_number = inv.name;
                            row.fees_structure = inv.fees_structure || inv.remarks || "";
                            row.total = inv.grand_total;
                            row.outstanding = inv.outstanding_amount;
                            row.allocated = 0;
                        });
                    }
                    frm.refresh_field("invoice");
                    calculate_totals(frm);
                }
            });
        }
    });
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
