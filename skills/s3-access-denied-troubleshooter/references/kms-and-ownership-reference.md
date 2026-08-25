# S3 KMS and Object Ownership Reference Guide

Supplementary reference for the S3 Access Denied Troubleshooter skill.
Loaded on-demand when a diagnostic needs KMS key policy details,
object ownership models, Object Lock semantics, or Block Public Access
configuration.

## KMS key types and S3 interaction

| KMS key type | ARN pattern | S3 behaviour | Caller needs kms:Decrypt? |
|---|---|---|---|
| AWS-managed (`aws/s3`) | `arn:aws:kms:<region>:<account>:key/aws/s3` | S3 decrypts transparently | **No** — AWS manages the key policy |
| Customer-managed CMK | `arn:aws:kms:<region>:<account>:key/<uuid>` | Caller must have `kms:Decrypt` | **Yes** — in IAM policy AND key policy must grant caller's account |

### Key policy structure for SSE-KMS on S3

The customer-managed key policy must include:

1. **Key administrators** — `"Root"` principal with `kms:*` (the
   account root).
2. **IAM delegation** — a statement allowing the account to use IAM
   to delegate access (so IAM policies can grant `kms:Decrypt`).
3. **S3 service access** — optional but recommended: scope
   `kms:Decrypt` to the S3 service via `kms:ViaService`.

Example key policy for SSE-KMS:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Enable IAM User Permissions",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
      "Action": "kms:*",
      "Resource": "*"
    },
    {
      "Sid": "Allow S3 to use the key",
      "Effect": "Allow",
      "Principal": {"Service": "s3.amazonaws.com"},
      "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "s3.us-east-1.amazonaws.com",
          "kms:EncryptionContext:aws:s3:arn": "arn:aws:s3:::prod-data-bucket"
        }
      }
    }
  ]
}
```

### KMS condition keys for S3

| Condition key | Value | Purpose |
|---|---|---|
| `kms:ViaService` | `s3.<region>.amazonaws.com` | Ensures the key is used by S3, not directly |
| `kms:EncryptionContext:aws:s3:arn` | `arn:aws:s3:::<bucket>` | Restricts key to a specific bucket |
| `kms:CallerAccount` | `<account-id>` | Restricts key to a specific account |

### Cross-account KMS + S3

For cross-account SSE-KMS access:
1. The **caller's IAM policy** must grant `s3:GetObject` AND
   `kms:Decrypt` on the key.
2. The **bucket policy** must allow the caller's account.
3. The **KMS key policy** must allow the caller's account (the "Enable
   IAM User Permissions" statement with `root` principal covers this
   for same-account; cross-account needs an explicit statement).

## Object ownership models

| Setting | ACLs | Object owner | Effect |
|---|---|---|---|
| `BucketOwnerEnforced` (default since April 2023) | **Disabled** | Always bucket owner | All objects owned by bucket owner; ACLs ignored. Eliminates ownership-based AccessDenied. |
| `BucketOwnerPreferred` | Enabled | Bucket owner IF uploader grants `bucket-owner-full-control` ACL | Bucket owner owns objects only if the uploader includes the ACL header. |
| `ObjectWriter` (legacy default) | Enabled | Uploader (object writer) | Each object owned by the account that uploaded it. Bucket policy cannot grant access to objects owned by another account. |

### Migrating to BucketOwnerEnforced

```bash
aws s3api put-bucket-ownership-controls \
  --bucket <bucket> \
  --ownership-controls Rules=[{ObjectOwnership=BucketOwnerEnforced}]
```

For existing objects owned by a different account:
1. The uploader account must grant `bucket-owner-full-control` ACL
   on each object.
2. Use S3 Batch Operations to copy objects in-place, which changes
   ownership to the bucket owner.

```bash
aws s3control create-job \
  --account-id <account-id> \
  --operation '{"S3PutObjectCopy":{"BucketReference":{"Bucket":"<bucket>"}}}' \
  --manifest '{"Spec":{"Format":"S3BatchOperations_CSV_20180820","Fields":["Bucket","Key"]},"Location":{"Bucket":"<manifest-bucket>","Key":"manifest.csv"}}' \
  --report '{"Bucket":"<report-bucket>","Format":"Report_CSV_20180820","Enabled":true}' \
  --role-arn <batch-role-arn>
```

## Block Public Access settings

| Setting | Scope | Effect |
|---|---|---|
| `BlockPublicAcls` | Bucket / Account | Blocks new public ACLs. Existing public ACLs are ignored for new requests. |
| `IgnorePublicAcls` | Bucket / Account | Ignores all public ACLs on the bucket and its objects. |
| `BlockPublicPolicy` | Bucket / Account | Blocks new public bucket policies (with `Principal: *`). |
| `RestrictPublicBuckets` | Bucket / Account | Blocks public access via public bucket policies or ACLs. Only the bucket owner's own access is unaffected. |

Account-level settings apply to ALL buckets in the account. Bucket-level
settings override account-level settings only if they are MORE
restrictive (you cannot relax account-level restrictions at the bucket
level).

## Object Lock modes

| Mode | Bypass possible? | Effect on delete | Effect on overwrite |
|---|---|---|---|
| `COMPLIANCE` | **No** — not even root | Blocked until retention expires | Blocked until retention expires |
| `GOVERNANCE` | Yes — with `s3:BypassGovernanceRetention` | Blocked unless bypass | Blocked unless bypass |
| Legal hold (on/off) | Yes — with `s3:PutObjectLegalHold` | Blocked while hold is on | Blocked while hold is on |

### Object Lock error signatures

- Delete a retained object: `AccessDenied` (HTTP 403). The error
  message does NOT mention Object Lock — it looks like a permissions
  issue.
- Overwrite a retained object: `AccessDenied` (HTTP 403).

Always check Object Lock configuration when a specific object cannot
be deleted or overwritten but the IAM policy allows it.

## VPC endpoint policy for S3

The S3 Gateway endpoint policy is an additional gate evaluated for
VPC-attached callers. The endpoint policy can:

- Allow only specific buckets: `Resource: arn:aws:s3:::allowed-bucket/*`
- Allow only specific actions: `Action: s3:GetObject`
- Deny specific principals: `Deny` with `Principal: <arn>`

A restrictive endpoint policy produces the same `AccessDenied` error
as a missing IAM permission. Bypass the endpoint (route via NAT) to
verify.

## Presigned URL mechanics

| URL parameter | Meaning | Failure mode |
|---|---|---|
| `X-Amz-Expires` | URL validity duration (seconds) | Request after expiry → `AccessDenied: "Request has expired"` |
| `X-Amz-Date` | Signing timestamp (ISO 8601) | Clock skew > 15 min → `RequestTimeTooSkewed` |
| `X-Amz-Credential` | `<key>/<date>/<region>/aws4_request` | Region mismatch → `SignatureDoesNotMatch` |
| `X-Amz-Signature` | HMAC-SHA256 of the canonical request | Credential rotated → `SignatureDoesNotMatch` |
| `X-Amz-SignedHeaders` | Headers included in signature | Missing signed header → `AccessDenied` |

Maximum expiry by credential type:
- IAM user: up to 7 days (604800 seconds).
- STS assumed role: limited by the session duration (max 12 hours
  default).
- EC2 instance profile: limited by the instance role credentials
  rotation (typically 6 hours).

## KMS condition keys for S3

| Condition key | Meaning |
|---|---|
| `kms:ViaService` | The AWS service making the KMS call (e.g., `s3.us-east-1.amazonaws.com`) |
| `kms:EncryptionContext:aws:s3:arn` | The bucket ARN in the encryption context |
| `kms:CallerAccount` | The account of the caller |

Use these in the KMS key policy to scope which S3 buckets can use the
key:

```json
{
  "Condition": {
    "StringEquals": {
      "kms:ViaService": "s3.us-east-1.amazonaws.com",
      "kms:EncryptionContext:aws:s3:arn": "arn:aws:s3:::prod-data-bucket"
    }
  }
}
```
