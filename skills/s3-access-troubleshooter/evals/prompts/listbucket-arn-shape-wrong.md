# Eval prompt: listbucket-arn-shape-wrong

Diagnose the following S3 AccessDenied incident. Walk the full diagnostic
decision tree (identity policy, bucket policy, BPA, Object Ownership,
VPC endpoint) and emit the standard VERDICT block (INCIDENT, VERDICT,
ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

An IAM user `arn:aws:iam::111111111111:user/dev` in account
`111111111111` runs `aws s3 ls s3://internal-docs/` and gets
`AccessDenied` with the message naming `s3:ListBucket` as the denied
action. The bucket `internal-docs` is in the same account.

## Known facts

- The user's identity policy grants `s3:ListBucket` on
  `arn:aws:s3:::internal-docs/*` (the object ARN, with the `/*` suffix).
- No bucket policy `Deny` statements on `s3:ListBucket`.
- BPA not blocking — caller is authenticated IAM.
- No KMS encryption (ListBucket does not invoke KMS regardless).
- Object Ownership is `BucketOwnerEnforced`.
- No VPC endpoint in the path.

## Symptom

The user gets `AccessDenied` on `s3:ListBucket` when running `aws s3 ls
s3://internal-docs/`.
