# Eval prompt: putobject-sse-enforcement-deny

Diagnose the following S3 AccessDenied incident. Walk the full PutObject
diagnostic decision tree (identity policy, bucket policy Deny, KMS
GenerateDataKey, Object Lock, Object Ownership, BPA) and emit the
standard VERDICT block (INCIDENT, VERDICT, ROOT_CAUSE, EVIDENCE,
ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

A service in account `111111111111` uploads to
`arn:aws:s3:::finance-logs/tx-2026-08.csv` (same account) via:

```
aws s3api put-object --bucket finance-logs --key tx-2026-08.csv --body data.csv
```

(without any `--server-side-encryption` flag).

## Known facts

- The bucket `finance-logs` has a bucket policy with a `Deny` statement:

  ```json
  {
    "Sid": "DenyPutObjectWithoutSSEKMS",
    "Effect": "Deny",
    "Principal": "*",
    "Action": "s3:PutObject",
    "Resource": "arn:aws:s3:::finance-logs/*",
    "Condition": {
      "StringNotEquals": {
        "s3:x-amz-server-side-encryption": "aws:kms"
      }
    }
  }
  ```
- The caller's identity policy grants `s3:PutObject` on
  `arn:aws:s3:::finance-logs/*` and `kms:GenerateDataKey` on
  `arn:aws:kms:us-east-1:111111111111:key/finance-key`.
- The bucket uses SSE-KMS with that key.
- No Object Lock retention on the key (this is a new upload).
- Object Ownership is `BucketOwnerEnforced` (same-account write, so no
  ACL issue).
- No BPA blocking.

## Symptom

The PutObject call returns `AccessDenied`.
