# S3 Replication Rule Configuration Templates Reference

Load this reference when planning or executing a replication rule change.
The templates below cover the canonical rule shapes (CRR, SRR,
cross-account, RTC, multiple destinations, delete-marker replication,
replica modification sync, Object Lock), the IAM role permission
templates, and the cross-account destination bucket policy templates.

## put-bucket-replication is a FULL-REPLACEMENT API

`put-bucket-replication` REPLACES the entire `ReplicationConfiguration`.
There is no `add-rule` or `update-rule` API. The mandatory merge
procedure:

1. `aws s3api get-bucket-replication --bucket <source> --output json >
   /tmp/<source>-repl-pre-$(date +%s).json` — capture pre-state.
2. Append the new rule, or modify the existing rule, in the JSON.
3. Sort ALL rules by `Priority` descending (highest Priority first in
   the list is NOT required by S3, but aids review).
4. `aws s3api put-bucket-replication --bucket <source>
   --replication-configuration file:///tmp/<source>-repl-merged.json`.

If you skip step 1, ALL existing rules are wiped and replication for
other prefixes halts silently.

## Rule anatomy

```json
{
  "ID": "unique-rule-id",
  "Priority": 1,
  "Status": "Enabled",
  "Filter": {
    "Prefix": "logs/",
    "Tags": [{"Key": "env", "Value": "prod"}]
  },
  "Destination": {
    "Bucket": "arn:aws:s3:::destination-bucket",
    "StorageClass": "STANDARD",
    "Account": "222222222222",
    "AccessControlTranslation": {"Owner": "Destination"},
    "EncryptionConfiguration": {"ReplicaKmsKeyID": "arn:aws:kms:eu-west-1:222222222222:key/dest-cmk"},
    "ReplicationTime": {"Status": "Enabled", "Time": {"Minutes": 15}},
    "Metrics": {"Status": "Enabled", "EventThreshold": {"Minutes": 15}}
  },
  "DeleteMarkerReplication": {"Status": "Enabled"},
  "DeleteReplication": {"Status": "Enabled"},
  "SourceSelectionCriteria": {
    "ReplicaModifications": {"Status": "Enabled"},
    "SseKmsEncryptedObjects": {"Status": "Enabled"}
  },
  "ExistingObjectReplication": {"Status": "Enabled"}
}
```

Field-by-field notes:

| Field | Purpose | Default |
|---|---|---|
| `ID` | Unique within the bucket. Used for diagnosis. | Required |
| `Priority` | Resolves overlaps. Higher integer = higher priority. | Required, must be unique within the bucket |
| `Status` | `Enabled` or `Disabled`. Disabled = rule inert. | Required |
| `Filter.Prefix` | Object key prefix filter. Empty = entire bucket. | Optional |
| `Filter.Tags` | Tag-based filter (AND with Prefix). Case-sensitive. | Optional |
| `Destination.Bucket` | Destination bucket ARN. | Required |
| `Destination.Account` | Destination account ID (cross-account). | Required for cross-account |
| `Destination.AccessControlTranslation` | `{Owner: Destination}` for cross-account ownership. | Required for cross-account |
| `Destination.EncryptionConfiguration.ReplicaKmsKeyID` | Forces replicas to use this destination CMK. | Optional |
| `Destination.ReplicationTime` | Enables RTC. `Time.Minutes` must be 15. | Optional |
| `Destination.Metrics` | Enables RTC metrics. `EventThreshold.Minutes` must be 15. | Optional |
| `DeleteMarkerReplication` | Whether delete markers replicate. | `Disabled` (default) |
| `DeleteReplication` | Whether hard DELETEs replicate. | `Disabled` (default) |
| `SourceSelectionCriteria.ReplicaModifications` | Metadata sync (tag/ACL updates). | `Disabled` (default) |
| `SourceSelectionCriteria.SseKmsEncryptedObjects` | Required if source is SSE-KMS. | Optional |
| `ExistingObjectReplication` | Nov 2022+ — replicates existing objects without Batch Operations. | `Disabled` (default) |

## Template: simple CRR (no KMS, no RTC, same account)

```json
{
  "Role": "arn:aws:iam::111111111111:role/s3-repl-role",
  "Rules": [
    {
      "ID": "crr-simple",
      "Priority": 1,
      "Status": "Enabled",
      "Filter": {"Prefix": "logs/"},
      "Destination": {"Bucket": "arn:aws:s3:::prod-logs-dr-eu-west-1"},
      "DeleteMarkerReplication": {"Status": "Disabled"}
    }
  ]
}
```

## Template: CRR with SSE-KMS source + destination, RTC enabled

```json
{
  "Role": "arn:aws:iam::111111111111:role/s3-repl-role",
  "Rules": [
    {
      "ID": "crr-kms-rtc",
      "Priority": 2,
      "Status": "Enabled",
      "Filter": {"Prefix": "logs/"},
      "Destination": {
        "Bucket": "arn:aws:s3:::prod-logs-dr-eu-west-1",
        "EncryptionConfiguration": {
          "ReplicaKmsKeyID": "arn:aws:kms:eu-west-1:111111111111:key/dest-cmk"
        },
        "ReplicationTime": {"Status": "Enabled", "Time": {"Minutes": 15}},
        "Metrics": {"Status": "Enabled", "EventThreshold": {"Minutes": 15}}
      },
      "DeleteMarkerReplication": {"Status": "Enabled"},
      "SourceSelectionCriteria": {
        "SseKmsEncryptedObjects": {"Status": "Enabled"},
        "ReplicaModifications": {"Status": "Enabled"}
      }
    }
  ]
}
```

## Template: same-region replication (SRR, backup)

```json
{
  "Role": "arn:aws:iam::111111111111:role/s3-repl-role",
  "Rules": [
    {
      "ID": "srr-backup",
      "Priority": 1,
      "Status": "Enabled",
      "Filter": {"Prefix": ""},
      "Destination": {"Bucket": "arn:aws:s3:::prod-data-backup-us-east-1"},
      "DeleteMarkerReplication": {"Status": "Enabled"},
      "ExistingObjectReplication": {"Status": "Enabled"}
    }
  ]
}
```

Note: SRR is for same-account, same-Region backup or log aggregation.
The destination Region MUST match the source Region.

## Template: cross-account CRR (account A source, account B destination)

```json
{
  "Role": "arn:aws:iam::AAAAAAAAAAAA:role/s3-repl-role",
  "Rules": [
    {
      "ID": "xaccount-audit",
      "Priority": 1,
      "Status": "Enabled",
      "Filter": {"Prefix": "audit/"},
      "Destination": {
        "Bucket": "arn:aws:s3:::audit-logs-dest",
        "Account": "BBBBBBBBBBBB",
        "AccessControlTranslation": {"Owner": "Destination"},
        "EncryptionConfiguration": {
          "ReplicaKmsKeyID": "arn:aws:kms:us-west-2:BBBBBBBBBBBB:key/dest-cmk"
        }
      },
      "DeleteMarkerReplication": {"Status": "Enabled"}
    }
  ]
}
```

This MUST be paired with the destination bucket policy AND the
destination KMS key policy (see references/diagnostic-procedures.md).

## Template: S3 Replication to multiple destinations (Nov 2022+ GA)

```json
{
  "Role": "arn:aws:iam::111111111111:role/s3-repl-multi-role",
  "Rules": [
    {
      "ID": "dest-dr-eu-west-1",
      "Priority": 2,
      "Status": "Enabled",
      "Filter": {"Prefix": "logs/"},
      "Destination": {"Bucket": "arn:aws:s3:::prod-logs-dr-eu-west-1"}
    },
    {
      "ID": "dest-audit-us-west-2",
      "Priority": 1,
      "Status": "Enabled",
      "Filter": {"Prefix": "logs/"},
      "Destination": {
        "Bucket": "arn:aws:s3:::audit-logs-dest",
        "Account": "222222222222",
        "AccessControlTranslation": {"Owner": "Destination"}
      }
    }
  ]
}
```

The same object matching `logs/` is replicated to BOTH destinations in
parallel. Costs scale linearly with destination count.

## Template: enabling delete-marker replication on an existing rule

Read the current config, then put the merged config with
`DeleteMarkerReplication.Status: Enabled`:

```bash
aws s3api get-bucket-replication --bucket <source> --output json > /tmp/repl-pre.json
# Edit /tmp/repl-pre.json: set DeleteMarkerReplication.Status = "Enabled" on the target rule
aws s3api put-bucket-replication --bucket <source> \
  --replication-configuration file:///tmp/repl-merged.json
```

## Template: enabling replica modification sync

Add `SourceSelectionCriteria.ReplicaModifications.Status: Enabled` to
the rule. Without this, tag and metadata updates on the source do NOT
propagate to existing replicas.

## IAM replication role — same-account, default encryption

Attach a policy like:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetReplicationConfiguration",
        "s3:GetObjectVersionForReplication",
        "s3:GetObjectVersionAcl",
        "s3:GetObjectVersionTagging"
      ],
      "Resource": ["arn:aws:s3:::<source>", "arn:aws:s3:::<source>/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ReplicateObject", "s3:ReplicateDelete"],
      "Resource": "arn:aws:s3:::<destination>/*"
    }
  ]
}
```

## IAM replication role — SSE-KMS source + destination

Add these KMS statements to the same role policy:

```json
{
  "Effect": "Allow",
  "Action": ["kms:Decrypt"],
  "Resource": "arn:aws:kms:<source-region>:<account>:key/<source-key-id>"
},
{
  "Effect": "Allow",
  "Action": ["kms:Encrypt"],
  "Resource": "arn:aws:kms:<dest-region>:<account>:key/<dest-key-id>"
}
```

## IAM replication role — cross-account (with ownership override)

Add `s3:ObjectOwnerOverrideToBucketOwner`:

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:ReplicateObject",
    "s3:ReplicateDelete",
    "s3:ObjectOwnerOverrideToBucketOwner"
  ],
  "Resource": "arn:aws:s3:::<destination>/*"
}
```

## IAM role for Batch Operations (S3ReplicateObject)

The Batch Operations role is SEPARATE from the bucket's replication
role. It needs read on source + replicate on destination + KMS:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:GetObjectVersion"],
      "Resource": "arn:aws:s3:::<source>/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ReplicateObject", "s3:ReplicateDelete"],
      "Resource": "arn:aws:s3:::<destination>/*"
    },
    {
      "Effect": "Allow",
      "Action": ["kms:Decrypt"],
      "Resource": "arn:aws:kms:<source-region>:<account>:key/<source-key-id>"
    },
    {
      "Effect": "Allow",
      "Action": ["kms:Encrypt", "kms:GenerateDataKey"],
      "Resource": "arn:aws:kms:<dest-region>:<account>:key/<dest-key-id>"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::<manifest-bucket>/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::<report-bucket>/*"
    }
  ]
}
```

## Destination bucket policy — cross-account replication

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::<source-account>:role/<repl-role>"},
      "Action": [
        "s3:ReplicateObject",
        "s3:ReplicateDelete",
        "s3:ObjectOwnerOverrideToBucketOwner",
        "s3:GetObjectVersion"
      ],
      "Resource": "arn:aws:s3:::<destination>/*",
      "Condition": {
        "StringEquals": {"s3:x-amz-source-account": "<source-account>"}
      }
    }
  ]
}
```

The `s3:x-amz-source-account` condition is REQUIRED — without it,
replication fails with `AccessDenied` that surfaces only in destination
CloudTrail or S3 Server Access Logs.

## Destination KMS key policy — cross-account

```json
{
  "Version": "2012-10-17",
  "Statement": [
    <existing-statements>,
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::<source-account>:role/<repl-role>"},
      "Action": ["kms:Encrypt", "kms:GenerateDataKey", "kms:DescribeKey"],
      "Resource": "*"
    }
  ]
}
```

## Batch Operations manifest from S3 Inventory

S3 Inventory generates a daily CSV manifest. The manifest object is a
JSON pointer to the CSV:

```bash
aws s3api get-object --bucket <inventory-bucket> \
  --key <inventory-path>/<source-bucket>/2026-08-09T03:00:00Z/manifest.json \
  /tmp/batch-manifest.json

cat /tmp/batch-manifest.json
# {
#   "sourceBucket": "prod-logs-source-us-east-1",
#   "destinationBucket": "...",
#   "version": "2016-11-30",
#   "files": [{"key": "...", "size": ..., "MD5checksum": "..."}]
# }

aws s3control create-job \
  --account-id <account> \
  --operation '{"S3ReplicateObject": {}}' \
  --manifest '{"Spec": {"Format": "S3InventoryReport_CSV_20161130"}, "Location": {"ObjectArn": "arn:aws:s3:::<inventory-bucket>/<path>/manifest.json", "ETag": "<etag>"}}' \
  --report '{"Bucket": "arn:aws:s3:::<report-bucket>", "Format": "Report_CSV_20180820", "Enabled": true, "ReportScope": "AllTasks"}' \
  --role-arn arn:aws:iam::<account>:role/s3-batch-repl-role \
  --client-request-token "$(uuidgen)"
```

## Common failure signatures

| Symptom | Root cause | Fix |
|---|---|---|
| Rule Enabled, zero replicates | Destination versioning OFF | Enable versioning on destination |
| `AccessDenied` in destination CloudTrail (cross-account) | Destination bucket policy missing source-account condition | Add Statement with `s3:x-amz-source-account` |
| `KMS.AccessDeniedException` | KMS key policy denies the role | Update key policy on source (Decrypt) or destination (Encrypt) key |
| Replica owned by source account | `ObjectOwnership: ObjectWriter` legacy mode | Set destination `ObjectOwnership: BucketOwnerEnforced` + add `ObjectOwnerOverrideToBucketOwner` |
| Existing objects not replicating | S3 replication only catches new PUTs | Run Batch Operations `S3ReplicateObject` job |
| Delete markers not propagating | `DeleteMarkerReplication.Status: Disabled` | Enable delete-marker replication |
| Tag updates not propagating | `ReplicaModifications.Status` missing or Disabled | Enable replica modification sync |
| Filter overlap masks a rule | Lower-Priority rule | Raise Priority of the intended rule |
| Object Lock source rejected | Destination Object Lock not enabled | Enable Object Lock on destination BEFORE retrying |
