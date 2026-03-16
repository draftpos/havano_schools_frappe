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
        "filters": [["reference_doctype", "in", ["Student", "Test Schedule", "Home Schedule", "Receipting", "Promote", "Student ID Card", "Attendance Settings", "Billing", "Sales Invoice", "Payment Entry", "Purchase Invoice", "Sales Order", "Journal Entry"]]]
    },
    {
        "dt": "Custom Field",
        "filters": [["dt", "in", ["Sales Invoice", "Ha User Mapping"]]]
    },
    {
        "dt": "Role",
        "filters": [["role_name", "in", ["Student", "Student Portal", "School User"]]]
    },
    {
        "dt": "Custom DocPerm",
        "filters": [["role", "in", ["School User"]]]
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
fixtures = [
    {"dt": "Server Script", "filters": [["name", "in", ["Sales Order Auto Payment Entry"]]]},
    {"dt": "Client Script", "filters": [["dt", "in", ["Sales Order", "Receipting"]]]}
]
