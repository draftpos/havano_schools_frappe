import frappe

def run():
    settings = frappe.get_doc("School Settings")
    print("PRIMARY COMMENTS:")
    for row in getattr(settings, "primary_admin_comments", []):
        print(f" - {row.comment_type}: {row.comment}")
    
    print("\nO LEVEL COMMENTS:")
    for row in getattr(settings, "o_level_admin_comments", []):
        print(f" - {row.comment_type}: {row.comment}")
        
    print("\nA LEVEL COMMENTS:")
    for row in getattr(settings, "a_level_admin_comments", []):
        print(f" - {row.comment_type}: {row.comment}")
