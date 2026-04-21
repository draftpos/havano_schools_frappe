frappe.ui.form.on('Student', {
    refresh: function(frm) {
        frm.set_query("account", function() {
            return {
                filters: {
                    is_group: 0,
                    company: frappe.defaults.get_default("company")
                }
            };
        });

        frm.set_query("section", function() {
            return {
                filters: frm.doc.student_class
                    ? { student_class: frm.doc.student_class }
                    : {}
            };
        });

        // Check School Settings for non-strict email
        frappe.call({
            method: "frappe.client.get",
            args: { doctype: "School Settings", name: "School Settings" },
            callback: function(r) {
                if (r.message) {
                    frm.settings = r.message;
                    handlePortalAccessFields(frm);
                }
            }
        });
    },
    after_save: function(frm) {
        if (frm.doc.create_user && frm.doc.portal_email) {
            frappe.msgprint({
                title: __('Portal User Created'),
                message: __('Portal user has been created for ' + frm.doc.portal_email + '. You can now login.'),
                indicator: 'green'
            });
        }
    },

    create_user: function(frm) {
        handlePortalAccessFields(frm);
    },

    student_class: function(frm) {
        frm.set_value("section", "");
        frm.set_query("section", function() {
            return {
                filters: frm.doc.student_class
                    ? { student_class: frm.doc.student_class }
                    : {}
            };
        });
    },

    admin_fee_paid: function(frm) {
        if (frm.doc.admin_fee_paid && !frm.doc.admin_fees_structure) {
            frappe.msgprint(__("Please select an Admin Fees Structure before marking as Paid."));
            frm.set_value("admin_fee_paid", 0);
        }
    },

    school: function(frm) {
        if (frm.doc.has_opening_balance && frm.doc.school) {
            frm.set_value("cost_center", frm.doc.school);
        }
    },

    has_opening_balance: function(frm) {
        if (frm.doc.has_opening_balance && frm.doc.school) {
            frm.set_value("cost_center", frm.doc.school);
        }
    },

    student_type: function(frm) {
        if (!frm.doc.student_type) return;

        frappe.call({
            method: "frappe.client.get",
            args: { doctype: "School Settings", name: "School Settings" },
            callback: function(r) {
                if (!r.message) return;
                var settings = r.message;
                frm.settings = settings;

                var adminRows = settings.fee_structure_defaults || [];
                var adminMatch = adminRows.find(row => row.status === frm.doc.student_type);
                if (adminMatch) {
                    frm.set_value("paying_admin_fee", 1);
                    frm.set_value("admin_fees_structure", adminMatch.fees_structure);
                    frappe.show_alert({
                        message: __("Admin fees structure auto-set for " + frm.doc.student_type),
                        indicator: "green"
                    }, 4);
                }
            }
        });
    }
});

function handlePortalAccessFields(frm) {
    if (frm.doc.create_user) {
        frm.set_df_property("portal_email", "reqd", 1);
        frm.toggle_display("portal_email", true);
        frm.toggle_display("portal_password", true);
        frm.set_df_property("portal_password", "reqd", 1);
    } else {
        frm.set_df_property("portal_email", "reqd", 0);
        frm.toggle_display("portal_email", false);
        frm.toggle_display("portal_password", false);
        frm.set_df_property("portal_password", "reqd", 0);
    }
}
