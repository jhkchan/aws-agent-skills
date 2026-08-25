# Error Handling — OpenSearch Snapshot Troubleshooter
Error-handling deep dives and API error tables, moved verbatim from SKILL.md.

## Remediation guidance
### For REPOSITORY_REGISTRATION — repository not registered

```bash
curl -X PUT "https://$ENDPOINT/_snapshot/<repo>" -H 'Content-Type: application/json' -d '
{"type": "s3", "settings": {
  "bucket": "<bucket>", "region": "<bucket-region>",
  "base_path": "<prefix>",
  "iam_role_arn": "arn:aws:iam::<account>:role/<role>",
  "compress": true}}'
curl -sS "https://$ENDPOINT/_snapshot/<repo>" | jq '.'
```

### For REPOSITORY_VERIFICATION — verification failed

1. Update the bucket policy (see IAM_ROLE_S3_ACCESS).
2. Re-run verification:
   ```bash
   curl -X POST "https://$ENDPOINT/_snapshot/<repo>/_verify?verbose=true"
   ```
3. If verification still fails, delete and re-register (CONFIRM first).

### For IAM_ROLE_S3_ACCESS — role or bucket policy missing

```bash
# Bucket policy granting the snapshot role
aws s3api put-bucket-policy --bucket <bucket> --policy '{
  "Version": "2012-10-17",
  "Statement": [
    {"Sid": "ListBucketForSnapshot", "Effect": "Allow",
     "Principal": {"AWS": "arn:aws:iam::<account>:role/<role>"},
     "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
     "Resource": "arn:aws:s3:::<bucket>"},
    {"Sid": "ReadWriteSnapshotObjects", "Effect": "Allow",
     "Principal": {"AWS": "arn:aws:iam::<account>:role/<role>"},
     "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
     "Resource": "arn:aws:s3:::<bucket>/<prefix>/*"}
  ]}'
# SSE-KMS: add kms:Decrypt and kms:GenerateDataKey to the role
aws iam put-role-policy --role-name <role-name> --policy-name KmsAccess \
  --policy-document '{"Version": "2012-10-17", "Statement": [
    {"Effect": "Allow", "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
     "Resource": "<kms-key-arn>"}]}'
```

Verify with `simulate-principal-policy`.

### For SNAPSHOT_TIMEOUT — snapshot stuck

1. Resolve cluster health (red → yellow → green).
2. Raise `thread_pool.snapshot.size` if saturated.
3. Stop competing snapshots in the same repository.
4. Cancel the snapshot if it cannot complete (CONFIRM first):
   ```bash
   curl -X DELETE "https://$ENDPOINT/_snapshot/<repo>/<snap>"
   ```

### For RESTORE_VERSION_CONFLICT — target version too low

```bash
aws opensearch update-domain-config --domain-name <domain> \
  --engine-version OpenSearch_<target> --profile <p>
# Wait for UpgradeStatus: Succeeded, then retry restore
```

### For RESTORE_ALIAS_CONFLICT — alias or index exists

```bash
curl -X POST "https://$ENDPOINT/_snapshot/<repo>/<snap>/_restore" \
  -H 'Content-Type: application/json' -d \
  '{"indices": "<pattern>", "rename_pattern": "<from>", "rename_replacement": "<to>"}'
# Or delete the conflict (CONFIRM first):
curl -X DELETE "https://$ENDPOINT/<index-or-alias>"
```

### For COLD_STORAGE_MIGRATION — warm/cold misconfig

```bash
aws opensearch update-domain-config --domain-name <domain> \
  --cluster-config WarmEnabled=true,WarmCount=3,WarmType=ultrawarm1.medium.search --profile <p>
curl -X PUT "https://$ENDPOINT/<index>/_settings" -H 'Content-Type: application/json' -d \
  '{"index": {"number_of_replicas": 1}}'
# Wait for green, then retry the migration via ISM
```

### For S3_LIFECYCLE_DELETION — lifecycle expires snapshots

```bash
aws s3api get-bucket-lifecycle-configuration --bucket <bucket> --output json > lifecycle.json
# Edit to scope/expire the rule, then:
aws s3api put-bucket-lifecycle-configuration --bucket <bucket> \
  --lifecycle-configuration file://lifecycle-merged.json
# Re-take snapshots that were lost
```

### For CROSS_REGION_REPLICATION — async replication stall

1. Verify `index.plugins.replication.enabled: true` on leader.
2. Verify follower write block is off and follower engine >= leader.
3. Resume replication: `curl -X POST "https://$FOLLOWER/_plugins/_replication/<index>/_resume"`

### For SHARD_ALLOCATION_RESTORE — recovery throttling

Raise `cluster.routing.allocation.node_concurrent_recoveries` (default 2)
and `indices.recovery.max_bytes_per_sec` (default 40mb). Watch
`_cat/recovery` for 100%.

### For MANIFEST_CORRUPTION — corrupt blob

1. `DELETE _snapshot/<repo>/<snap>` (CONFIRM first).
2. Re-take a fresh snapshot; new snapshot uses healthy segments.
3. If repository metadata itself is corrupt, re-register against a
   clean prefix and re-take all snapshots.

### For CONCURRENT_SNAPSHOT_LIMIT — second snapshot blocked

Wait for the in-flight snapshot, OR cancel it (CONFIRM first).
Reschedule the manual cadence to avoid the automated snapshot hour,
or use a different repository/prefix.

### For CUR_AUDIT_LOG_CONFIG — audit logs missing

```bash
aws opensearch update-domain-config --domain-name <domain> \
  --log-publishing-options AuditLogsEnabled=true,CloudWatchLogsLogGroupArn="<log-group-arn>" --profile <p>
# Then configure CloudWatch Logs → S3 export (subscription filter to Firehose)
```
