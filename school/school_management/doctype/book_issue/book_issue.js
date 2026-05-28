frappe.ui.form.on('Book Issue', {
	book_title: function(frm) {
		if (frm.doc.book_title) {
			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'Books',
					name: frm.doc.book_title
				},
				callback: function(r) {
					if (r.message && r.message.items) {
						let options = r.message.items.map(i => i.book_number).filter(Boolean);
						frm.set_df_property('book_number', 'options', options);
					}
				}
			});
		} else {
			frm.set_df_property('book_number', 'options', []);
			frm.set_value('book_number', '');
		}
	}
});
