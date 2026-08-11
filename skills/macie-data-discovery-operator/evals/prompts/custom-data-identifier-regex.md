# Eval: custom-data-identifier-regex

**Difficulty:** hard
**Branch:** READY — custom regex data identifier for EMP###### employee ID with proximity keywords and ignore words

## Prompt

Create a Macie custom data identifier named "employee-id-pattern" that
detects our internal employee ID format EMP###### (EMP followed by 6
digits). Use proximity keywords: employee, emp_id, staff, id. Ignore
test/sample data: example, test, sample, demo. Maximum match distance
50 characters. Severity HIGH. Account: 123456789012. Region: us-east-1.
Provide the full procedure.
