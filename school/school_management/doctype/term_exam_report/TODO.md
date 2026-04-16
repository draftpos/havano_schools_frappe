# Task Progress: Fix comments in exam schedule to term exam report

## Completed:
- [x] Step 1: Remove admin_comment from term_exam_result_item.json  
- [x] Step 2: Remove admin_comment from exam_schedule_item.json
- [x] Step 3: Implement teacher_comment passing from exam_schedule_item to term_exam_result_item during fetch_results
- [x] Step 4: Add overall admin_comment field to term_exam_report parent doctype
- [x] Step 5: Update HTML report to display teacher_comments per subject and overall admin_comment
- [x] Step 6: Update get_student_reports to include teacher_comment

## Remaining:
- [ ] Step 7: Run bench migrate and test
