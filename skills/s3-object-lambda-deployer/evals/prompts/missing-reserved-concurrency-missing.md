# Eval prompt: missing-reserved-concurrency-missing

Design a deployment plan for an S3 Object Lambda Access Point. Emit the
standard VERDICT block (OBJECT_LAMBDA_SPEC, VERDICT, CHECKLIST,
VERIFICATION_COMMANDS).

Requirements:

- OLAP name: enrichment-olap
- Bucket: prod-data-lake (baseline healthy)
- Supporting standard AP: dlake-team-b-ap (exists, AP policy allows
  Lambda role to GetObject)
- IAM role: olap-enrich-role (trust=s3-object-lambda.amazonaws.com;
  perms include WriteGetObjectResponse, logs:*, s3:GetObject)
- Transform Lambda: enrich-fn (python3.12, uses WriteGetObjectResponse)
- Reserved concurrency: NOT SET — the team plans to rely on the
  account-level unreserved concurrency pool
- Operations: GetObject
- Expected peak traffic: ~100 GETs/sec during the morning batch

Additional context: the team expects to scale transparently because
"S3 handles the load." They have not set any reserved concurrency on
the Lambda function.
