# Login Portal Header - Separate Doctype Fix

**Status: Complete**

## Changes:
- Slides API/JS reverted (images work)
- **New**: Login Portal Header (Single doctype)
- **New**: school.api.get_portal_header() (fallback default)
- **New**: JS loadPortalHeader() (separate AJAX)

## To Fix/Use:
1. `cd /home/ashley/frappe-bench-v15 && bench migrate`
2. Login admin → Search "Login Portal Header" → Create (auto due Single) → Set `header_text` → Save
3. /portal-login → Check h2

If doctype not showing: `bench --site [site] console` → `frappe.delete_doc("DocType", "Login Portal Header", ignore_missing=True); frappe.reload_doc("School Management", "doctype", "login_portal_header")`

