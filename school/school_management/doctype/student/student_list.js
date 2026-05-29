// Copyright (c) 2026, Ashley and contributors
// For license information, please see license.txt

frappe.listview_settings['Student'] = {
	onload: function(listview) {
		// By default, only show active students in the list view
		frappe.route_options = {
			"transfer_status": "Active"
		};
	},
	get_indicator: function(doc) {
		if (doc.transfer_status === "Transferred") {
			return [__("Transferred"), "red", "transfer_status,=,Transferred"];
		} else if (doc.transfer_status === "Inactive") {
			return [__("Inactive"), "orange", "transfer_status,=,Inactive"];
		} else {
			return [__("Active"), "green", "transfer_status,=,Active"];
		}
	}
};
