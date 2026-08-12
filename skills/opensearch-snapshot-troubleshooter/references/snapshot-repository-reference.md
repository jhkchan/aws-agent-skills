# OpenSearch Snapshot Repository Reference Guide

Supplementary reference for the OpenSearch Snapshot Troubleshooter
skill. Loaded on-demand when a diagnostic needs repository
registration syntax, IAM role trust policy templates, bucket policy
minimums, or engine-version compatibility matrices.

## Repository types (managed OpenSearch Service)

| Repository | Owner | Use case |
|---|---|---|
| `cs-automated` | AWS-managed | Daily automated snapshots; bucket is read-only to the customer. Retention ~14 days. |
| `cs-automated-enc` | AWS-managed | Same as `cs-automated` but for encrypted domains. |
| Custom (any name) | Customer | Manual snapshots to a customer S3 bucket via a customer IAM role. |

Automated snapshots do NOT appear in your S3 account. List them via
`curl $ENDPOINT/_snapshot/cs-automated/_all`.

## PUT _snapshot minimum body (S3)

```json
{
  "type": "s3",
  "settings": {
    "bucket": "<bucket-name>",
    "region": "<bucket-region>",
    "base_path": "<prefix>",
    "iam_role_arn": "arn:aws:iam::<account>:role/<role>",
    "compress": true,
    "chunk_size": "1g"
  }
}
```

Field rules:

- `bucket` — the S3 bucket name (no `s3://` prefix).
- `region` — the bucket's Region (NOT the domain's Region). Omitting
  this field defaults to the domain Region and breaks cross-Region
  repositories.
- `base_path` — the S3 key prefix. Two repositories on the same
  bucket MUST have distinct `base_path` values; shared prefixes
  corrupt both repositories.
- `iam_role_arn` — the role the OpenSearch domain assumes to write
  to S3. Omitting this field fails on the first snapshot.
- `compress` — boolean. Halves S3 GET volume on restore.
- `chunk_size` — default `1g`. Lower to `256m` for clusters with
  large shards to reduce the blast radius of a corrupt blob.

## Snapshot IAM role — trust policy (same-account)

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "opensearchservice.amazonaws.com"},
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": {"aws:SourceAccount": "<account-id>"},
      "ArnLike": {
        "aws:SourceArn": "arn:aws:es:<region>:<account-id>:domain/<domain>"
      }
    }
  }]
}
```

Legacy domains (Elasticsearch 7.x / OpenSearch 1.x) may use
`"Service": "es.amazonaws.com"` — both work, the newer principal
is preferred.

## Snapshot IAM role — trust policy (cross-account)

For a snapshot role in Account A that a domain in Account B assumes:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "opensearchservice.amazonaws.com"},
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": {"aws:SourceAccount": "<account-B>"},
      "ArnLike": {
        "aws:SourceArn": "arn:aws:es:<region>:<account-B>:domain/<domain-in-B>"
      }
    }
  }]
}
```

Without the `aws:SourceAccount` / `aws:SourceArn` conditions, the
confused-deputy protection rejects the assume-role call and
verification fails.

## Snapshot IAM role — identity policy (minimum S3 actions)

| Action | Resource | Required for |
|---|---|---|
| `s3:ListBucket` | `arn:aws:s3:::<bucket>` | Listing snapshot objects |
| `s3:GetBucketLocation` | `arn:aws:s3:::<bucket>` | Resolving bucket Region |
| `s3:GetObject` | `arn:aws:s3:::<bucket>/<prefix>/*` | Reading snapshot blobs (restore) |
| `s3:PutObject` | `arn:aws:s3:::<bucket>/<prefix>/*` | Writing snapshot blobs (backup) |
| `s3:DeleteObject` | `arn:aws:s3:::<bucket>/<prefix>/*` | Deleting snapshot via `DELETE _snapshot` |

For SSE-KMS buckets, add `kms:Decrypt` and `kms:GenerateDataKey`
on the KMS key ARN.

For cross-account snapshots, add `s3:PutObjectAcl` so the writer
can set the ACL on the object.

## Bucket policy — grant the role (NOT the service principal)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListBucketForSnapshot",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::<account>:role/<role>"},
      "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
      "Resource": "arn:aws:s3:::<bucket>"
    },
    {
      "Sid": "ReadWriteSnapshotObjects",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::<account>:role/<role>"},
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::<bucket>/<prefix>/*"
    }
  ]
}
```

The most common mistake is keying the bucket policy to
`"Principal": {"Service": "opensearchservice.amazonaws.com"}`.
The role's session ARN does NOT match the service principal and
verification fails. The service principal goes in the ROLE TRUST,
not the bucket policy.

## Engine-version compatibility (snapshot restore)

| Source engine | Target engine | Direct restore? |
|---|---|---|
| ES 6.x | ES 7.x | Yes (one major up) |
| ES 7.0–7.10 | ES 7.x same/higher | Yes |
| ES 7.0–7.10 | OpenSearch 1.x | Yes |
| ES 7.0–7.10 | OpenSearch 2.x | No — needs intermediate 1.x |
| OpenSearch 1.x | OpenSearch 1.x same/higher | Yes |
| OpenSearch 1.x | OpenSearch 2.x | Yes (one major up) |
| OpenSearch 2.x | OpenSearch 2.y >= 2.x | Yes |
| OpenSearch 2.x | OpenSearch 2.y < 2.x | No |
| OpenSearch 2.x | OpenSearch 1.x | No |

For cross-major (7.x → 2.x) restores, use the snapshot-upgrade
flow: restore into an intermediate 1.x domain, snapshot from
there, then restore into the 2.x target.

## Verification-file diagnostic

OpenSearch writes a `verification-file-<uuid>` object during
`_verify`, then reads it back:

- Object present in S3 → write path works; failure is on the read
  path (KMS, role policy, or bucket Region).
- Object absent from S3 → write path failed (IAM, bucket policy,
  or wrong `base_path`).

```bash
aws s3 ls s3://<bucket>/<prefix>/verification-file-*
```

## Common failure signatures

| Error | Most common cause |
|---|---|
| `repository_verification_exception` | Bucket policy keyed to service principal instead of role ARN |
| `S3Exception: Forbidden` on verification | Wrong Region in PUT body; bucket policy missing `s3:GetBucketLocation` |
| `AccessDenied` from KMS on first object | Role missing `kms:GenerateDataKey` on the SSE-KMS key |
| `ConcurrentSnapshotExecutionException` | Automated and manual snapshots colliding on same repository |
| `SnapshotMissingException` on old snapshots | S3 lifecycle rule expiring snapshot blobs |
| `version_not_supported` on restore | Target engine version lower than source snapshot version |
| `resource_already_allocated_exception` on restore | Alias or index with same name exists on target |
