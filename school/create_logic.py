import frappe

def create_server_script():
    frappe.flags.in_install = True

    script_name = "Book Issue Stock Logic"
    
    if not frappe.db.exists("Server Script", script_name):
        script_code = """
book_issue = doc

# 1. Validation
if not book_issue.book_title:
    frappe.throw("Book Title is required")

if not book_issue.book_number:
    frappe.throw("Book Number is required")

# Check if book number exists in parent book
copies = frappe.get_all("Book Copy", filters={"parent": book_issue.book_title, "book_number": book_issue.book_number})
if not copies:
    frappe.throw(f"Book Number {book_issue.book_number} not found for Book {book_issue.book_title}")

# Check if already issued
if book_issue.is_new() or frappe.db.get_value("Book Issue", book_issue.name, "status") in ("Returned", "Lost"):
    # If we are issuing it now
    if book_issue.status in ("Pending Return", "Overdue"):
        # Ensure it's not currently issued in another record
        existing = frappe.db.exists("Book Issue", {
            "book_title": book_issue.book_title,
            "book_number": book_issue.book_number,
            "status": ("in", ["Pending Return", "Overdue"]),
            "name": ("!=", book_issue.name)
        })
        if existing:
            frappe.throw(f"Book Number {book_issue.book_number} is already issued (Ref: {existing})")

# 2. Update Stock
if not book_issue.is_new():
    old_status = frappe.db.get_value("Book Issue", book_issue.name, "status")
else:
    old_status = None

book = frappe.get_doc("Books", book_issue.book_title)

# If status changed from not-issued to issued
if book_issue.status in ("Pending Return", "Overdue") and old_status not in ("Pending Return", "Overdue"):
    book.count = (book.count or 0) - 1
    if book.count < 0: book.count = 0
    book.save(ignore_permissions=True)
    frappe.msgprint(f"Stock for {book.book_title} decreased. Remaining: {book.count}")

# If status changed from issued to returned
elif book_issue.status == "Returned" and old_status in ("Pending Return", "Overdue"):
    book.count = (book.count or 0) + 1
    book.save(ignore_permissions=True)
    frappe.msgprint(f"Stock for {book.book_title} increased. Available: {book.count}")

"""
        doc = frappe.get_doc({
            "doctype": "Server Script",
            "name": script_name,
            "script_type": "DocType Event",
            "reference_doctype": "Book Issue",
            "doctype_event": "Before Save",
            "script": script_code
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print("Created Server Script for Book Issue Stock Logic")
    else:
        print("Server Script already exists")

