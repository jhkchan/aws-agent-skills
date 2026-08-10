# S3 Batch Operations — Operation/IAM Permission Matrix

Load this reference when planning a `create-job` to verify the role has
the operation-specific IAM grants. `batchoperations:*` is the job-
control plane permission only; each operation type has a distinct set
of S3 / KMS / Lambda grants the role must also carry.

## Operation → required role permissions

| Operation | S3 grants | KMS grants | Other |
|---|---|---|---|
| **Copy** (`S3Copy`) | `s3:GetObject` on source; `s3:PutObject` on destination; `s3:GetObjectVersion` for versioned source | `kms:Decrypt` on source key (SSE-KMS); `kms:Encrypt` on destination key | For cross-account destination, destination bucket policy must grant the role |
| **ReplaceTag** (`S3ReplaceTags`) | `s3:GetObjectTagging`, `s3:PutObjectTagging`, `s3:DeleteObjectTagging` on target | `kms:Decrypt` on source key (SSE-KMS required to read the object) | Tag set ≤ 10 keys; value ≤ 256 chars |
| **Restore** (`S3InitiateRestoreObject`) | `s3:RestoreObject` on target | `kms:Decrypt` on source key (SSE-KMS) | Object must be in GLACIER / GLACIER_IR / DEEP_ARCHIVE; `ExpirationInDays` and `Tier` required |
| **Replicate** (`S3ReplicateObject`) | `s3:ReplicateObject`, `s3:ReplicateDelete` on destination; `s3:GetObjectVersion`, `s3:GetObjectVersionAcl` on source | `kms:Decrypt` on source key; `kms:Encrypt` on destination key | Source bucket must have replication configured |
| **Invoke** (`LambdaInvoke`) | `s3:GetObject` on source (the Lambda receives the object ARN) | N/A (Lambda is responsible for any KMS use) | Lambda resource-based policy must allow `batchoperations.amazonaws.com` to `lambda:InvokeFunction`; Lambda reserved concurrency ≥ `RequestsPerSecond` |
| **PutACL** (`S3PutObjectAcl`) | `s3:PutObjectAcl`, `s3:GetObjectAcl` on target | `kms:Decrypt` on source key (SSE-KMS) | Canned ACL or access-control policy is valid |
| **PutObjectLockRetention** (`S3PutObjectRetention`) | `s3:PutObjectRetention`, `s3:GetObjectRetention` on target | `kms:Decrypt` on source key | Target bucket MUST have Object Lock enabled; `Mode: GOVERNANCE | COMPLIANCE`; `RetainUntilDate` in the future |
| **PutObjectLockLegalHold** (`S3PutObjectLegalHold`) | `s3:PutObjectLegalHold`, `s3:GetObjectLegalHold` on target | `kms:Decrypt` on source key | Target bucket MUST have Object Lock enabled; `Status: ON | OFF` |

## Caller-side permissions (the principal invoking `create-job`)

```
s3control:CreateJob
iam:PassRole on arn:aws:iam::<account>:role/<batch-ops-role>
```

For diagnose / cancel / update operations:

```
s3control:DescribeJob
s3control:UpdateJobStatus
s3control:UpdateJobPriority
s3control:ListJobs
```

## Role trust policy

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "batchoperations.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

Without this trust, the job cannot assume the role and fails immediately
with `AccessDenied` at `Active` → `Failed` transition.

## Common least-privilege policy (copy operation, same-account)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:GetObjectVersion"],
      "Resource": "arn:aws:s3:::prod-source/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::prod-destination/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::prod-inventory/manifests/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::prod-batch-reports/*"
    },
    {
      "Effect": "Allow",
      "Action": ["kms:Decrypt"],
      "Resource": "arn:aws:kms:us-east-1:111111111111:key/<source-key>"
    },
    {
      "Effect": "Allow",
      "Action": ["kms:Encrypt", "kms:ReEncrypt*"],
      "Resource": "arn:aws:kms:us-east-1:111111111111:key/<destination-key>"
    }
  ]
}
```

The role does NOT need `batchoperations:*` — that is the caller-side
permission. The role needs only the S3 / KMS / Lambda grants above.

## Cross-account destination bucket policy (copy)

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::<source-account>:role/<batch-ops-role>"},
    "Action": ["s3:PutObject", "s3:PutObjectAcl", "s3:PutObjectTagging"],
    "Resource": "arn:aws:s3:::prod-destination/*",
    "Condition": {"StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}}
  }]
}
```

## Lambda resource-based policy (invoke operation)

```bash
aws lambda add-permission \
  --function-name <function> \
  --statement-id BatchOperationsAccess \
  --principal batchoperations.amazonaws.com \
  --action lambda:InvokeFunction \
  --source-arn arn:aws:s3:<region>:<account>:<manifest-bucket> \
  --source-account <account>
```

The Lambda receives an event with `taskId`, `s3Key`, `s3VersionArn`,
`s3BucketArn`. The Lambda must return a valid response (success /
temporary failure / permanent failure) per the Batch Operations
Lambda contract.

## Failure code reference

| Failure code in completion report | Meaning | Fix |
|---|---|---|
| `AccessDenied` | Role lacks an operation-specific grant on the object | Add the missing S3 / KMS grant |
| `NoSuchKey` | Object deleted between manifest generation and processing | Re-generate manifest or skip |
| `NoSuchBucket` | Source or destination bucket deleted | Update manifest or cancel job |
| `SlowDown` / `Throttling` | Source / destination bucket throttled | Lower `RequestsPerSecond`; re-run failures |
| `InvalidRequest` | Operation invalid for the object state (e.g., Object Lock on a bucket without Object Lock) | Fix bucket configuration or filter manifest |
| `ResourceConflictException` (Lambda) | Lambda reserved concurrency exhausted | `put-function-concurrency --reserved-concurrent-executions <rate>` |
| `Timeout` (Lambda) | Lambda timeout too short | `update-function-configuration --timeout 60` |
| `KMS.AccessDeniedException` | KMS key policy denies the role | Update key policy; cross-account needs explicit grant |
| `Transient` | Internal S3 transient error; auto-retried up to limit | Re-run failed objects if count persists |

## Manifest format reference

### S3 inventory report manifest

Requires both `manifest.json` and `manifest.checksum` in the same
prefix. The `manifest.json` contains the bucket/key list; the
checksum file allows Batch Operations to verify integrity.

```json
{
  "Spec": {"Format": "S3InventoryReport", "Fields": ["Bucket", "Key", "VersionId"]},
  "Location": {
    "ObjectArn": "arn:aws:s3:::prod-inventory/2026-08-01/manifest.json",
    "ETag": "<etag-of-manifest-json>"
  }
}
```

For versioned operations, the inventory configuration must use
`Version: V2` and include the `VersionId` field.

### CSV manifest

No header row. One line per object:

```
prod-source,object-key-1
prod-source,object-key-2
prod-source,object-key-3,version-id-3
```

The optional third column is the version ID for version-aware
operations. Lines without a version ID target the latest version.

```json
{
  "Spec": {"Format": "CSV", "Fields": ["Bucket", "Key", "VersionId"]},
  "Location": {
    "ObjectArn": "arn:aws:s3:::prod-manifests/bulk-copy-2026-08.csv",
    "ETag": "<etag-of-csv>"
  }
}
```
