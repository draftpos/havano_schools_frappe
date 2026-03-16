frappe.pages['admin-school-managem'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'School Management Dashboard',
		single_column: true
	});
	$(wrapper).find('.page-head').hide();
	var csrf = frappe.csrf_token;
	var url = '/assets/school/html/admin_school_management.html?csrf=' + encodeURIComponent(csrf);
	$(page.body).html('<iframe src="' + url + '" style="width:100%;height:100vh;border:none;display:block;margin:0;padding:0;" frameborder="0"></iframe>');
}
