frappe.query_reports["School Receivables"] = {
    filters: [
        {
            fieldname: "cost_center",
            label: __("School / Cost Centre"),
            fieldtype: "Link",
            options: "Cost Center"
        },
        {
            fieldname: "student_class",
            label: __("Class"),
            fieldtype: "Link",
            options: "Student Class"
        },
        {
            fieldname: "section",
            label: __("Section"),
            fieldtype: "Link",
            options: "Section"
        },
        {
            fieldname: "fees_structure",
            label: __("Fees Structure"),
            fieldtype: "Link",
            options: "Fees Structure"
        }
    ]
};
