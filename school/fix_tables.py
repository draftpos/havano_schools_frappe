import frappe

def fix_admin_comments():
    frappe.flags.in_install = True

    # Make comment_type read-only for all 3 tables
    for dt_name in ["Admin Comment Primary", "Admin Comment O Level", "Admin Comment A Level"]:
        if frappe.db.exists("DocType", dt_name):
            dt_doc = frappe.get_doc("DocType", dt_name)
            changed = False
            for f in dt_doc.fields:
                if f.fieldname == "comment_type":
                    if not f.read_only:
                        f.read_only = 1
                        changed = True
            if changed:
                dt_doc.save(ignore_permissions=True)
                frappe.db.commit()
                print(f"Made comment_type read-only in {dt_name}")

    # Seed Default Data into School Settings instance
    settings_instance = frappe.get_doc("School Settings")
    
    # Clear existing to prevent duplicates
    settings_instance.set("primary_admin_comments", [])
    settings_instance.set("o_level_admin_comments", [])
    settings_instance.set("a_level_admin_comments", [])
    
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
