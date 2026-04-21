frappe.ui.form.on('Teacher', {
    refresh: function(frm) {
        handlePortalAccessFields(frm);
    },

    create_user: function(frm) {
        handlePortalAccessFields(frm);
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
