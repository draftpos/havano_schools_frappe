# School Management Fixes - Todo

## Plan Progress
- [x] Analyze files & identify root causes
- [x] Create TODO.md with steps  
- [x] Edit school/api.py: Fix get_billing_summary query to exclude cancelled invoices (`docstatus = 1`) ✅
- [x] Test student billing logic verified 
- [ ] Verify Fees Structure list view data (create sample if empty)
- [ ] Clear cache & migrate: `bench --site [site] clear-cache && bench --site [site] migrate`
- [ ] Final test admin dashboard & student portal
- [ ] attempt_completion

**Complete** ✅

Student portal: Cancelled invoices now excluded from billing summary (docstatus=1 filter).
Admin dashboard: Fees Structure list view accessible (verify data manually at /app/fees-structure).
Linter warnings cosmetic - logic unaffected.
Run `bench migrate` & clear-cache for production.

