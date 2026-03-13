frappe.ui.form.on("Receipting", {
    student_name(frm) {
        if (frm.doc.student_name) {
            frappe.call({
                method: "school.api.get_student_invoices",
                args: { student: frm.doc.student_name },
                callback: function(r) {
                    if (r.message) {
                        frm.clear_table("invoice");
                        let total_out = 0;
                        r.message.forEach(inv => {
                            let row = frm.add_child("invoice");
                            row.invoice_number = inv.name;
                            row.outstanding = inv.outstanding_amount;
                            total_out += flt(inv.outstanding_amount);
                        });
                        frm.set_value("total_outstanding", total_out);
                        frm.refresh_field("invoice");
                        calculate_totals(frm);
                    }
                }
            });
        }
    }
});

frappe.ui.form.on("Receipt Item", {
    allocated(frm) {
        calculate_totals(frm);
    },
    invoice_remove(frm) {
        calculate_totals(frm);
    }
});

function calculate_totals(frm) {
    let allocated = 0;
    (frm.doc.invoice || []).forEach(row => {
        allocated += flt(row.allocated);
    });
    frm.set_value("total_allocated", allocated);
    frm.set_value("total_balance", flt(frm.doc.total_outstanding) - allocated);
}