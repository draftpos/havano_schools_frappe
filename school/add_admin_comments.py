import frappe

def create_admin_comments():
    frappe.flags.in_install = True

    # 1. Create the 3 Child Table DocTypes
    primary_options = "\n".join([
        "Excellent (80% and above)",
        "Good (60% to 79%)",
        "Moderate (50% to 59%)",
        "Failed (Below 50%)"
    ])

    o_level_options = "\n".join([
        "10 As & Above",
        "9 As",
        "7 As - 8 As",
        "5 Subjects & Above with 4 As",
        "5 Subjects Passed with 3 As",
        "5 Subjects Passed with 1A - 2As",
        "5 Subjects Passed without As",
        "Less than 4 Subjects Passed",
        "0 Subjects Passed"
    ])

    a_level_options = "\n".join([
        "15+ points",
        "14 points",
        "12 - 13 points",
        "10 - 11 points",
        "8 - 9 points",
        "6 - 7 points",
        "4 - 5 points",
        "0 - 3 points"
    ])

    doctypes_to_create = [
        ("Admin Comment Primary", primary_options),
        ("Admin Comment O Level", o_level_options),
        ("Admin Comment A Level", a_level_options)
    ]

    for dt_name, options in doctypes_to_create:
        if not frappe.db.exists("DocType", dt_name):
            doc = frappe.get_doc({
                "doctype": "DocType",
                "name": dt_name,
                "module": "School Management",
                "custom": 0,
                "istable": 1,
                "editable_grid": 1,
                "fields": [
                    {"fieldname": "comment_type", "label": "Type of Comment", "fieldtype": "Select", "options": options, "reqd": 1, "in_list_view": 1},
                    {"fieldname": "comment", "label": "Comment", "fieldtype": "Small Text", "reqd": 1, "in_list_view": 1}
                ]
            })
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            print(f"Created {dt_name} DocType")
        else:
            # Update options just in case
            dt_doc = frappe.get_doc("DocType", dt_name)
            for f in dt_doc.fields:
                if f.fieldname == "comment_type":
                    f.options = options
            dt_doc.save(ignore_permissions=True)
            frappe.db.commit()

    # 2. Update School Settings DocType
    school_settings_dt = frappe.get_doc("DocType", "School Settings")
    
    # Remove old fields if present
    fields_to_keep = []
    for f in school_settings_dt.fields:
        if f.fieldname not in ["admin_comments_section", "admin_comment_settings", "primary_admin_comments", "o_level_admin_comments", "a_level_admin_comments"]:
            fields_to_keep.append(f)
            
    school_settings_dt.fields = fields_to_keep
    
    # Append the new structure
    school_settings_dt.append("fields", {
        "fieldname": "admin_comments_section",
        "fieldtype": "Section Break",
        "label": "Admin Comments (Auto)"
    })
    school_settings_dt.append("fields", {
        "fieldname": "primary_admin_comments",
        "fieldtype": "Table",
        "label": "Primary Admin Comments",
        "options": "Admin Comment Primary"
    })
    school_settings_dt.append("fields", {
        "fieldname": "o_level_admin_comments",
        "fieldtype": "Table",
        "label": "O Level Admin Comments",
        "options": "Admin Comment O Level"
    })
    school_settings_dt.append("fields", {
        "fieldname": "a_level_admin_comments",
        "fieldtype": "Table",
        "label": "A Level Admin Comments",
        "options": "Admin Comment A Level"
    })
    
    school_settings_dt.save(ignore_permissions=True)
    frappe.db.commit()
    print("Updated School Settings DocType structure")

    # 3. Seed Default Data into School Settings instance
    settings_instance = frappe.get_doc("School Settings")
    
    # Clear existing
    settings_instance.set("primary_admin_comments", [])
    settings_instance.set("o_level_admin_comments", [])
    settings_instance.set("a_level_admin_comments", [])
    
    primary_defaults = [
        ("Excellent (80% and above)", "Excellent performance! Keep up the brilliant work."),
        ("Good (60% to 79%)", "Very good progress. With a bit more effort, you can reach the top."),
        ("Moderate (50% to 59%)", "Satisfactory result, but there is room for improvement."),
        ("Failed (Below 50%)", "Needs extra support and more focus. Please put in more effort next term.")
    ]
    for ctype, cmt in primary_defaults:
        settings_instance.append("primary_admin_comments", {
            "comment_type": ctype,
            "comment": cmt
        })
        
    o_level_defaults = [
        ("10 As & Above", "Excellent work. Maintain this high standard. Aim to achieve A+ in every subject.\nConsult your teachers and other students, and make use of previous exam papers."),
        ("9 As", "A hardworking student. Keep up the good work. Aim to get an A in every subject.\nConsult your teachers and other students, and make use of previous exam papers."),
        ("7 As - 8 As", "A conscientious student with the potential to do better.\nConsult your teachers and other students, and make use of previous exam papers."),
        ("5 Subjects & Above with 4 As", "Satisfactory work, but you need to put more effort in all subjects.\nConsult your teachers and other students, and make use of previous exam papers."),
        ("5 Subjects Passed with 3 As", "This is a weak pass. We expect better grades from you.\nConsult your teachers and other students, and make use of previous exam papers."),
        ("5 Subjects Passed with 1A - 2As", "This is a weak pass. We expect you to work harder.\nConsult your teachers and other students, and make use of previous exam papers."),
        ("5 Subjects Passed without As", "This is a weak pass. You are expected to work harder. Time is running out.\nConsult your teachers and other students, and make use of previous exam papers."),
        ("Less than 4 Subjects Passed", "Watch out, time is not on your side. Concentrate on your school work.\nConsult your teachers and other students, and participate in class."),
        ("0 Subjects Passed", "A very disappointing end of term report. Please be more serious and understand why you are here.\nConsult your teachers and other students, and make use of previous exam papers.\nParticipate in class and think about your future.")
    ]
    for ctype, cmt in o_level_defaults:
        settings_instance.append("o_level_admin_comments", {
            "comment_type": ctype,
            "comment": cmt
        })

    a_level_defaults = [
        ("15+ points", "Excellent work. Maintain this high standard. Aim to achieve 3A*s.\nConsult your teachers and other students, and make use of previous exam papers."),
        ("14 points", "A hardworking student. Work on weak areas. Aim for 15 points.\nConsult your teachers and other students, and make use of previous exam papers."),
        ("12 - 13 points", "Hardworking student. Aim to get 15 points / 3 A's.\nConsult your teachers and other students, and make use of previous exam papers."),
        ("10 - 11 points", "Satisfactory work, but improve in all subjects to get better grades. Aim for 15 points.\nConsult your teachers and other students, and make use of previous exam papers."),
        ("8 - 9 points", "This is a weak pass. You should work harder in all subjects.\nConsult your teachers and other students, and make use of previous exam papers."),
        ("6 - 7 points", "This is a very weak pass. Put more effort in every subject.\nConsult your teachers and other students, and make use of previous exam papers."),
        ("4 - 5 points", "A very disappointing end of term report. Please put in more effort.\nConsult your teachers and other students, and make use of previous exam papers."),
        ("0 - 3 points", "A very disappointing end of term. Understand why you are here. Participate in class.\nConsult your teachers and other students, and make use of previous exam papers.")
    ]
    for ctype, cmt in a_level_defaults:
        settings_instance.append("a_level_admin_comments", {
            "comment_type": ctype,
            "comment": cmt
        })
        
    settings_instance.save(ignore_permissions=True)
    frappe.db.commit()
    print("Seeded default comments to School Settings")

if __name__ == "__main__":
    frappe.init(site="v15.local")
    frappe.connect()
    create_admin_comments()
