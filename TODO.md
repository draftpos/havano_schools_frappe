# Task Progress: Fix comments in exam schedule to term exam report

## Steps:
- [ ] Step 1: Remove admin_comment from term_exam_result_item.json
- [ ] Step 2: Remove admin_comment from exam_schedule_item.json  
- [ ] Step 3: Implement teacher_comment passing from exam_schedule_item to term_exam_result_item during fetch_results
- [ ] Step 4: Add overall admin_comment field to term_exam_report parent doctype
- [ ] Step 5: Update term_exam_report.py to copy teacher_comment and populate overall admin_comment if needed
- [ ] Step 6: Update HTML report to display teacher_comments per subject and overall admin comment
- [ ] Step 7: Run bench migrate and test

