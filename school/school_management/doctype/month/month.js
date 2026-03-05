// Copyright (c) 2026, Your Company and contributors
// For license information, please see license.txt

frappe.ui.form.on("Month", {

    // ------------------------------------------------------------------
    // Lifecycle hooks
    // ------------------------------------------------------------------

    refresh(frm) {
        update_summary(frm);
        add_select_all_button(frm);
        add_clear_all_button(frm);
        highlight_selected(frm);
    },

    // ------------------------------------------------------------------
    // React to every individual month checkbox changing
    // ------------------------------------------------------------------

    january:   (frm) => { on_month_change(frm); },
    february:  (frm) => { on_month_change(frm); },
    march:     (frm) => { on_month_change(frm); },
    april:     (frm) => { on_month_change(frm); },
    may:       (frm) => { on_month_change(frm); },
    june:      (frm) => { on_month_change(frm); },
    july:      (frm) => { on_month_change(frm); },
    august:    (frm) => { on_month_change(frm); },
    september: (frm) => { on_month_change(frm); },
    october:   (frm) => { on_month_change(frm); },
    november:  (frm) => { on_month_change(frm); },
    december:  (frm) => { on_month_change(frm); },
});


// ------------------------------------------------------------------
// Constants
// ------------------------------------------------------------------

const MONTH_FIELDS = [
    "january", "february", "march", "april",
    "may", "june", "july", "august",
    "september", "october", "november", "december"
];

const MONTH_LABELS = {
    january:   "January",
    february:  "February",
    march:     "March",
    april:     "April",
    may:       "May",
    june:      "June",
    july:      "July",
    august:    "August",
    september: "September",
    october:   "October",
    november:  "November",
    december:  "December",
};


// ------------------------------------------------------------------
// Core helpers
// ------------------------------------------------------------------

function get_selected_months(frm) {
    return MONTH_FIELDS.filter(f => frm.doc[f] === 1);
}

function on_month_change(frm) {
    update_summary(frm);
    highlight_selected(frm);
}

function update_summary(frm) {
    const selected = get_selected_months(frm);
    const labels   = selected.map(f => MONTH_LABELS[f]);

    // Update read-only display fields immediately in the UI
    frm.set_value("total_months_selected", selected.length);
    frm.set_value(
        "selected_months_display",
        labels.length ? labels.join(", ") : "None"
    );

    // Refresh the display fields so they repaint without a full save
    frm.refresh_field("total_months_selected");
    frm.refresh_field("selected_months_display");
}

/**
 * Visually highlight checked month labels with a soft green background
 * so the user can instantly see which months are active.
 */
function highlight_selected(frm) {
    MONTH_FIELDS.forEach(field => {
        const $wrapper = frm.fields_dict[field]
            && frm.fields_dict[field].$wrapper;
        if (!$wrapper) return;

        if (frm.doc[field]) {
            $wrapper.css({ "background": "#e6f4ea", "border-radius": "4px", "padding": "2px 6px" });
        } else {
            $wrapper.css({ "background": "", "border-radius": "", "padding": "" });
        }
    });
}


// ------------------------------------------------------------------
// Toolbar buttons
// ------------------------------------------------------------------

function add_select_all_button(frm) {
    if (frm.doc.docstatus !== 0) return; // only on editable docs

    frm.add_custom_button(__("Select All Months"), () => {
        MONTH_FIELDS.forEach(f => frm.set_value(f, 1));
        on_month_change(frm);
        frappe.show_alert({ message: __("All 12 months selected"), indicator: "green" });
    }, __("Actions"));
}

function add_clear_all_button(frm) {
    if (frm.doc.docstatus !== 0) return;

    frm.add_custom_button(__("Clear All Months"), () => {
        MONTH_FIELDS.forEach(f => frm.set_value(f, 0));
        on_month_change(frm);
        frappe.show_alert({ message: __("All months cleared"), indicator: "orange" });
    }, __("Actions"));
}