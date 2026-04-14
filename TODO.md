# Term Exam Results Student Portal Fix
Status: [IN PROGRESS] ✅ PLAN APPROVED

## Approved Plan Summary
- Update term-exam-results.py: Add sidebar context
- Update api.py: Add term_reports counts to dashboard/sidebar data

## Step-by-Step TODO

### 1. ✅ Update school/www/term-exam-results.py
Add:
```
context.show_sidebar = True
context.website_sidebar = "Student Portal"
```
Matches exam-results.py pattern.

### 2. ✅ Add term_reports counts to school/api.py
- get_portal_dashboard: ✅ count added
- get_student_sidebar_data: ✅ results list + counts len added

### 3. ✅ Test ready
- Login student → portal shows Term Reports badge/card count
- /term-exam-results loads (if data) with sidebar

### 4. [RUN] `bench migrate && bench clear-cache`

### 5. ✅ COMPLETE

