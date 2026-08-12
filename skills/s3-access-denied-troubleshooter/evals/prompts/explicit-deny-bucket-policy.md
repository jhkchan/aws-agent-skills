# Eval prompt: explicit-deny-bucket-policy

Diagnose the S3 Access Denied error for the following scenario. Walk
the authorisation evaluation hierarchy and emit the standard diagnostic
block (TARGET, VERDICT, REASON, ROOT_CAUSE, EVIDENCE, REMEDIATION).

Symptom: Lambda function `fn-data-pipeline` gets "Access Denied" on
`s3:PutObject` to `prod-logs-bucket`. The function's execution role
has `s3:PutObject` permission. The bucket policy has an explicit Deny
based on `aws:SourceIp` not matching the corporate CIDR `10.0.0.0/8`.
The Lambda function is VPC-attached; its source IP is the NAT Gateway
IP (which is outside `10.0.0.0/8`).

```text
Bucket: prod-logs-bucket
Caller: arn:aws:iam::111111111111:role/fn-data-pipeline-role
Action: s3:PutObject
Error: "Access Denied" (HTTP 403)

IAM policy (fn-data-pipeline-role):
  - Allow s3:PutObject on arn:aws:s3:::prod-logs-bucket/*

Bucket policy (prod-logs-bucket):
  Statement 1: Allow s3:PutObject for principal *
  Statement 2: Deny s3:PutObject if
    "aws:SourceIp" not in ["10.0.0.0/8"]

Encryption: SSE-S3
SCPs: none deny s3
Permission boundary: none

CloudTrail errorMessage: "explicit deny"
```

An explicit Deny at any level overrides all Allow statements. Verify
the Deny statement in the bucket policy and recommend the fix.
