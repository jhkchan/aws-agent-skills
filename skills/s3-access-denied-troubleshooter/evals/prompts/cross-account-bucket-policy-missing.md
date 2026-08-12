# Eval prompt: cross-account-bucket-policy-missing

Diagnose the S3 Access Denied error for the following scenario. Walk
the authorisation evaluation hierarchy and emit the standard diagnostic
block (TARGET, VERDICT, REASON, ROOT_CAUSE, EVIDENCE, REMEDIATION).

Symptom: role `arn:aws:iam::222222222222:role/cross-account-reader`
gets "Access Denied" on `s3:GetObject` for
`s3://shared-data-bucket/reports/daily.csv`. The caller is in a
different account than the bucket owner.

```text
Bucket: shared-data-bucket (owner: 111111111111)
Key: reports/daily.csv
Caller: arn:aws:iam::222222222222:role/cross-account-reader
Action: s3:GetObject
Error: "Access Denied" (HTTP 403)

IAM policy (cross-account-reader in 222222222222):
  - Allow s3:GetObject on arn:aws:s3:::shared-data-bucket/*

Bucket policy (shared-data-bucket in 111111111111):
  - Allow s3:GetObject for principal
    arn:aws:iam::111111111111:role/internal-reader
  (NO statement for account 222222222222)

Encryption: SSE-S3 (no KMS)
Object ownership: BucketOwnerEnforced
SCPs: none deny s3
Permission boundary: none
```

Cross-account S3 access requires BOTH the caller's IAM policy AND the
bucket policy to explicitly allow. Verify the bucket policy side and
recommend the fix.
