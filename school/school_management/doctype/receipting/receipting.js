// Copyright (c) 2026, Ashley and contributors
// For license information, please see license.txt

frappe.ui.form.on("Receipting", {
    refresh: function(frm) {
        if (!frm.doc.date) {
            frm.set_value("date", frappe.datetime.get_today());
        }
        frm.set_query("account", function() {
            return {
                filters: {
                    "name": ["in", ["Cash - SS", "Bank Payment - SS"]]
                }
            };
        });
    },

    onload: function(frm) {
        if (!frm.doc.date) {
            frm.set_value("date", frappe.datetime.get_today());
        }
        frm.set_query("account", function() {
            return {
                filters: {
                    "name": ["in", ["Cash - SS", "Bank Payment - SS"]]
                }
            };
        });
    },

    student_name: function(frm) {
        if (!frm.doc.student_name) return;

        frappe.db.get_value("Student", frm.doc.student_name, ["student_class", "section"], function(r) {
            if (r) {
                frm.set_value("student_class", r.student_class);
                frm.set_value("section", r.section);
            }
        });

        frappe.call({
            method: "school.api.get_student_invoices",
            args: { student: frm.doc.student_name },
            callback: function(r) {
                if (!r.message) return;
                frm.clear_table("invoice");
                var total_out = 0;
                for (var i = 0; i < r.message.length; i++) {
                    var inv = r.message[i];
                    var row = frm.add_child("invoice");
                    row.invoice_number = inv.name;
                    row.fees_structure = inv.fees_structure;
                    row.outstanding = inv.outstanding_amount;
                    row.total = inv.grand_total;
                    total_out += (inv.outstanding_amount || 0);
                }
                frm.set_value("total_outstanding", total_out);
                frm.refresh_field("invoice");
                calculate_totals(frm);
            }
        });
    }
});

frappe.ui.form.on("Receipt Item", {
    allocated: function(frm) {
        calculate_totals(frm);
    },
    invoice_remove: function(frm) {
        calculate_totals(frm);
    }
});

function calculate_totals(frm) {
    var total_outstanding = 0;
    var total_allocated = 0;
    var rows = frm.doc.invoice || [];
    for (var i = 0; i < rows.length; i++) {
        total_outstanding += (rows[i].outstanding || 0);
        total_allocated += (rows[i].allocated || 0);
    }
    frm.set_value("total_outstanding", total_outstanding);
    frm.set_value("total_allocated", total_allocated);
    frm.set_value("total_balance", total_outstanding - total_allocated);
}