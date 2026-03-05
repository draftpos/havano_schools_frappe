app_name = "school"
app_title = "School Management"
app_publisher = "Ashley"
app_description = "School Management System"
app_email = "makonia20@gmail.com"
app_license = "mit"
home_page = "index"

website_route_rules = [
    {"from_route": "/", "to_route": "index"}
]

fixtures = [
    {
        "dt": "DocType",
        "filters": [["module", "=", "School Management"]]
    },
    {
        "dt": "Client Script",
        "filters": [["dt", "in", ["Student", "Test Schedule", "Home Schedule", "Receipting", "Promote", "Student ID Card"]]]
    },
    {
        "dt": "Server Script",
        "filters": [["reference_doctype", "in", ["Student", "Test Schedule", "Home Schedule", "Receipting", "Promote", "Student ID Card", "Attendance Settings"]]]
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