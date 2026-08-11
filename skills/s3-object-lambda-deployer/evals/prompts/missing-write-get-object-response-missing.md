# Eval prompt: missing-write-get-object-response-missing

Design a deployment plan for an S3 Object Lambda Access Point. Emit the
standard VERDICT block (OBJECT_LAMBDA_SPEC, VERDICT, CHECKLIST,
VERIFICATION_COMMANDS).

Requirements:

- OLAP name: format-convert-olap
- Bucket: data-exports (baseline healthy)
- Supporting standard AP: exports-ap (exists, AP policy allows Lambda
  role to GetObject)
- IAM role: olap-convert-role (trust=s3-object-lambda.amazonaws.com).
  The permission policy includes:
  - logs:CreateLogGroup, logs:CreateLogStream, logs:PutLogEvents
  - s3:GetObject on the standard AP
  - NOTE: s3-object-lambda:WriteGetObjectResponse is NOT in the
    policy — the operator forgot to add it
- Transform Lambda: csv-to-json-fn (python3.12, the code DOES call
  WriteGetObjectResponse)
- Reserved concurrency: 30
- Operations: GetObject
- Region: us-east-1

Additional context: the team's Lambda code is correct (it calls
WriteGetObjectResponse), but the IAM role was created from a generic
Lambda template that does not include s3-object-lambda:WriteGetObjectResponse.
They have not noticed yet because testing hasn't started.
