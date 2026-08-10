# Eval prompt: cross-account-kms-decrypt

Diagnose the following S3 AccessDenied incident. Walk the full diagnostic
decision tree across both accounts (identity policy in caller account,
bucket policy in resource account, KMS key policy in resource account,
BPA in both, Object Ownership in resource account) and emit the standard
VERDICT block (INCIDENT, VERDICT, ROOT_CAUSE, EVIDENCE,
ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

A Lambda function in account `111111111111` (role
`arn:aws:iam::111111111111:role/app-lambda`) calls `s3:GetObject` on
`arn:aws:s3:::prod-data/report.csv` in account `222222222222`. The
object is encrypted with a customer-managed KMS key
`arn:aws:kms:us-east-1:222222222222:key/abc123` in account
`222222222222`.

## Known facts

- Lambda role identity policy includes:
  - `s3:GetObject` on `arn:aws:s3:::prod-data/*` (object ARN with `/*`).
  - `kms:Decrypt` on `arn:aws:kms:us-east-1:222222222222:key/abc123`.
- S3 bucket policy (account `222222222222`) has a statement with
  `Principal: { AWS: "arn:aws:iam::111111111111:role/app-lambda" }`,
  `Action: s3:GetObject`, `Resource: arn:aws:s3:::prod-data/*`.
- KMS key policy (account `222222222222`) has `Principal.AWS` listing
  only account-`222222222222` roles. No cross-account grant for
  `kms:Decrypt`.
- No SCPs on either account restrict S3 or KMS.
- No permissions boundary on the Lambda role.
- No session policy (direct Lambda invocation).
- Object Ownership is `BucketOwnerEnforced` (does not affect reads).
- BPA at both scopes in both accounts is either disabled or not
  applicable for authenticated IAM cross-account access.

## Symptom

The Lambda function gets `AccessDenied` on `s3:GetObject`.
