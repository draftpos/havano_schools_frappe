# Receipting/Payment Entry Fix Task
Current working directory: //wsl.localhost/Ubuntu-24.04/home/ashley/frappe-bench-v15/apps/school

## Steps:
- [x] 1. Implement payment_entry_invoice.py: Auto-populate child table from Receipting (new + historical via reference_no).
- [x] 2. Update receipting.js: Clear invoice table post-submit.
- [x] 3. Enhance receipting.py: Add SI cancel on full payment; keep all existing.
- [ ] 4. Add PE client script for reference_no → load Receipting details into references.
- [ ] 5. Test: Create Receipting → check PE displays → full pay cancels SI → historical also shows.
- [ ] 6. bench migrate && bench clear-cache.
- [ ] 7. Mark COMPLETE.

Progress: Core fixes done (UI clear, full pay cancel). PE display via client script next.

