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
    }
});
