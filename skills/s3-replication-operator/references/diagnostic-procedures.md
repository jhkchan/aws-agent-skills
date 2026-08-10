# S3 Replication Diagnostic Procedures Reference

Load this reference when diagnosing replication that is not happening
or is partially failing. The procedures below are the canonical
sequences for each symptom archetype, with the read-only diagnostic
commands and the CLI to fix each root cause.

## Decision tree — which diagnostic archetype

| Symptom | Use | Why |
|---|---|---|
| Rule `Status: Enabled` but zero objects in destination | **Silent halt** | Versioning, IAM role, KMS, or destination policy gap |
| `PendingReplication` rising, never drains | **Backlog bottleneck** | IAM/KMS/destination policy throttling replication |
| Delete markers in source, none in destination | **Delete-marker gap** | `DeleteMarkerReplication.Status: Disabled` |
| Tag updates in source, not in destination | **Replica-mod gap** | `ReplicaModifications.Status` missing or Disabled |
| Cross-account `AccessDenied` in destination CloudTrail | **Cross-account policy** | Destination bucket policy missing `s3:x-amz-source-account` |
| Some prefixes replicate, others do not | **Filter overlap** | Multiple rules, lower-Priority rule masked |
| Replication worked, then stopped after bucket change | **State change** | Versioning suspended, Object Lock enabled on source only, ownership change |
| Batch Operations job reports FAILED entries | **Batch role gap** | Batch Operations IAM role missing KMS or ReplicateObject |
| Replica is owned by source account (cross-account) | **Ownership gap** | `ObjectOwnership: ObjectWriter` + missing `ObjectOwnerOverrideToBucketOwner` |

## Procedure: Silent halt (rule Enabled, zero replicates)

**Symptom:** Source rule `Status: Enabled`; no objects in destination;
`PendingReplication` either missing (no RTC) or rising.

**Diagnostics:**

```bash
# 1. Source versioning (MUST be Enabled)
aws s3api get-bucket-versioning --bucket <source>

# 2. Destination versioning (MUST be Enabled — silent halt if not)
aws s3api get-bucket-versioning --bucket <destination>

# 3. Source location (confirm Region matches the rule's source)
aws s3api get-bucket-location --bucket <source>

# 4. Destination location
aws s3api get-bucket-location --bucket <destination>

# 5. Full replication config
aws s3api get-bucket-replication --bucket <source> --output json

# 6. IAM role permissions
aws iam list-attached-role-policies --role-name <role>
aws iam list-role-policies --role-name <role>
aws iam get-role-policy --role-name <role> --policy-name <inline-policy>

# 7. Source KMS key state + policy
aws kms describe-key --key-id <source-key>
aws kms get-key-policy --key-id <source-key> --policy-name default

# 8. Destination KMS key state + policy (commonly missed)
aws kms describe-key --key-id <destination-key>
aws kms get-key-policy --key-id <destination-key> --policy-name default

# 9. (Cross-account) Destination bucket policy
aws s3api get-bucket-policy --bucket <destination>

# 10. (RTC enabled) PendingReplication trend
aws cloudwatch get-metric-statistics \
  --namespace AWS/S3 --metric-name PendingReplication \
  --dimensions Name=SourceBucket,Value=<source> \
                Name=DestinationBucket,Value=<destination> \
  --start-time $(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Sum
```

**Common findings and fixes:**

| Finding | Fix |
|---|---|
| Source versioning OFF | `aws s3api put-bucket-versioning --bucket <source> --versioning-configuration Status=Enabled` |
| Destination versioning OFF | Same as above on the destination |
| IAM role missing `s3:ReplicateObject` on destination | Attach a policy granting `s3:ReplicateObject`, `s3:ReplicateDelete` on `arn:aws:s3:::<dest>/*` |
| IAM role missing `kms:Decrypt` on source key | Add `kms:Decrypt` grant on the source CMK ARN |
| IAM role missing `kms:Encrypt` on destination key | Add `kms:Encrypt` grant on the destination CMK ARN |
| Destination KMS key policy denies the role | Update key policy via `aws kms put-key-policy` to grant the role |
| Cross-account destination bucket policy missing source-account condition | Add a Statement with `s3:x-amz-source-account` condition for the source account ID |
| Rule `Status: Disabled` | Update rule with `Status: Enabled` |
| Filter prefix does not match any objects | Update the prefix or add a Tag filter that matches |

## Procedure: Backlog bottleneck (PendingReplication rising)

**Symptom:** RTC enabled; `PendingReplication` is non-zero and rising;
`OperationPendingReplicationCount` is also rising.

**Diagnostics:**

```bash
# 1. PendingReplication trend (last 24h)
aws cloudwatch get-metric-statistics \
  --namespace AWS/S3 --metric-name PendingReplication \
  --dimensions Name=SourceBucket,Value=<source> \
                Name=DestinationBucket,Value=<destination> \
  --start-time $(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Sum

# 2. BytesPendingReplication (size of backlog)
aws cloudwatch get-metric-statistics \
  --namespace AWS/S3 --metric-name BytesPendingReplication \
  --dimensions Name=SourceBucket,Value=<source> \
                Name=DestinationBucket,Value=<destination> \
  --start-time $(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Sum

# 3. OperationPendingReplicationCount (count of objects)
aws cloudwatch get-metric-statistics \
  --namespace AWS/S3 --metric-name OperationPendingReplicationCount \
  --dimensions Name=SourceBucket,Value=<source> \
                Name=DestinationBucket,Value=<destination> \
  --start-time $(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Sum

# 4. Destination S3 Server Access Logs (look for AccessDenied)
aws s3api select-object-content \
  --bucket <access-logs-bucket> --key <log-key> \
  --expression "SELECT * FROM s3object s WHERE s.\"Operation\" = 'Replication.PutObject' AND s.\"HTTPStatus\" LIKE '4%' OR s.\"HTTPStatus\" LIKE '5%'" \
  --input-serialization '{"CSV": {}, "CompressionType": "GZIP"}' \
  --output-serialization '{"CSV": {}}' /tmp/replication-errors.csv
```

**Common findings:**

| Finding | Fix |
|---|---|
| Burst of PUTs overwhelming replication throughput | Transient — backlog should drain within RTC SLA (15 min) |
| Persistent backlog with no AccessDenied | Throttling on the destination KMS key — request a quota increase |
| Intermittent AccessDenied on destination | Destination bucket policy or KMS key policy gap on cross-account |
| Backlog started after KMS key rotation | New key version not granted to the role — update key policy |

## Procedure: Delete-marker / replica-modification gap

**Symptom:** Object replication works but delete markers or metadata
updates do not propagate.

**Diagnostics:**

```bash
aws s3api get-bucket-replication --bucket <source> --output json | \
  jq '.ReplicationConfiguration.Rules[] |
      {ID, DeleteMarkerReplication, SourceSelectionCriteria}'
```

**Common findings and fixes:**

| Finding | Fix |
|---|---|
| `DeleteMarkerReplication.Status: Disabled` | Update rule: `DeleteMarkerReplication: {Status: Enabled}` |
| `DeleteReplication.Status: Disabled` (for versioned DELETEs) | Update rule: `DeleteReplication: {Status: Enabled}` |
| `SourceSelectionCriteria.ReplicaModifications.Status` missing | Add `ReplicaModifications: {Status: Enabled}` for metadata sync |
| Filter excludes the deleted/metadata-updated objects | Update the rule's Filter to include the affected keys |

## Procedure: Cross-account triple-policy audit

**Symptom:** Cross-account replication fails with `AccessDenied` in
destination CloudTrail. There are THREE policy surfaces to verify.

**Audit checklist:**

1. **IAM role (identity-based, in source account):**
   ```bash
   aws iam get-role --role-name <role>
   aws iam list-attached-role-policies --role-name <role>
   aws iam list-role-policies --role-name <role>
   ```
   Verify the role has `s3:ReplicateObject`,
   `s3:ReplicateDelete`, `s3:ObjectOwnerOverrideToBucketOwner` on
   `arn:aws:s3:::<dest>/*`.

2. **Destination bucket policy (resource-based, in destination account):**
   ```bash
   aws s3api get-bucket-policy --bucket <destination>
   ```
   Verify the policy has a Statement with:
   - `Principal: {AWS: <source-role-arn>}`
   - `Action: [s3:ReplicateObject, s3:ReplicateDelete, s3:ObjectOwnerOverrideToBucketOwner]`
   - `Condition: {StringEquals: {"s3:x-amz-source-account": "<source-account-id>"}}`

3. **Destination KMS key policy (in destination account):**
   ```bash
   aws kms get-key-policy --key-id <destination-key> --policy-name default
   ```
   Verify the policy grants the source role `kms:Encrypt` and
   `kms:GenerateDataKey`.

**Fix template — destination bucket policy (cross-account):**

```bash
aws s3api put-bucket-policy --bucket <destination> --policy '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::<source-account>:role/<role>"},
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
}'
```

**Fix template — destination KMS key policy (cross-account):**

```bash
aws kms put-key-policy --key-id <destination-key> --policy-name default --policy '{
  "Version": "2012-10-17",
  "Statement": [
    <existing-statements>,
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::<source-account>:role/<role>"},
      "Action": ["kms:Encrypt", "kms:GenerateDataKey", "kms:DescribeKey"],
      "Resource": "*"
    }
  ]
}'
```

## Procedure: Filter overlap (partial replication)

**Symptom:** Objects under some prefixes replicate; others do not.

**Diagnostics:**

```bash
# List all rules sorted by Priority
aws s3api get-bucket-replication --bucket <source> --output json | \
  jq '.ReplicationConfiguration.Rules | sort_by(.Priority)'
```

**Common findings:**

| Finding | Fix |
|---|---|
| Two rules with overlapping prefixes; lower-Priority rule masked | Disambiguate the filters or raise the Priority of the intended rule |
| Rule A (Priority 1, prefix "logs/") masks Rule B (Priority 2, prefix "logs/audit/") | Raise Rule B's Priority above Rule A's |
| Tag filter mismatches object tags | Verify the object actually has the tag key/value; tags are case-sensitive |

## Procedure: Batch Operations job FAILED entries

**Symptom:** A Batch Operations `S3ReplicateObject` job completed with
non-zero `Failed` count.

**Diagnostics:**

```bash
# 1. Job status + failure summary
aws s3control describe-job \
  --account-id <account> --job-id <job-id>

# 2. Download the completion report (FAILED entries)
aws s3 cp s3://<report-bucket>/<job-id>/results/<csv> /tmp/batch-failed.csv
# Inspect the failure reasons (AccessDenied, KMS.AccessDeniedException, NotFound, etc.)
```

**Common findings:**

| Finding | Fix |
|---|---|
| Batch role missing `s3:GetObject` on source | Add `s3:GetObject` on `arn:aws:s3:::<source>/*` |
| Batch role missing `kms:Decrypt` on source key | Add KMS grant |
| Batch role missing `kms:Encrypt` on destination key | Add KMS grant |
| Manifest includes deleted objects | Filter the manifest by `ReplicationStatus != COMPLETED` before re-running |

## Diagnostic command quick-reference

| Goal | Command |
|---|---|
| Replication config | `aws s3api get-bucket-replication --bucket <source>` |
| Source versioning | `aws s3api get-bucket-versioning --bucket <source>` |
| Destination versioning | `aws s3api get-bucket-versioning --bucket <destination>` |
| Source Region | `aws s3api get-bucket-location --bucket <source>` |
| Source encryption | `aws s3api get-bucket-encryption --bucket <source>` |
| Destination ObjectOwnership | `aws s3api get-bucket-ownership-controls --bucket <destination>` |
| Destination bucket policy | `aws s3api get-bucket-policy --bucket <destination>` |
| Source KMS key state | `aws kms describe-key --key-id <source-key>` |
| Source KMS key policy | `aws kms get-key-policy --key-id <source-key> --policy-name default` |
| Destination KMS key policy | `aws kms get-key-policy --key-id <destination-key> --policy-name default` |
| PendingReplication (RTC) | `aws cloudwatch get-metric-statistics --namespace AWS/S3 --metric-name PendingReplication --dimensions ...` |
| Batch Operations status | `aws s3control describe-job --account-id <account> --job-id <id>` |
| Apply merged replication config | `aws s3api put-bucket-replication --bucket <source> --replication-configuration file://<merged>.json` |
| Enable versioning | `aws s3api put-bucket-versioning --bucket <bucket> --versioning-configuration Status=Enabled` |
| Update destination bucket policy | `aws s3api put-bucket-policy --bucket <destination> --policy file://<policy>.json` |
| Create Batch Operations job | `aws s3control create-job --account-id <account> --operation '{"S3ReplicateObject": {}}' --manifest ... --report ... --role-arn ...` |

## Failure-mode to operation routing

| Failure mode | Recommended operation | Notes |
|---|---|---|
| Rule Enabled, no replicates | diagnose-not-replicating | Check versioning on BOTH buckets first |
| Cross-account AccessDenied | configure-cross-account | Verify all three policy surfaces |
| Existing objects not replicating | batch-replicate | S3 Replication only catches new PUTs |
| Delete markers not propagating | enable-delete-marker-replication | Set `DeleteMarkerReplication.Status: Enabled` |
| Tag/metadata updates not propagating | update-rule | Add `ReplicaModifications.Status: Enabled` |
| Filter overlap masking a rule | update-rule | Sort by Priority; raise intended rule |
| Replicas owned by source account | configure-cross-account | Switch ObjectOwnership to BucketOwnerEnforced |
