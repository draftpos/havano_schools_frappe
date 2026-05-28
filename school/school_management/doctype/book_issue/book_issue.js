frappe.ui.form.on('Book Issue', {
	refresh: function(frm) {
		if (frm.doc.book_title) {
			frm.trigger('fetch_book_numbers');
		}
	},
	book_title: function(frm) {
		frm.set_value('book_number', '');
		if (frm.doc.book_title) {
			frm.trigger('fetch_book_numbers');
		} else {
			frm.set_df_property('book_number', 'options', '');
		}
	},
	fetch_book_numbers: function(frm) {
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'Books',
				name: frm.doc.book_title
			},
			callback: function(r) {
				if (r.message && r.message.items) {
					let options = r.message.items.map(i => i.book_number).filter(Boolean);
					frm.set_df_property('book_number', 'options', options.join('\n'));
				} else {
					frm.set_df_property('book_number', 'options', '');
				}
			}
		});
	}
});
