// Copyright (c) 2026, Ashley and contributors
// For license information, please see license.txt

frappe.ui.form.on("Receipting", {
    refresh: function(frm) {
        frappe.db.get_single_value("School Settings", "allow_reference_on_receipts").then(value => {
            var is_allowed = (value == 1 || value == true);
            frm.fields_dict['invoice'].grid.set_column_disp('reference', is_allowed);
        });

        frm.set_query("student_name", function() {
            return { 
                query: "school.school_management.doctype.student.student.get_active_students",
                filters: {
                    student_class: frm.doc.student_class,
                    section: frm.doc.section
                }
            }; 
        });
        if (frm.doc.docstatus == 1) {
            frm.clear_table("invoice");
            frm.refresh_field("invoice");
            frappe.msgprint("Receipt submitted. Invoices cleared from view. Check Payment Entry: " + (frm.doc.name || ""));
        }
    },

    onload: function(frm) {
        if (!frm.doc.date) {
            frm.set_value("date", frappe.datetime.get_today());
        }
        frm.set_query("account", function() {
            return {
                filters: {
                    "account_type": ["in", ["Bank", "Cash"]],
                    "is_group": 0,
                    "company": frappe.defaults.get_default("company")
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
                for (var i = 0; i < r.message.length; i++) {
                    var inv = r.message[i];
                    var row = frm.add_child("invoice");
                    row.invoice_number = inv.name;
                    row.invoice_currency = inv.currency || "USD";
                    row.fee_item = inv.fee_item;
                    row.outstanding = inv.outstanding_amount;
                    row.total = inv.total;
                }
                frm.refresh_field("invoice");
                calculate_totals(frm);
            }
        });
    },

    account: function(frm) {
        if (!frm.doc.account) return;

        frappe.db.get_value("Account", frm.doc.account, "account_currency", function(r) {
            if (r && r.account_currency) {
                frm.set_value("currency", r.account_currency);
            } else {
                frm.set_value("currency", "USD");
            }
            // Setting currency will trigger the currency() handler below
        });
    },

    currency: function(frm) {
        if (!frm.doc.currency) return;
        
        var company_currency = "USD"; // Default fallback
        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Company",
                filters: { name: frappe.defaults.get_default("company") },
                fieldname: "default_currency"
            },
            callback: function(r) {
                if (r.message && r.message.default_currency) {
                    company_currency = r.message.default_currency;
                }
                
                if (frm.doc.currency === company_currency) {
                    frm.set_value("exchange_rate", 1.0);
                } else {
                    frappe.call({
                        method: "school.api.get_exchange_rate",
                        args: {
                            from_currency: company_currency,
                            to_currency: frm.doc.currency
                        },
                        callback: function(r) {
                            frm.set_value("exchange_rate", r.message || 1.0);
                        }
                    });
                }
            }
        });
    },

    exchange_rate: function(frm) {
        calculate_totals(frm);
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
    var receipt_currency = frm.doc.currency || "USD";
    var rate = flt(frm.doc.exchange_rate) || 1.0;

    for (var i = 0; i < rows.length; i++) {
        var row = rows[i];
        var inv_currency = row.invoice_currency || "USD";
        var out = flt(row.outstanding);

        if (receipt_currency !== inv_currency) {
            if (receipt_currency === "ZWG" && inv_currency === "USD") {
                out = out * rate;
            } else if (receipt_currency === "USD" && inv_currency === "ZWG") {
                out = out / rate;
            }
        }
        
        total_outstanding += out;
        total_allocated += flt(row.allocated);
    }
    frm.set_value("total_outstanding", total_outstanding);
    frm.set_value("total_allocated", total_allocated);
    frm.set_value("total_balance", total_outstanding - total_allocated);
}