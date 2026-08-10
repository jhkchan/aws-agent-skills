# Eval prompt: getobject-arn-shape-wrong

Diagnose the following S3 AccessDenied incident. Walk the full diagnostic
decision tree (identity policy, bucket policy, KMS key policy, BPA,
Object Ownership, ACL, VPC endpoint) and emit the standard VERDICT block
(INCIDENT, VERDICT, ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG,
REMEDIATION).

## Scenario

A Lambda function in account `111111111111` (role
`arn:aws:iam::111111111111:role/app-lambda`) calls `s3:GetObject` on
`arn:aws:s3:::prod-data/report.csv` (same account, no cross-account
involved).

## Known facts

- Lambda role identity policy grants `s3:GetObject` on
  `arn:aws:s3:::prod-data` (no `/*` suffix).
- No bucket policy `Deny` statements.
- No KMS encryption (SSE-S3 only).
- BPA not blocking — caller is an authenticated IAM principal.
- Object Ownership is `BucketOwnerEnforced` (default for new buckets).
- No VPC endpoint in the path.

## Symptom

The Lambda function gets `AccessDenied` on `s3:GetObject`.
