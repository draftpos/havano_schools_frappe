# Fix Teacher Permission Error: "Could not find Row #1: Role: Website User"

## Steps:
- [x] 1. Create this TODO.md with plan breakdown
- [x] 2. Edit school/school_management/doctype/teacher/teacher.json to add Website User permission row

- [x] 3. Run `cd .. && bench migrate` to apply DocType changes
- [x] 4. Run `bench clear-cache`
- [x] 5. Test: Create Teacher with create_user=1, portal_email; verify no error, User created with Teacher + Website User roles, login works like student portal

- [x] 6. Update TODO.md after completion

