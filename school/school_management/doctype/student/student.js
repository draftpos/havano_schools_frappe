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
        
        // Add custom button to update password manually
        if (frm.doc.create_user && frm.doc.portal_email) {
            frm.add_custom_button(__('Update Portal Password'), function() {
                updatePortalPassword(frm);
            }, __('Portal'));
        }
    },
    
    after_save: function(frm) {
        // Check if create_user is checked and password was provided
        if (frm.doc.create_user && frm.doc.portal_password && frm.settings && frm.settings.allow_non_strict_email) {
            frappe.confirm(
                __('Do you want to update the portal password for ' + frm.doc.portal_email + ' now?'),
                function() {
                    // Yes - update password
                    updatePortalPassword(frm);
                },
                function() {
                    // No - do nothing
                    frappe.msgprint({
                        title: __('Password Not Updated'),
                        message: __('You can update the password later using the "Update Portal Password" button.'),
                        indicator: 'orange'
                    });
                }
            );
        }
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
            frm.set_df_property("portal_password", "reqd", 0);
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

function updatePortalPassword(frm) {
    if (!frm.doc.portal_email) {
        frappe.msgprint({
            title: __('Error'),
            message: __('No portal email found. Please set a portal email first.'),
            indicator: 'red'
        });
        return;
    }
    
    // Ask for password if not already set
    let password = frm.doc.portal_password;
    
    if (!password) {
        frappe.prompt({
            fieldtype: 'Password',
            label: 'New Password',
            fieldname: 'password',
            reqd: 1,
            description: 'Enter the new password for ' + frm.doc.portal_email
        }, function(values) {
            updateUserPassword(frm, values.password);
        }, __('Set Portal Password'), __('Update'));
    } else {
        updateUserPassword(frm, password);
    }
}

function updateUserPassword(frm, password) {
    // Try different method paths
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            "doctype": "Student",
            "filters": {"name": frm.doc.name},
            "fieldname": "name"
        },
        callback: function(response) {
            // Method exists, now call the password update
            frappe.call({
                method: "frappe.client.set_value",
                args: {
                    "doctype": "User",
                    "name": frm.doc.portal_email,
                    "fieldname": "new_password",
                    "value": password
                },
                callback: function(resp) {
                    if (resp.message) {
                        frappe.msgprint({
                            title: __('Password Updated'),
                            message: __('Portal password has been successfully updated for ' + frm.doc.portal_email),
                            indicator: 'green'
                        });
                        frm.set_value("portal_password", "");
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            message: __('Failed to update password. Please update manually in User doctype.'),
                            indicator: 'red'
                        });
                    }
                },
                error: function(error) {
                    // If direct method fails, try reset password
                    frappe.call({
                        method: "frappe.core.doctype.user.user.reset_password",
                        args: {
                            "user": frm.doc.portal_email
                        },
                        callback: function(res) {
                            frappe.msgprint({
                                title: __('Password Reset Email Sent'),
                                message: __('A password reset link has been sent to ' + frm.doc.portal_email),
                                indicator: 'green'
                            });
                        }
                    });
                }
            });
        }
    });
}