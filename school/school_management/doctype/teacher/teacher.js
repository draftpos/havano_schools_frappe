frappe.ui.form.on('Teacher', {
    refresh: function(frm) {
        handlePortalAccessFields(frm);

        if (!frm.is_new()) {
            frm.add_custom_button(__('Create Teacher User'), function() {
                frm.call('create_teacher_user').then(r => {
                    if (!r.exc) frm.reload_doc();
                });
            }, __('Portal Access'));
        }
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
