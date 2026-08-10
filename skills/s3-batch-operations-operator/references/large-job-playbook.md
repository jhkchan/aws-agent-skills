# S3 Batch Operations — Large-Job Playbook (100M – Billion+ Objects)

Load this reference when planning a job against a manifest with 100
million or more objects. At this scale, rate control, KMS quotas,
report size, and manifest generation become first-class risks.

## Scaling boundaries

| Object count | Default strategy | Key risk |
|---|---|---|
| < 1M | Auto-scale, no explicit rate limit | Minimal |
| 1M – 100M | Explicit `RequestsPerSecond`, `FailedTasksOnly` report | KMS quota on SSE-KMS buckets |
| 100M – 1B | Explicit `RequestsPerSecond` + CloudWatch alarms + KMS quota uplift | Throttling cascades; multi-day runtime |
| > 1B | Split manifest into multiple jobs by prefix/shard | Single-job runtime exceeds practical limits |

## Rate-control planning

`RequestsPerSecond` caps the per-second object-processing rate. The
right value depends on:

1. **Source bucket request budget.** S3 sustains 3,500 PUT/s and 5,500
   GET/s per prefix by default; higher with partition spread. A copy
   job consumes 1 GET + 1 PUT per object.
2. **Destination bucket request budget.** Same limits apply on the
   destination.
3. **KMS request quota.** Each SSE-KMS object consumes 1 Decrypt
   (source) + 1 Encrypt (destination for copy / re-encrypt). Default
   account quota is 5,500 / 10,000 / variable by Region. Request a
   quota lift BEFORE the job.
4. **Lambda concurrency (invoke operations).** Reserved concurrency
   must be ≥ `RequestsPerSecond`.

### Worked example — 1B object re-encrypt

- Source: 1B objects in `prod-data`, SSE-KMS with old key
- Operation: copy + new SSE-KMS key (in-place re-encrypt)
- Rate: 1,000 RPS
- KMS volume: 1,000 Decrypt/s + 1,000 Encrypt/s = 2,000 KMS requests/s
- ETA: 1,000,000,000 / 1,000 = 1,000,000 s ≈ 11.6 days

Set `CompletionWindow: P30D` (30 days) to allow for retries and
planned pauses. Split into 10 prefix-scoped jobs of 100M each for
better isolation and parallelism.

## KMS quota uplift

```bash
# Check current quota
aws service-quotas get-service-quota \
  --service-code kms \
  --quota-id L-InitialAccountThrottling

# Request a quota increase (if needed)
aws service-quotas request-service-quota-increase \
  --service-code kms \
  --quota-id L-InitialAccountThrottling \
  --desired-value 20000
```

Process the quota lift BEFORE the job — quota increases can take hours
to days depending on the Region and current usage.

## Manifest generation for billion-object jobs

S3 inventory reports run daily or weekly. For a one-off bulk job,
generate the manifest via S3 inventory (preferred) or a custom
`ListObjectsV2` paginator (slow but flexible).

### Use S3 inventory (preferred)

```bash
aws s3api put-bucket-inventory-configuration \
  --bucket prod-data \
  --id bulk-reencrypt-manifest \
  --inventory-configuration '{
    "Destination": {"Bucket": "arn:aws:s3:::prod-inventory", "Prefix": "bulk-reencrypt/", "Format": "CSV"},
    "IsEnabled": true,
    "Id": "bulk-reencrypt-manifest",
    "IncludedObjectVersions": "All",
    "Schedule": {"Frequency": "Daily"},
    "OptionalFields": ["Size", "LastModifiedDate", "StorageClass"]
  }'
```

Wait for the next inventory run (up to 24 hours), then point the job
manifest at the generated `manifest.json` + `manifest.checksum`.

### Shard the manifest by prefix

For > 1B objects, shard the job:

```bash
# Shard 1: keys starting with a-h
# Shard 2: keys starting with i-p
# Shard 3: keys starting with q-z
```

Each shard runs as an independent job with its own manifest, report
prefix, and priority. This isolates failures, allows partial re-runs,
and avoids a single 11-day runtime.

## Completion report strategy

- **Use `FailedTasksOnly`** for any job over 1M objects. A `Task`-scope
  report produces one row per object — a multi-GB CSV for billion-
  object jobs.
- **Read the report via S3 Select** for fast filtering:
  ```bash
  aws s3api select-object-content \
    --bucket prod-batch-reports \
    --key bulk-reencrypt/result/<job-id>/results.csv \
    --expression "SELECT * FROM s3object s WHERE s._4 != ''" \
    --expression-type SQL \
    --input-serialization '{"CSV": {}, "CompressionType": "None"}' \
    --output-serialization '{"CSV": {}}' \
    /dev/stdout
  ```

## CloudWatch alarm template

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name batchops-<job-id>-failures \
  --namespace AWS/S3Operations \
  --metric-name NumberOfTasksFailed \
  --dimensions Name=JobId,Value=<job-id> \
  --threshold 100 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --period 300 --evaluation-periods 1
```

For KMS throttles during the job window:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name batchops-<job-id>-kms-throttles \
  --namespace AWS/KMS \
  --metric-name Throttles \
  --dimensions Name=KeyId,Value=<key-id> \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --period 300 --evaluation-periods 1
```

## Cancel-and-restart protocol

For a runaway job:

```bash
aws s3control update-job-status \
  --account-id <account> \
  --job-id <id> \
  --requested-job-status Cancelled \
  --status-update-reason "Throttle cascade — cancelling to preserve production traffic"
```

Cancellation is async. Poll `describe-job` until `Status: Cancelled`.
The completion report will include all objects processed before
cancellation.

For partial re-runs, extract the `FAILED` entries from the completion
report into a new CSV manifest and create a follow-up job at a lower
rate.

## Failure-code triage for large jobs

| Failure code | Expected % in a healthy large job | Action |
|---|---|---|
| `NoSuchKey` | < 0.01% (objects deleted between manifest and processing) | Acceptable; no action |
| `AccessDenied` | 0% | Role or KMS gap; cancel and fix |
| `SlowDown` / `Throttling` | < 0.1% | Lower rate; re-run failures |
| `Transient` | < 0.1% | Acceptable; auto-retried |
| `Timeout` (Lambda) | < 0.1% | Raise Lambda timeout; re-run failures |

Treat any failure code exceeding its threshold as a stop condition:
cancel the job, diagnose, and re-run at a lower rate.
