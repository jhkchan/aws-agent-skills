# Eval prompt: kms-cross-account-decrypt

Diagnose the following IAM AccessDenied incident. Walk the full policy
evaluation decision tree (SCP, resource-based, identity-based, boundary,
session, VPC endpoint) and emit the standard VERDICT block (INCIDENT,
VERDICT, ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

A Lambda function in account `111111111111` (role
`arn:aws:iam::111111111111:role/app-lambda`) calls `s3:GetObject` on
`arn:aws:s3:::prod-data/report.csv` in account `222222222222`. The
object is encrypted with a customer-managed KMS key
`arn:aws:kms:us-east-1:222222222222:key/abc123` in account `222222222222`.

## Known facts

- Lambda role identity policy includes:
  - `s3:GetObject` on `arn:aws:s3:::prod-data/*`
  - `kms:Decrypt` on `arn:aws:kms:us-east-1:222222222222:key/abc123`
- S3 bucket policy (account `222222222222`) has a statement with
  `Principal: { AWS: "arn:aws:iam::111111111111:role/app-lambda" }`,
  `Action: s3:GetObject`, `Resource: arn:aws:s3:::prod-data/*`.
- KMS key policy (account `222222222222`) has `Principal.AWS` listing
  only account-`222222222222` roles. No cross-account grant.
- No SCPs on either account restrict S3 or KMS.
- No permissions boundary on the Lambda role.
- No session policy (direct invocation).

## Symptom

The Lambda function gets `AccessDenied` on `s3:GetObject`.
