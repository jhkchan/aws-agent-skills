# Eval prompt: kms-key-policy-decrypt-missing

Diagnose the S3 Access Denied error for the following scenario. Walk
the authorisation evaluation hierarchy and emit the standard diagnostic
block (TARGET, VERDICT, REASON, ROOT_CAUSE, EVIDENCE, REMEDIATION).

Symptom: application role `arn:aws:iam::111111111111:role/app-role`
gets "Access Denied" (HTTP 403) on every `s3:GetObject` call for
objects in `prod-data-bucket`. The bucket policy and IAM policy both
allow `s3:GetObject`. Objects are encrypted with SSE-KMS using a
customer-managed key
`arn:aws:kms:us-east-1:111111111111:key/abc-123`.

```text
Bucket: prod-data-bucket
Key: orders/2024/order-001.json
Caller: arn:aws:iam::111111111111:role/app-role
Action: s3:GetObject
Error: "Access Denied" (HTTP 403)

IAM policy (app-role):
  - Allow s3:GetObject on arn:aws:s3:::prod-data-bucket/*
  - Allow s3:ListBucket on arn:aws:s3:::prod-data-bucket

Bucket policy:
  - Allow s3:GetObject for principal
    arn:aws:iam::111111111111:role/app-role

Bucket encryption: SSE-KMS with
  arn:aws:kms:us-east-1:111111111111:key/abc-123
KMS key manager: CUSTOMER
KMS key state: Enabled
Caller kms:Decrypt on key abc-123: NOT PRESENT

SCPs: none deny s3 or kms
Permission boundary: none
VPC endpoint policy: allows all S3 actions
```

The S3 authorisation chain allows the request, but the KMS key policy
is a separate gate. Verify whether the caller has `kms:Decrypt` on the
customer-managed key and recommend the fix.
