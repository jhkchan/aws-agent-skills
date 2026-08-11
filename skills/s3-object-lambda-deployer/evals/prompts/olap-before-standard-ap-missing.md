# Eval prompt: olap-before-standard-ap-missing

Design a deployment plan for an S3 Object Lambda Access Point. Emit the
standard VERDICT block (OBJECT_LAMBDA_SPEC, VERDICT, CHECKLIST,
VERIFICATION_COMMANDS).

Requirements:

- OLAP name: new-olap
- Bucket: shared-reports (baseline healthy — BPA, SSE-S3, versioning)
- Supporting standard AP: reports-ap — DOES NOT EXIST YET. The
  operator plans to create the OLAP first, then create the standard
  AP afterward.
- IAM role: olap-reports-role (trust=s3-object-lambda.amazonaws.com;
  perms include WriteGetObjectResponse, logs:*, s3:GetObject)
- Transform Lambda: reports-redact-fn (python3.12, uses
  WriteGetObjectResponse correctly)
- Reserved concurrency: 20
- Operations: GetObject
- Region: us-east-1, Account: 111111111111

Additional context: the operator wants to "test the OLAP creation"
before setting up the standard AP, reasoning that the OLAP can be
re-pointed later. They have not verified whether reports-ap exists.
