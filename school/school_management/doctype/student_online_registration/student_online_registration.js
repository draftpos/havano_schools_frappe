frappe.ui.form.on('Student Online Registration', {
    refresh: function(frm) {
        // Show approve/reject buttons for pending registrations
        if (frm.doc.enrollment_status === 'Pending') {
            frm.add_custom_button(__('Approve'), function() {
                frappe.prompt([
                    {
                        fieldname: 'section',
                        label: 'Select Section',
                        fieldtype: 'Link',
                        options: 'Section',
                        reqd: 1,
                        get_query: function() {
                            return {
                                filters: {
                                    'cost_center': frm.doc.school
                                }
                            };
                        }
                    }
                ], function(values) {
                    frm.set_value('approved_section', values.section);
                    frm.set_value('enrollment_status', 'Approved');
                    frm.save();
                }, __('Approve Registration'), __('Approve'));
            });
            
            frm.add_custom_button(__('Reject'), function() {
                frappe.prompt([
                    {
                        fieldname: 'remarks',
                        label: 'Rejection Reason',
                        fieldtype: 'Small Text',
                        reqd: 1
                    }
                ], function(values) {
                    frm.set_value('enrollment_status', 'Rejected');
                    frm.set_value('approval_remarks', values.remarks);
                    frm.save();
                }, __('Reject Registration'), __('Reject'));
            });
        }
        
        // Show View Student button if student was created
        if (frm.doc.student_created && frm.doc.created_student) {
            frm.add_custom_button(__('View Student'), function() {
                frappe.set_route('Form', 'Student', frm.doc.created_student);
            });
        }
        
        // Show message if approved but no section selected
        if (frm.doc.enrollment_status === 'Approved' && !frm.doc.approved_section) {
            frappe.msgprint({
                title: __('Section Required'),
                message: __('Please assign a section to this student.'),
                indicator: 'orange'
            });
        }
    },
    
    student_class: function(frm) {
        // Suggest sections based on selected class
        if (frm.doc.student_class && frm.doc.school) {
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Section',
                    filters: {
                        'cost_center': frm.doc.school
                    },
                    fields: ['name']
                },
                callback: function(r) {
                    if (r.message && r.message.length) {
                        var sections = r.message.map(function(s) { return s.name; });
                        frm.set_df_property('requested_section', 'options', sections.join('\n'));
                    }
                }
            });
        }
    },
    
    school: function(frm) {
        // When school changes, reload class options
        if (frm.doc.school) {
            frappe.call({
                method: 'school.www.student_registration.get_classes_by_school',
                args: { school: frm.doc.school },
                callback: function(r) {
                    if (r.message && r.message.length) {
                        var classes = r.message.map(function(c) { return c.name; });
                        frm.set_df_property('student_class', 'options', classes.join('\n'));
                    }
                }
            });
            
            // Also load sections for this school
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Section',
                    filters: {
                        'cost_center': frm.doc.school
                    },
                    fields: ['name']
                },
                callback: function(r) {
                    if (r.message && r.message.length) {
                        var sections = r.message.map(function(s) { return s.name; });
                        frm.set_df_property('requested_section', 'options', sections.join('\n'));
                    }
                }
            });
        }
    },
    
    before_save: function(frm) {
        // Auto-set full name
        if (frm.doc.first_name && frm.doc.last_name) {
            var fullName = frm.doc.first_name;
            if (frm.doc.second_name) fullName += ' ' + frm.doc.second_name;
            fullName += ' ' + frm.doc.last_name;
            frm.set_value('full_name', fullName);
        }
    }
});