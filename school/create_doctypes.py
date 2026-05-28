import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def create_doctypes():
    frappe.flags.in_install = True

    # 1. Create 'Book Copy' Child Table
    if not frappe.db.exists("DocType", "Book Copy"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "Book Copy",
            "module": "School Management",
            "custom": 1,
            "istable": 1,
            "fields": [
                {"fieldname": "book_number", "label": "Book Number", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
                {"fieldname": "book_title", "label": "Book Title", "fieldtype": "Data", "read_only": 1, "in_list_view": 1, "fetch_from": "parent.book_title"}
            ]
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print("Created Book Copy DocType")

    # 2. Create 'Books' Parent DocType
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
                {"fieldname": "year", "label": "Year", "fieldtype": "Int"},
                {"fieldname": "count", "label": "Count (Available)", "fieldtype": "Int", "read_only": 1},
                {"fieldname": "copies_section", "label": "Copies", "fieldtype": "Section Break"},
                {"fieldname": "copies", "label": "Copies", "fieldtype": "Table", "options": "Book Copy"}
            ]
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print("Created Books DocType")

    # 3. Create 'Book Issue' DocType
    if not frappe.db.exists("DocType", "Book Issue"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "Book Issue",
            "module": "School Management",
            "custom": 1,
            "autoname": "naming_series:",
            "fields": [
                {"fieldname": "naming_series", "label": "Series", "fieldtype": "Select", "options": "B-ISSUE-.YYYY.-", "default": "B-ISSUE-.YYYY.-", "reqd": 1, "hidden": 1},
                {"fieldname": "date", "label": "Issue Date", "fieldtype": "Date", "default": "Today", "reqd": 1},
                {"fieldname": "librarian", "label": "Librarian", "fieldtype": "Link", "options": "User", "default": "Administrator"},
                {"fieldname": "student", "label": "Student", "fieldtype": "Link", "options": "Student", "reqd": 1, "in_list_view": 1},
                {"fieldname": "book_title", "label": "Book Title", "fieldtype": "Link", "options": "Books", "reqd": 1, "in_list_view": 1},
                {"fieldname": "book_number", "label": "Book Number", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
                {"fieldname": "return_date", "label": "Expected Return Date", "fieldtype": "Date"},
                {"fieldname": "status", "label": "Status", "fieldtype": "Select", "options": "Pending Return\nReturned\nOverdue\nLost", "default": "Pending Return", "reqd": 1, "in_list_view": 1}
            ]
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print("Created Book Issue DocType")
    else:
        print("Book Issue already exists")

