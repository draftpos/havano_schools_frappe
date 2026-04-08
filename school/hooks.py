app_name = "school"
app_title = "School Management"
app_publisher = "Havano"
app_description = "Customized school management application"
app_email = "nyashagumbo0@gmail.com"
app_license = "mit"
fixtures = [
    {
        "dt": "Client Script",
        "filters": [["dt", "in", ["Student", "Test Schedule", "Home Schedule", "Receipting", "Promote", "Student ID Card", "Sales Invoice", "Payment Entry"]]]
    },
    {
        "dt": "Server Script",
        "filters": [["name", "in", [
            "Sales Order Auto Payment Entry",
            "Create Payment Entry from Receipting",
            "Calculate Student Count",
            "Fetch Students for ID Card",
            "Fetch Students for Promote",
            "Apply Student Promotion",
            "Calculate Home Schedule Student Count",
            "Fetch Attendance Summary",
            "Create Student Portal User",
            "Auto Create Class Result",
            "Auto Submit Receipting",
            "Send Student Portal Credentials",
            "Student Opening Balance Journal Entry",
            "School Permission - Billing",
            "School Permission - Student",
            "School Permission - Receipting",
            "School Permission - Sales Invoice",
            "School Permission - Payment Entry",
            "School Permission - Purchase Invoice",
            "School Permission - Sales Order",
            "School Permission - Journal Entry",
            "Filter Test Schedule Portal"
        ]]]
    },
    {
        "dt": "Custom Field",
        "filters": [
            ["fieldname", "in", [
                "student_class", "student_section", "student_category", 
                "academic_year", "academic_term", "fees_structure", 
                "billing_reference", "school", "school_cost_center"
            ]]
        ]
    },
    {
        "dt": "Role",
        "filters": [["role_name", "in", ["Student", "Student Portal", "School User"]]]
    },
    {
        "dt": "Custom DocPerm",
        "filters": [["role", "in", ["School User", "Student Portal"]]]
    },
    {
        "dt": "DocType",
        "filters": [["name", "in", ["HA POS Settings", "Ha User Mapping"]]]
    }
]
doc_events = {
    "DocType": {
        "after_save": "school.utils.export_doctype_on_save"
    },
    "Client Script": {
        "after_save": "school.utils.export_client_script_on_save"
    },
    "Server Script": {
        "after_save": "school.utils.export_server_script_on_save"
    }
}
on_login = "school.utils.redirect_to_portal"
app_include_js = [
    '/assets/school/js/school_redirect.js'
]
# Fixtures for synchronization
