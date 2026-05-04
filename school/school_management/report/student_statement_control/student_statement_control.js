frappe.query_reports["Student Statement Control"] = {
    filters: [
        {fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company")},
        {fieldname: "report_date", label: __("Report Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today()},
        {fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.month_start()},
        {fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today()},
        {fieldname: "customer", label: __("Student"), fieldtype: "Link", options: "Customer"},
        {fieldname: "customer_group", label: __("Customer Group"), fieldtype: "Link", options: "Customer Group"},
        {fieldname: "section", label: __("Section"), fieldtype: "Data"},
        {fieldname: "student_class", label: __("Class"), fieldtype: "Data"},
    ],
    onload(report) {
        report.page.add_inner_button(__("Bulk Download ZIP"), async () => {
            await cs_bulk_action(report, "school.school_management.api.download_student_statements_zip");
        });
        report.page.add_inner_button(__("Bulk Print PDF"), async () => {
            await cs_bulk_action(report, "school.school_management.api.download_student_statements_merged_pdf");
        });
        report.page.add_inner_button(__("Open Single Student Statement"), async () => {
            const f = report.get_values();
            if (!f.customer) { frappe.msgprint(__("Select a Student filter first.")); return; }
            frappe.set_route("query-report", "Student Statement Detail", {
                company: f.company, customer: f.customer,
                from_date: f.from_date, to_date: f.to_date, report_date: f.report_date,
            });
        });
    },
};
async function cs_bulk_action(report, method) {
    const filters = report.get_values();
    frappe.dom.freeze(__("Preparing statements..."));
    try {
        const cr = await frappe.call({method: "school.school_management.api.get_batch_student_count", args: {filters}});
        const count = (cr.message || {}).count || 0;
        if (!count) { frappe.msgprint(__("No students matched the selected filters.")); return; }
        const r = await frappe.call({method, args: {filters}});
        const p = r.message || {};
        if (p.file_url) { window.open(p.file_url, "_blank"); }
        else { frappe.msgprint(__("No download URL was returned.")); }
    } finally { frappe.dom.unfreeze(); }
}
