# Copyright (c) 2026, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


MONTH_FIELDS = [
    "january", "february", "march", "april",
    "may", "june", "july", "august",
    "september", "october", "november", "december"
]

MONTH_LABELS = {
    "january":   "January",
    "february":  "February",
    "march":     "March",
    "april":     "April",
    "may":       "May",
    "june":      "June",
    "july":      "July",
    "august":    "August",
    "september": "September",
    "october":   "October",
    "november":  "November",
    "december":  "December",
}


class Month(Document):

    def validate(self):
        self._update_selected_months_summary()

    def before_save(self):
        self._update_selected_months_summary()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_selected_month_labels(self):
        """Return an ordered list of label strings for every checked month."""
        return [
            MONTH_LABELS[field]
            for field in MONTH_FIELDS
            if self.get(field)
        ]

    def _update_selected_months_summary(self):
        """Populate the read-only summary fields."""
        selected = self._get_selected_month_labels()
        self.selected_months_display = ", ".join(selected) if selected else "None"
        self.total_months_selected = len(selected)

    # ------------------------------------------------------------------
    # Public API (callable via frappe.call / whitelisted)
    # ------------------------------------------------------------------

    @frappe.whitelist()
    def get_selected_months(self):
        """
        Returns a list of selected month label strings.

        Usage from client:
            frappe.call({
                method: 'frappe.client.get',
                args: { doctype: 'Month', name: frm.doc.name },
                callback(r) { ... }
            });
        Or via server:
            doc = frappe.get_doc('Month', name)
            months = doc.get_selected_months()
        """
        self._update_selected_months_summary()
        return self._get_selected_month_labels()


# ------------------------------------------------------------------
# Standalone whitelisted helper — usable without a document instance
# ------------------------------------------------------------------

@frappe.whitelist()
def get_months_for_record(name):
    """
    Convenience function: given a Month document name, return the
    list of selected month labels.

    Client usage:
        frappe.call({
            method: 'school_management.school_management.doctype.month.month.get_months_for_record',
            args: { name: 'MON-0001' },
            callback(r) { console.log(r.message); }
        });
    """
    doc = frappe.get_doc("Month", name)
    return doc.get_selected_months()