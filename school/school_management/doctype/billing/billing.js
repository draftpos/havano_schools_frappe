// Copyright (c) 2026, Ashley and contributors
// For license information, please see license.txt

frappe.ui.form.on("Billing", {
    refresh: function(frm) {
        toggle_student_filters(frm);
        frm.set_df_property("student_class", "reqd", 0);

        if (!frm.doc.cost_center) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "User",
                    filters: { name: frappe.session.user },
                    fieldname: "school"
                },
                callback: function(r) {
                    if (r.message && r.message.school) {
                        frm.set_value("cost_center", r.message.school);
                    }
                    apply_cost_center_filters(frm);
                }
            });
        } else {
            apply_cost_center_filters(frm);
        }
    },

    onload: function(frm) {
        // Run filter application on load to ensure dropdowns are ready
        apply_cost_center_filters(frm);
    },

    student: function(frm) {
        toggle_student_filters(frm);
        update_student_count(frm);
    },

    fees_structure: function(frm) {
        if (!frm.doc.fees_structure) return;
        frappe.call({
            method: "frappe.client.get",
            args: { doctype: "Fees Structure", name: frm.doc.fees_structure },
            callback: function(r) {
                if (!r.message) return;
                frm.clear_table("items");
                (r.message.fees_items || []).forEach(function(item) {
                    var row = frm.add_child("items");
                    row.item_code = item.item_code;
                    row.item_name = item.item_name;
                    row.qty = item.qty || 1;
                    row.rate = item.rate || 0;
                    row.amount = (item.qty || 1) * (item.rate || 0);
                    row.cost_center = frm.doc.cost_center || "";
                });
                frm.refresh_field("items");
            }
        });
    },

    student_class: function(frm) {
        // Clear section when class changes
        frm.set_value("section", "");
        frm.set_value("section1", "");
        update_student_count(frm);
        
        if (frm.doc.student_class) {
            frappe.show_alert({
                message: __("Class set."),
                indicator: "green"
            }, 3);
        }
    },

    section: function(frm) {
        // Update student count when section changes
        update_student_count(frm);
        
        if (frm.doc.section) {
            frappe.show_alert({
                message: __("Section selected: ") + frm.doc.section,
                indicator: "blue"
            }, 2);
        }
    },

    section1: function(frm) {
        // Handle alternative section field
        update_student_count(frm);
    },

    cost_center: function(frm) {
        frm.set_value("student_class", "");
        frm.set_value("section", "");
        frm.set_value("section1", "");
        frm.set_value("student", "");
        apply_cost_center_filters(frm);
        update_student_count(frm);
    },

    category_1: function(frm) {
        frm.set_query("category_2", function() {
            return { filters: { category_1: frm.doc.category_1 } };
        });
        frm.set_value("category_2", "");
        frm.set_value("category_3", "");
        update_student_count(frm);
    },
    category_2: function(frm) {
        frm.set_query("category_3", function() {
            return { filters: { category_2: frm.doc.category_2 } };
        });
        frm.set_value("category_3", "");
        update_student_count(frm);
    },
    category_3: function(frm) { update_student_count(frm); },
    area: function(frm) {
        frm.set_value("territory", "");
        update_student_count(frm);
    },
    territory: function(frm) { update_student_count(frm); },
    fees_category: function(frm) { update_student_count(frm); }
});

function apply_cost_center_filters(frm) {
    var cc = frm.doc.cost_center;

    // Filter student_class — show all classes
    frm.set_query("student_class", function() {
        return {};
    });

    // MODIFIED: Section filter - shows ALL sections regardless of class
    let section_query = function() {
        return {};  // No filters - shows all sections
    };

    frm.set_query("section", section_query);
    frm.set_query("section1", section_query);

    // Filter student
    frm.set_query("student", function() {
        var f = {};
        if (cc) f["school"] = cc;
        if (frm.doc.student_class) f["student_class"] = frm.doc.student_class;
        if (frm.doc.section) f["section"] = frm.doc.section;
        return { filters: f };
    });

    // Filter fees_structure by cost center
    frm.set_query("fees_structure", function() {
        var f = {};
        if (cc) f["cost_center"] = cc;
        return { filters: f };
    });
}

function update_student_count(frm) {
    if (frm.doc.student) {
        frm.set_value("number_of_students", 1);
        return;
    }
    
    var filters = {};
    
    // Build filters for student count
    if (frm.doc.cost_center) filters["school"] = frm.doc.cost_center;
    if (frm.doc.student_class) filters["student_class"] = frm.doc.student_class;
    
    // Use section field (prioritize section over section1)
    var active_section = frm.doc.section || frm.doc.section1;
    if (active_section) filters["section"] = active_section;
    
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
                if (r.message > 0) {
                    frappe.show_alert({
                        message: __("Found ") + r.message + __(" student(s)"),
                        indicator: "green"
                    }, 2);
                }
            }
        }
    });
}

function toggle_student_filters(frm) {
    var single = !!frm.doc.student;
    frm.set_df_property("student_class", "reqd", 0);
    frm.set_df_property("student_class", "hidden", single ? 1 : 0);
    frm.set_df_property("section", "hidden", single ? 1 : 0);
    frm.set_df_property("section1", "hidden", single ? 1 : 0);
    frm.set_df_property("other_filtering_section", "hidden", single ? 1 : 0);
    frm.set_df_property("category_1", "hidden", single ? 1 : 0);
    frm.set_df_property("category_2", "hidden", single ? 1 : 0);
    frm.set_df_property("category_3", "hidden", single ? 1 : 0);
    frm.set_df_property("area", "hidden", single ? 1 : 0);
    frm.set_df_property("territory", "hidden", single ? 1 : 0);
    frm.set_df_property("fees_category", "hidden", single ? 1 : 0);
    frm.set_df_property("student", "hidden", 0);
}