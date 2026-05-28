import frappe

def create():
    
    # 1. Book Item (Child Table)
    if not frappe.db.exists("DocType", "Book Item"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "Book Item",
            "module": "School Management",
            "istable": 1,
            "custom": 1,
            "fields": [
                {"fieldname": "book_number", "label": "Book Number", "fieldtype": "Data", "in_list_view": 1},
                {"fieldname": "book_title", "label": "Book Title", "fieldtype": "Data", "in_list_view": 1, "read_only": 1, "fetch_from": "parent.book_title"}
            ]
        })
        doc.insert(ignore_permissions=True)
        print("Created Book Item")
    else:
        print("Book Item already exists")
    
    # 2. Books
    if not frappe.db.exists("DocType", "Books"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "Books",
            "module": "School Management",
            "custom": 1,
            "autoname": "field:book_title",
            "fields": [
                {"fieldname": "book_title", "label": "Book Title", "fieldtype": "Data", "reqd": 1, "unique": 1},
                {"fieldname": "subject", "label": "Subject", "fieldtype": "Link", "options": "Subject"},
                {"fieldname": "author", "label": "Author", "fieldtype": "Data"},
                {"fieldname": "publisher", "label": "Publisher", "fieldtype": "Data"},
                {"fieldname": "year", "label": "Year", "fieldtype": "Data"},
                {"fieldname": "count", "label": "Count", "fieldtype": "Int"},
                {"fieldname": "items", "label": "Book Items", "fieldtype": "Table", "options": "Book Item"}
            ]
        })
        doc.insert(ignore_permissions=True)
        print("Created Books")
    else:
        print("Books already exists")

    # 3. Book Issue
    if not frappe.db.exists("DocType", "Book Issue"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "Book Issue",
            "module": "School Management",
            "custom": 1,
            "is_submittable": 0,
            "fields": [
                {"fieldname": "date", "label": "Date", "fieldtype": "Date", "reqd": 1, "default": "Today"},
                {"fieldname": "librarian", "label": "Librarian", "fieldtype": "Link", "options": "User", "default": "Administrator"},
                {"fieldname": "student", "label": "Student", "fieldtype": "Link", "options": "Student", "reqd": 1, "in_list_view": 1},
                {"fieldname": "book_title", "label": "Book Title", "fieldtype": "Link", "options": "Books", "reqd": 1, "in_list_view": 1},
                {"fieldname": "return_date", "label": "Return Date", "fieldtype": "Date"},
                {"fieldname": "status", "label": "Status", "fieldtype": "Select", "options": "Pending Return\nReturned\nOverdue\nLost", "default": "Pending Return", "in_list_view": 1}
            ]
        })
        doc.insert(ignore_permissions=True)
        print("Created Book Issue")
    else:
        print("Book Issue already exists")

    frappe.db.commit()

create()
