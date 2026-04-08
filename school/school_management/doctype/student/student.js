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

        frappe.call({
            method: "frappe.client.get",
            args: { doctype: "School Settings", name: "School Settings" },
            callback: function(r) {
                if (r.message && r.message.enable_registration_billing) {
                    frm.set_df_property("billed_on_registration", "read_only", 1);
                }
            }
        });
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
