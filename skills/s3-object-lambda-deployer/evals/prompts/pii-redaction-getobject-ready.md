# Eval prompt: pii-redaction-getobject-ready

Design a deployment plan for an S3 Object Lambda Access Point. Emit the
standard VERDICT block (OBJECT_LAMBDA_SPEC, VERDICT, CHECKLIST,
VERIFICATION_COMMANDS).

Requirements:

- OLAP name: pii-redact-olap
- Bucket: prod-data-lake (BPA all 4 True, SSE-KMS, versioning Enabled)
- Supporting standard AP: dlake-team-a-ap (already exists; AP policy
  allows Lambda role arn:aws:iam::111111111111:role/olap-exec to
  GetObject)
- IAM role: olap-exec (trust=s3-object-lambda.amazonaws.com; perms
  include s3-object-lambda:WriteGetObjectResponse, logs:*, and
  s3:GetObject on the standard AP)
- Transform Lambda: pii-redact-fn (python3.12, index.handler, uses
  WriteGetObjectResponse with RequestRoute and RequestToken)
- Reserved concurrency: 50 (expected peak ~40 GETs/sec)
- Operations: GetObject only
- Region: us-east-1, Account: 111111111111

Additional context: the team is redacting SSN/email/phone patterns from
CSV exports served from the data lake. The transform Lambda fetches via
the presigned URL, applies regex substitutions, and writes back.
