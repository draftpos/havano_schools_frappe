// Copyright (c) 2026, Ashley and contributors
// For license information, please see license.txt

frappe.ui.form.on("Billing", {

    refresh(frm) {
        toggle_student_filters(frm);
        // Make class optional
        frm.set_df_property("student_class", "reqd", 0);
    },

    student(frm) {
        toggle_student_filters(frm);
        update_student_count(frm);
    },

    student_class(frm) {
        frm.set_value("section", "");
        update_student_count(frm);
    },

    section(frm) {
        update_student_count(frm);
    },

    category_1(frm) {
        frm.set_query("category_2", function() {
            return { filters: { category_1: frm.doc.category_1 } };
        });
        frm.set_value("category_2", "");
        frm.set_value("category_3", "");
        update_student_count(frm);
    },

    category_2(frm) {
        frm.set_query("category_3", function() {
            return { filters: { category_2: frm.doc.category_2 } };
        });
        frm.set_value("category_3", "");
        update_student_count(frm);
    },

    category_3(frm) {
        update_student_count(frm);
    },

    area(frm) {
        frm.set_value("territory", "");
        update_student_count(frm);
    },

    territory(frm) {
        update_student_count(frm);
    },

    fees_category(frm) {
        update_student_count(frm);
    },

});

function update_student_count(frm) {
    if (frm.doc.student) {
        frm.set_value("number_of_students", 1);
        return;
    }
    let filters = {};
    if (frm.doc.student_class) filters["student_class"] = frm.doc.student_class;
    if (frm.doc.section) filters["section"] = frm.doc.section;
    if (frm.doc.category_1) filters["category_1"] = frm.doc.category_1;
    if (frm.doc.category_2) filters["category_2"] = frm.doc.category_2;
    if (frm.doc.category_3) filters["category_3"] = frm.doc.category_3;
    if (frm.doc.area) filters["area"] = frm.doc.area;
    if (frm.doc.territory) filters["territory"] = frm.doc.territory;
    if (frm.doc.fees_category) filters["fees_category"] = frm.doc.fees_category;

    if (Object.keys(filters).length === 0) {
        frm.set_value("number_of_students", 0);
        return;
    }

    frappe.call({
        method: "frappe.client.get_count",
        args: { doctype: "Student", filters: filters },
        callback: function(r) {
            if (r.message !== undefined) {
                frm.set_value("number_of_students", r.message);
            }
        }
    });
}

function toggle_student_filters(frm) {
    let single = !!frm.doc.student;
    frm.set_df_property("student_class", "reqd", 0);
    frm.set_df_property("student_class", "hidden", single ? 1 : 0);
    frm.set_df_property("section", "hidden", single ? 1 : 0);
    frm.set_df_property("category_1", "hidden", single ? 1 : 0);
    frm.set_df_property("category_2", "hidden", single ? 1 : 0);
    frm.set_df_property("category_3", "hidden", single ? 1 : 0);
    frm.set_df_property("area", "hidden", single ? 1 : 0);
    frm.set_df_property("territory", "hidden", single ? 1 : 0);
    frm.set_df_property("fees_category", "hidden", single ? 1 : 0);
}
