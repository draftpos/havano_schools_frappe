// Copyright (c) 2026, Havano and contributors
// For license information, please see license.txt

frappe.ui.form.on("Assign Class to Teacher", {
    refresh(frm) {
        if (frm.doc.teacher) {
            frappe.db.get_value("Teacher", frm.doc.teacher, "cost_center", (r) => {
                if (r && r.cost_center) frm.teacher_cost_center = r.cost_center;
            });
        }
        frm.set_query("class_name", "classes", function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            let filters = { is_active: 1 };
            
            if (row.cost_center) {
                filters.cost_center = row.cost_center;
            } else if (frm.teacher_cost_center) {
                filters.cost_center = frm.teacher_cost_center;
            }
            
            return { filters: filters };
        });

        frm.set_query("section", "classes", function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            let filters = {};
            
            if (row.cost_center) {
                filters.cost_center = row.cost_center;
            } else if (frm.teacher_cost_center) {
                filters.cost_center = frm.teacher_cost_center;
            }
            
            return { filters: filters };
        });

        frm.set_query("cost_center", "classes", function() {
            return { filters: { is_group: 0 } };
        });
    },
    
    teacher(frm) {
        if (frm.doc.teacher) {
            frappe.db.get_value("Teacher", frm.doc.teacher, "cost_center", (r) => {
                if (r && r.cost_center) {
                    frm.teacher_cost_center = r.cost_center;
                }
            });
        }
    }
});

frappe.ui.form.on("Teacher Class Assignment Item", {
    cost_center: function(frm, cdt, cdn) {
        // Refresh class_name query when cost_center in row changes
        frm.fields_dict.classes.grid.refresh();
    }
});
