// Copyright (c) 2026, Ashley and contributors
// For license information, please see license.txt
frappe.ui.form.on("Student", {
    refresh: function(frm) {
        if (!frm.doc.school) {
            frm.set_value("school", "Main - SS");
        }

        // Add New School button
        frm.add_custom_button(__('New School'), function() {
            frappe.new_doc('Cost Center');
        }, __('Actions'));

        // Quick Add School dialog
        frm.add_custom_button(__('Quick Add School'), function() {
            frappe.prompt([
                {
                    label: 'School Name',
                    fieldname: 'cost_center_name',
                    fieldtype: 'Data',
                    reqd: 1
                },
                {
                    label: 'Parent Cost Center',
                    fieldname: 'parent_cost_center',
                    fieldtype: 'Link',
                    options: 'Cost Center',
                    reqd: 1,
                    default: 'Showline Solutions - SS'
                }
            ],
            function(values) {
                frappe.call({
                    method: 'frappe.client.insert',
                    args: {
                        doc: {
                            doctype: 'Cost Center',
                            cost_center_name: values.cost_center_name,
                            parent_cost_center: values.parent_cost_center,
                            company: frappe.defaults.get_default('company') || 'Showline Solutions'
                        }
                    },
                    callback: function(r) {
                        if (r.message) {
                            frappe.show_alert({
                                message: __('School ' + r.message.name + ' created successfully'),
                                indicator: 'green'
                            });
                            frm.set_value('school', r.message.name);
                        }
                    }
                });
            },
            'Quick Add New School',
            'Create'
            );
        }, __('Actions'));

        // Show invoice/payment status if admin fee is set
        if (frm.doc.paying_admin_fee && frm.doc.admin_fees_structure && !frm.is_new()) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Sales Invoice",
                    filters: {
                        customer: frm.doc.full_name,
                        fees_structure: frm.doc.admin_fees_structure,
                        docstatus: ["!=", 2]
                    },
                    fields: ["name", "outstanding_amount", "status"],
                    limit: 1
                },
                callback: function(r) {
                    if (r.message && r.message.length) {
                        var inv = r.message[0];
                        frm.dashboard.add_comment(
                            '🧾 Admin Fee Invoice: <a href="/app/sales-invoice/' + inv.name + '">' + inv.name + '</a> — Status: <b>' + inv.status + '</b>',
                            inv.status === "Paid" ? "green" : "orange",
                            true
                        );
                    }
                }
            });
        }
    },

    onload: function(frm) {
        if (!frm.doc.school) {
            frm.set_value("school", "Main - SS");
        }
    },

    school: function(frm) {
        if (frm.doc.school) {
            frm.set_value("cost_center", frm.doc.school);
        }
        // Filter admin fees structure by school/cost center
        frm.set_query("admin_fees_structure", function() {
            return {
                filters: {
                    cost_center: frm.doc.school
                }
            };
        });
        // Auto-generate student_reg_no when school changes
        if (frm.doc.school) {
            frappe.call({
                method: "school.school_management.doctype.student.student.generate_reg_no_for_school",
                args: {
                    school: frm.doc.school,
                    current_student: frm.doc.name || null
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value("student_reg_no", r.message);
                    }
                }
            });
        }
    },

    paying_admin_fee: function(frm) {
        if (!frm.doc.paying_admin_fee) {
            frm.set_value("admin_fee_paid", 0);
            frm.set_value("admin_fees_structure", "");
        }
        // Filter admin fees structure by school/cost center
        if (frm.doc.school) {
            frm.set_query("admin_fees_structure", function() {
                return {
                    filters: {
                        cost_center: frm.doc.school
                    }
                };
            });
        }
    },

    admin_fee_paid: function(frm) {
        if (frm.doc.admin_fee_paid && !frm.doc.admin_fees_structure) {
            frappe.msgprint(__("Please select an Admin Fees Structure before marking as Paid."));
            frm.set_value("admin_fee_paid", 0);
        }
    }
});