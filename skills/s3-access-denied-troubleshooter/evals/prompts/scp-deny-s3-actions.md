# Eval prompt: scp-deny-s3-actions

Diagnose the S3 Access Denied error for the following scenario. Walk
the authorisation evaluation hierarchy and emit the standard diagnostic
block (TARGET, VERDICT, REASON, ROOT_CAUSE, EVIDENCE, REMEDIATION).

Symptom: role `arn:aws:iam::999999999999:role/sandbox-app` gets
"Access Denied" on `s3:GetObject` for
`s3://sandbox-data-bucket/config.json`. The IAM policy and bucket
policy both allow the action. The account `999999999999` is in the
"Sandbox" OU, which has an SCP denying all S3 actions.

```text
Bucket: sandbox-data-bucket
Key: config.json
Caller: arn:aws:iam::999999999999:role/sandbox-app
Action: s3:GetObject
Error: "Access Denied" (HTTP 403)

IAM policy (sandbox-app):
  - Allow s3:GetObject on arn:aws:s3:::sandbox-data-bucket/*

Bucket policy (sandbox-data-bucket):
  - Allow s3:GetObject for principal *

SCPs on OU "Sandbox" (contains account 999999999999):
  - Deny s3:* for all principals

Encryption: SSE-S3
Permission boundary: none
KMS: not in use

simulate-principal-policy result: explicitDeny
```

SCPs are evaluated first in the hierarchy, before IAM and bucket
policies. Verify the SCP and recommend the fix.
