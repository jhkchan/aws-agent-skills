# Batch Operations and Lifecycle Integration Reference

Load this reference when planning a bulk restore via S3 Batch
Operations or when integrating restores with lifecycle policies.

## S3 Batch Operations — bulk restore workflow

### Manifest formats

| Format | Use case |
|---|---|
| `S3BatchOperations_CSV_20180820` | CSV with `bucket,key` (and optional `versionId`) per line |
| `S3InventoryReport_csv_20161130` | S3 Inventory report (daily or weekly) as the manifest |
| Tag-based (2025+) | Manifest generated from S3 resource tags at job creation |

For DR-class restores, prefer S3 Inventory reports — they are
already filtered and versioned.

### Manifest bucket policy

The manifest bucket must grant the Batch Operations service principal
read access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "batchoperations.s3.amazonaws.com"},
      "Action": ["s3:GetObject", "s3:GetBucketLocation"],
      "Resource": ["arn:aws:s3:::batch-ops-manifests", "arn:aws:s3:::batch-ops-manifests/*"]
    }
  ]
}
```

### Job role policy

The job role needs permissions on the target bucket(s) and the
report bucket:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:RestoreObject", "s3:GetObject", "s3:GetObjectVersion"],
      "Resource": ["arn:aws:s3:::prod-archive-bucket/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": ["arn:aws:s3:::batch-ops-reports/*"]
    }
  ]
}
```

The caller (the IAM user/role creating the job) needs
`iam:PassRole` on the job role ARN.

### Job priority

- Priority 1 (highest) for DR drills.
- Priority 10 (default) for routine bulk restores.
- Higher-priority jobs pre-empt lower-priority jobs in the same
  account-region pair.

### Job monitoring commands

```bash
# Describe a job
aws s3control describe-job --account-id <account> --job-id <job-id>

# Wait for terminal state
aws s3control describe-job --account-id <account> --job-id <job-id> \
  --query 'Job.Status'

# List jobs filtered by operation
aws s3control list-jobs --account-id <account> \
  --operation S3RestoreObject \
  --job-status Active,Complete,Failed

# Update job priority (pre-empt)
aws s3control update-job-priority --account-id <account> \
  --job-id <job-id> --priority 1

# Cancel a job (only if New, Suspended, or Ready)
aws s3control update-job-status --account-id <account> \
  --job-id <job-id \
  --requested-job-status CANCELLED
```

### Reading the report

The completion report is CSV in the report bucket:

```csv
JobId,TaskId,Key,VersionId,TaskStatus,ErrorCode,HTTPStatusCode
1234abcd-...,001,reports/Q1.parquet,,Succeeded,,200
1234abcd-...,002,reports/Q2.parquet,,Succeeded,,200
1234abcd-...,003,reports/old.parquet,,Failed,NoSuchKey,404
```

Use `aws s3 ls` and `aws s3 cp` to fetch and parse the report. The
`TaskStatus` field drives re-run decisions.

## Lifecycle integration

### The re-archival foot-gun

If the bucket has a lifecycle rule that transitions objects to
Glacier, restored objects are still subject to that rule. After the
rule's `Days` threshold, the object re-archives — undoing the
restore and breaking workflows.

### Lifecycle rule structure

```json
{
  "Rules": [
    {
      "ID": "archive-after-90d",
      "Status": "Enabled",
      "Filter": {"Prefix": "logs/"},
      "Transitions": [{"Days": 90, "StorageClass": "GLACIER"}],
      "NoncurrentVersionTransitions": [
        {"NoncurrentDays": 30, "StorageClass": "GLACIER"}
      ]
    }
  ]
}
```

### Preventing re-archival of promoted objects

**Option 1 — filter exclusion:**
Update the rule's filter to exclude the promoted prefix:

```json
"Filter": {"Prefix": "logs/"}
```

If promoted objects live under `promoted/`, they are not matched by
the rule.

**Option 2 — tag-based exclusion:**
Use a tag filter:

```json
"Filter": {"Tag": {"Key": "Permanent", "Value": "true"}}
```

And exclude tagged objects via a separate rule with `Expiration` or
no transition.

**Option 3 — separate bucket:**
Copy promoted objects to a bucket without archive rules. Cleanest
separation but adds a copy operation.

### Lifecycle rule validation

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket prod-archive-bucket \
  --lifecycle-configuration file://lifecycle.json
```

AWS validates rule syntax and non-overlapping rule detection (2024+).
Overlapping rules are rejected. Pre-2024 deployments may have silent
churn — re-validate after upgrade.

### Noncurrent version handling

`NoncurrentVersionTransitions` archives noncurrent (older) versions.
Restoring a noncurrent version requires specifying `--version-id` on
`restore-object`:

```bash
aws s3api restore-object --bucket prod-archive-bucket \
  --key quarterly-report.parquet \
  --version-id "<version-id>" \
  --restore-request '{"Days":7,"GlacierJobParameters":{"Tier":"Standard"}}'
```

Without `--version-id`, the operation targets the current version,
which may not be archived.

## DR drill integration

### Pre-drill checklist

1. Identify the manifest (objects to restore).
2. Provision Expedited capacity in the source region.
3. Verify the IAM role has `s3:RestoreObject` on the target bucket.
4. Document the RTO and emit it in the operation notes.
5. Capture the start time for SLA measurement.

### During the drill

1. Issue the restore(s) at T=0.
2. Poll `head-object Restore.ongoing-request` every minute for
   Expedited, every 30 min for Standard/Bulk.
3. On completion, verify readability via `get-object`.
4. Record elapsed time vs RTO.

### Post-drill

1. Capture expiry-date of restored objects.
2. Copy or promote objects that need to remain accessible.
3. Update the runbook with lessons learned.

## Common failure modes

| Failure | Symptom | Fix |
|---|---|---|
| Wrong tier for source class | `restore-object` returns 400 | Re-tier per the compatibility matrix |
| On-demand Expedited rejected | Restore fails during demand peak | Provision capacity |
| Object re-archived after promotion | GetObject fails after Days=N | Update lifecycle rule or copy to Standard |
| Batch Operations job stuck Active | describe-job never reaches Complete | Check manifest ETag, IAM role, NoSuchKey in report |
| Restore on GIR object | No-op or error | Skip restore; use GetObject directly |
| Restore on versioned object targets wrong version | Restored version not the archived one | Specify --version-id |
| Restore expires mid-use | GetObject fails on day N+1 | Use longer Days or copy-to-tier |
