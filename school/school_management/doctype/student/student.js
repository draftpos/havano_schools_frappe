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
                    
                    // Handle portal access section visibility on refresh
                    handlePortalAccessFields(frm);
                    
                    if (r.message.enable_registration_billing) {
                        frm.set_df_property("billed_on_registration", "read_only", 1);
                    }
                }
            }
        });
    },

    create_user: function(frm) {
        handlePortalAccessFields(frm);
    },
    
    portal_email: function(frm) {
        // Validate email if non-strict email is not enabled
        if (frm.settings && !frm.settings.allow_non_strict_email && frm.doc.portal_email) {
            var email = frm.doc.portal_email;
            var emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailPattern.test(email)) {
                frappe.msgprint(__("Please enter a valid email address."));
                frm.set_value("portal_email", "");
            }
        }
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

                if (settings.enable_registration_billing) {
                    var regRows = settings.registration_billing_defaults || [];
                    var regMatch = regRows.find(row => row.status === frm.doc.student_type);
                    if (regMatch) {
                        frm.set_value("fees_structure", regMatch.fees_structure);
                        frm.set_value("billed_on_registration", 0);
                        frm.set_df_property("billed_on_registration", "read_only", 1);
                        frappe.show_alert({
                            message: __("Billing fees structure auto-set for " + frm.doc.student_type),
                            indicator: "green"
                        }, 4);
                    } else {
                        frappe.show_alert({
                            message: __("No registration billing found in Settings for: " + frm.doc.student_type),
                            indicator: "orange"
                        }, 4);
                    }
                }
            }
        });
    }
});

function handlePortalAccessFields(frm) {
    // Show/hide portal access section based on create_user checkbox
    if (frm.doc.create_user) {
        frm.set_df_property("portal_email", "reqd", 1);
        frm.toggle_display("portal_email", true);
        
        // Show password field only if non-strict email is enabled
        if (frm.settings && frm.settings.allow_non_strict_email) {
            frm.toggle_display("portal_password", true);
            frm.set_df_property("portal_password", "reqd", 1);
        } else {
            frm.toggle_display("portal_password", false);
            frm.set_df_property("portal_password", "reqd", 0);
        }
    } else {
        frm.set_df_property("portal_email", "reqd", 0);
        frm.toggle_display("portal_email", false);
        frm.toggle_display("portal_password", false);
        frm.set_df_property("portal_password", "reqd", 0);
    }
}