import frappe

def create_doctype():
    if not frappe.db.exists("DocType", "Library"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "module": "School Management",
            "name": "Library",
            "custom": 0,
            "beta": 0,
            "fields": [
                {
                    "fieldname": "title",
                    "fieldtype": "Data",
                    "label": "Title",
                    "reqd": 1,
                    "in_list_view": 1
                },
                {
                    "fieldname": "author",
                    "fieldtype": "Data",
                    "label": "Author",
                    "in_list_view": 1
                },
                {
                    "fieldname": "year_published",
                    "fieldtype": "Data",
                    "label": "Year Published",
                    "in_list_view": 1
                },
                {
                    "fieldname": "book_file",
                    "fieldtype": "Attach",
                    "label": "Book File"
                },
                {
                    "fieldname": "link",
                    "fieldtype": "Data",
                    "label": "Link",
                    "options": "URL"
                },
                {
                    "fieldname": "description",
                    "fieldtype": "Small Text",
                    "label": "Description"
                }
            ],
            "permissions": [
                {
                    "role": "System Manager",
                    "read": 1,
                    "write": 1,
                    "create": 1,
                    "delete": 1,
                    "export": 1
                },
                {
                    "role": "School Administrator",
                    "read": 1,
                    "write": 1,
                    "create": 1,
                    "delete": 1,
                    "export": 1
                }
            ],
            "naming_rule": "Expression",
            "autoname": "format:LIB-{title}-{####}",
            "title_field": "title",
            "search_fields": "title,author"
        })
        doc.insert()
        frappe.db.commit()
        print("Library Doctype created successfully.")
    else:
        print("Library Doctype already exists.")
