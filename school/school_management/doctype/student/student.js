// Copyright (c) 2026, Ashley and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student", {
    refresh: function(frm) {
        if (!frm.doc.school) {
            frm.set_value("school", "Main - SS");
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
    }
});