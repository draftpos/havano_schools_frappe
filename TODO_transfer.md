# TODO: Implement Student Transfer Synchronization

## Task
Make Student and Student Transfer doctypes communicate:
- When transfer_status in Student is changed to "Transferred" or "Inactive" → create Student Transfer record automatically
- When change back to "Active" → handle the reversal

## Implementation Plan:

### 1. Modify student.py
Add logic in `on_update` method to:
- Detect transfer_status changes using `has_value_changed("transfer_status")`
- When status changes to "Transferred" or "Inactive":
  - Create Student Transfer record automatically
  - Clear class and section fields
- When status changes to "Active":
  - Handle any necessary cleanup

### 2. Test the implementation
- Change status in Student doctype
- Verify Student Transfer is created
- Verify class/section are cleared
- Cancel the Student Transfer and verify status reverts
