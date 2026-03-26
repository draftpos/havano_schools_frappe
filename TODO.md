# Billing Status Filter and School Settings Tables Implementation

## TODO Steps:

### 1. Create new Child DocType 'Student Status Fee Mapping' (similar to Fee Structure Defaults)
   - Create school/school_management/doctype/student_status_fee_mapping/__init__.py
   - Create school/school_management/doctype/student_status_fee_mapping/student_status_fee_mapping.json (fields: status Select(Day,Boarding), fees_structure Link(Fees Structure))
   - Create school/school_management/doctype/student_status_fee_mapping/student_status_fee_mapping.py (empty class)

### 2. Update school_settings.json
   - Add new Section Break if needed
   - Add Table field 'student_status_fee_mappings' options='Student Status Fee Mapping'

### 3. Update billing.json
   - Add field 'status' (Select: Day\nBoarding) after 'col_break_4'
   - Update field_order to include 'status'

### 4. Update billing.py
   - In get_student_filters(): if self.status: filters['student_status'] = self.status (add student_status filter)

### 5. Add Client Scripts (school/fixtures/client_script.json)
   - For School Settings: on student_status_fee_mappings-add/update, auto-set fees_structure based on status if predefined.
   - For Billing: on status change, fetch fees_structure from School Settings mapping and set.

### 6. [Pending] Verify/add student_status field to Student doctype if missing
   - Check Student.json, add if needed

### 7. bench migrate && bench clear-cache
### 8. Test: School Settings add status mapping, Billing filter by status, auto fees_structure



### 1. [✅ Complete] Create new Child DocType 'Student Status Fee Mapping'...
### 2. [✅ Complete] Update school_settings.json
### 3. [✅ Complete] Update billing.json
### 4. [✅ Complete] Update billing.py


