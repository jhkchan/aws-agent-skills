# Bucket Policy and Organization Trail Reference Guide

Supplementary reference for the CloudTrail Missing Events
Troubleshooter skill. Loaded on-demand when a diagnostic needs the
canonical CloudTrail bucket policy, org trail topology, member
shadow trail semantics, KMS-encrypted log files, multi-region
trail scope, log file validation, or log file delivery timing
rules.

## Canonical CloudTrail bucket policy

The S3 bucket policy MUST include three statements that allow the
`cloudtrail.amazonaws.com` service principal to perform the
required actions. Without these statements, CloudTrail reports
`IsLogging: true` but does not deliver any log files — the service
retries silently on bucket-policy rejection.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AWSCloudTrailAclCheck20150319",
      "Effect": "Allow",
      "Principal": { "Service": "cloudtrail.amazonaws.com" },
      "Action": "s3:GetBucketAcl",
      "Resource": "arn:aws:s3:::<bucket>"
    },
    {
      "Sid": "AWSCloudTrailWrite20150319",
      "Effect": "Allow",
      "Principal": { "Service": "cloudtrail.amazonaws.com" },
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::<bucket>/<prefix>/AWSLogs/<account>/CloudTrail/*",
      "Condition": {
        "StringEquals": { "s3:x-amz-acl": "bucket-owner-full-control" }
      }
    },
    {
      "Sid": "AWSCloudTrailListBucket20150319",
      "Effect": "Allow",
      "Principal": { "Service": "cloudtrail.amazonaws.com" },
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::<bucket>",
      "Condition": {
        "StringLike": {
          "s3:prefix": [ "<prefix>/AWSLogs/<account>/CloudTrail/*" ]
        }
      }
    }
  ]
}
```

### Required actions

| Action | Purpose |
|---|---|
| `s3:GetBucketAcl` | CloudTrail checks the bucket ACL on every delivery. |
| `s3:ListBucket` | CloudTrail lists the prefix to determine the next sequence number. |
| `s3:PutObject` | CloudTrail writes the log file. |
| (condition) `s3:x-amz-acl: bucket-owner-full-control` | Ensures the log file is owned by the bucket owner, not the CloudTrail service account. Without this, downstream Athena / Lake Formation queries break. |

### Common policy pitfalls

- **Missing the `bucket-owner-full-control` condition:** Without
  the condition, the CloudTrail service account owns the objects.
  Athena and Lake Formation queries that depend on bucket-owner
  permissions fail.
- **Resource ARN scoped to the wrong account:** The `Resource` ARN
  must include the AWS account ID that owns the trail. A policy
  scoped to the bucket account when the trail is in another
  account fails.
- **Explicit Deny that matches:** A Deny statement with an
  `aws:SourceIp` condition that matches the CloudTrail service
  range silently blocks delivery.
- **BucketOwnerEnforced without the CloudTrail statement:** The
  S3 BucketOwnerEnforced ACL setting (which disables ACLs entirely)
  does NOT automatically grant CloudTrail write access. The bucket
  policy must still include the canonical CloudTrail statement.

### Organization trail bucket policy

For organization trails, the bucket policy `Resource` ARN must
cover the org ID instead of (or in addition to) individual account
IDs:

```json
"Resource": "arn:aws:s3:::<bucket>/<prefix>/AWSLogs/o-<org-id>/*"
```

This allows CloudTrail to deliver log files for every member
account in the org. A policy scoped to
`AWSLogs/<management-account-id>/*` only delivers the management
account's events — member account events fail silently.

## Organization trail topology

When an org trail is created in the management account, CloudTrail
creates a **shadow trail** in every member account. The shadow
trail:

- Appears in `describe-trails` in the member account with
  `IsOrganizationTrail: true`.
- Is read-only — the member account cannot modify it.
- Delivers events to the **org trail's bucket**, not the member's
  bucket.
- Causes any pre-existing member trail that delivered to the
  member's own bucket to **STOP DELIVERING** — the events are now
  captured by the org trail.

### Org trail creation flow

```
1. Management account: aws cloudtrail create-trail --is-organization-trail
2. CloudTrail creates shadow trails in every member account.
3. Member shadow trails deliver events to the org trail's bucket.
4. Pre-existing member trails that delivered to member buckets stop.
5. Member account operators see the shadow trail in describe-trails.
```

### Org trail bucket policy (canonical)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AWSCloudTrailAclCheck",
      "Effect": "Allow",
      "Principal": { "Service": "cloudtrail.amazonaws.com" },
      "Action": "s3:GetBucketAcl",
      "Resource": "arn:aws:s3:::<org-bucket>"
    },
    {
      "Sid": "AWSCloudTrailWriteForOrg",
      "Effect": "Allow",
      "Principal": { "Service": "cloudtrail.amazonaws.com" },
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::<org-bucket>/<prefix>/AWSLogs/o-<org-id>/*",
      "Condition": {
        "StringEquals": { "s3:x-amz-acl": "bucket-owner-full-control" }
      }
    }
  ]
}
```

Note the `o-<org-id>` in the Resource ARN — this is the org ID, not
an account ID.

### Member trail coexistence

Both an org trail and a member trail can coexist:
- The org trail delivers to the org bucket.
- The member trail delivers to the member bucket.
- The member trail's `start-logging` must be re-invoked if it was
  shadowed by the org trail creation.

The trade-off: both trails capture the member's events, so the
member's events are duplicated (once in the org bucket, once in the
member bucket). This is acceptable for compliance but incurs
double ingestion cost.

### Member left the org

When a member leaves the org:
- The shadow trail in the member account is removed.
- The member's events are no longer captured by the org trail.
- If the member has its own trail (re-started), it resumes
  delivering to the member bucket.

## Multi-region trail scope

| Field | Effect |
|---|---|
| `IsMultiRegionTrail: true` | Trail captures events from every region. Default for new trails created via the console. |
| `IsMultiRegionTrail: false` | Trail captures events only from its home region. Common for cost-optimised trails. |

Note: a single-region trail in us-east-1 still captures global
service events (IAM, STS, CloudFront) if
`IncludeGlobalServiceEvents: true`. Operators who "see IAM events
but not EC2 events from us-west-2" have a single-region trail.

## Log file delivery timing

CloudTrail delivers log files approximately every 5 minutes per
region per account. The `LatestDeliveryTime` field in
`get-trail-status` reflects the most recent delivery.

| Field | Healthy | Stale (investigate) |
|---|---|---|
| `LatestDeliveryTime` | Within last 15 minutes | More than 60 minutes old |
| `LatestCloudWatchLogsDeliveryTime` | Within last 15 minutes | More than 60 minutes old |
| `LatestDigestDeliveryTime` | Within last 60 minutes | More than 6 hours old |

`LatestDigestDeliveryTime` is independent of `LatestDeliveryTime`
because digests are delivered on a different cadence (hourly).
Stale digest delivery with healthy log delivery is a separate
issue (usually the bucket policy missing `s3:PutObject` for the
digest prefix).

## KMS-encrypted log files

If the trail has `KmsKeyId: <arn>` set, CloudTrail encrypts every
log file with the specified customer-managed CMK before writing
to S3. The CMK must:

- Be in the same region as the trail.
- Have a key policy that grants `kms:GenerateDataKey` and
  `kms:DescribeKey` to the `cloudtrail.amazonaws.com` service
  principal.
- Be `Enabled`. If the key state is `Disabled` or `PendingDeletion`,
  CloudTrail cannot encrypt log files and stops delivering.

### KMS key policy for CloudTrail

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Allow CloudTrail to encrypt logs",
      "Effect": "Allow",
      "Principal": { "Service": "cloudtrail.amazonaws.com" },
      "Action": ["kms:GenerateDataKey", "kms:DescribeKey"],
      "Resource": "*"
    }
  ]
}
```

### KMS-disabled diagnosis

If `KeyState: Disabled` or `PendingDeletion`:
- CloudTrail reports `IsLogging: true`.
- `LatestDeliveryTime` is stale (last delivery was before the key
  was disabled).
- The bucket policy is correct; the S3 bucket has space.
- Fix: re-enable the key (`aws kms enable-key --key-id <id>`).
  If the key is in `PendingDeletion` within the 7-30 day deletion
  window, the key cannot be re-enabled — migrate the trail to a
  new key via `update-trail --kms-key-id <new-arn>`.

## Log file validation

CloudTrail supports log file validation via hourly digest files.
The digest files are written to the same S3 bucket under
`<prefix>/AWSLogs/<account>/CloudTrail-Digest/`. To validate:

```bash
aws cloudtrail validate-logs --trail-arn <trail-arn> \
  --start-time <time> --end-time <time> --s3-bucket <bucket> \
  --s3-prefix <prefix>
```

Common validation failures:
- **Digest files deleted from S3:** Manual deletion or a lifecycle
  policy that targets the digest prefix. Restore from versioning or
  backup.
- **Bucket policy missing `s3:PutObject` for the digest prefix:**
  The digest files are never delivered. `LatestDigestDeliveryTime`
  is stale while `LatestDeliveryTime` is healthy.
- **KMS key disabled:** Both log files and digest files fail to
  encrypt and deliver.

## AWS documentation references

- CloudTrail S3 bucket policy: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/create-s3-bucket-policy-for-cloudtrail.html
- Organization trails: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html
- KMS-encrypted log files: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/encrypting-cloudtrail-log-files-with-aws-kms.html
- Log file validation: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-log-file-validation-cli.html
- Multi-region trails: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/receive-cloudtrail-log-files-from-multiple-regions.html

## Canonical bucket policy statement (Step 3a)

The canonical policy statement:

```json
{
  "Sid": "AWSCloudTrailAclCheck20150319",
  "Effect": "Allow",
  "Principal": {"Service": "cloudtrail.amazonaws.com"},
  "Action": "s3:GetBucketAcl",
  "Resource": "arn:aws:s3:::<bucket>"
},
{
  "Sid": "AWSCloudTrailWrite20150319",
  "Effect": "Allow",
  "Principal": {"Service": "cloudtrail.amazonaws.com"},
  "Action": "s3:PutObject",
  "Resource": "arn:aws:s3:::<bucket>/<prefix>/AWSLogs/<account>/CloudTrail/*",
  "Condition": {"StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}}
}
```

## Org trail shadow patterns (Step 5)

Common patterns: member account `describe-trails` shows a trail with
`IsOrganizationTrail: true` that the member did not create (shadow
trail; member events go to the org bucket); member's pre-existing
trail stops delivering after the org trail was created (org trail
shadows the member trail); org trail bucket policy scoped to the
management account only (Resource ARN missing the org ID
`o-<org-id>`); member left the org (shadow trail removed).
