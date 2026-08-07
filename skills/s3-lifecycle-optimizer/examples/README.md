# End-to-end usage scenario: s3-lifecycle-optimizer

A walkthrough showing the skill optimising a versioned logs bucket that has
no lifecycle policy, 40% noncurrent bytes, and 14 stale multipart uploads —
demonstrating the priority-ordered dimension analysis (noncurrent cleanup,
multipart abort, storage-class transitions, expiration), the dollar
savings estimate net of minimum-duration charges, and the CONFIRM gate
before `put-bucket-lifecycle-configuration`.

## Input (user prompt)

> Our app-logs-prod bucket is costing us $446/month. Can you design a
> lifecycle policy and tell me what we'd save?

```json
{
  "Bucket": "app-logs-prod",
  "Region": "us-east-1",
  "Versioning": "Enabled",
  "ObjectLock": "not configured",
  "LifecycleConfiguration": null,
  "StorageLens": {
    "window": "last 30 days",
    "total_storage_bytes": 20000000000000,
    "noncurrent_bytes": 8000000000000,
    "noncurrent_pct": 40,
    "storage_class_distribution": {"Standard": 100},
    "average_object_age_days": 95
  },
  "KeyPrefixLayout": ["logs/", "application/", "archive/"],
  "IncompleteMultipartUploads": {"older_than_7d": 14}
}
```

## Skill output

```text
BUCKET: app-logs-prod
VERDICT: OPPORTUNITY_FOUND
REASON: Bucket is versioned with 8 TB noncurrent bytes (40% of total) and no
lifecycle policy (Step 1, Step 2, Step 3, Step 4). All 20 TB sit in Standard
at $0.023/GB-mo. 14 multipart uploads older than 7 days are leaking parts.
RECOMMENDATION:
  {
    "Rules": [
      {
        "ID": "logs-lifecycle",
        "Status": "Enabled",
        "Filter": {"Prefix": "logs/"},
        "Transitions": [
          {"Days": 30, "StorageClass": "STANDARD_IA"},
          {"Days": 90, "StorageClass": "GLACIER_IR"},
          {"Days": 180, "StorageClass": "GLACIER"}
        ],
        "Expiration": {"Days": 365}
      },
      {
        "ID": "noncurrent-version-cleanup",
        "Status": "Enabled",
        "Filter": {},
        "NoncurrentVersionTransitions": [
          {"NoncurrentDays": 30, "NewNoncurrentStorageClass": "STANDARD_IA"},
          {"NoncurrentDays": 90, "NewNoncurrentStorageClass": "GLACIER_IR"}
        ],
        "NoncurrentVersionExpiration": {"NoncurrentDays": 180}
      },
      {
        "ID": "abort-incomplete-multipart-uploads",
        "Status": "Enabled",
        "Filter": {},
        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7}
      }
    ]
  }
SAVINGS:
  CURRENT_MONTHLY: $460.00  (20,000 GB × $0.023)
  PROJECTED_MONTHLY: $124.95
    - 7,000 GB current Standard × $0.023 = $161.00
    - 4,000 GB current Standard-IA × $0.0125 = $50.00
    - 1,000 GB current Glacier IR × $0.004 = $4.00
    - 8,000 GB noncurrent Glacier IR × $0.004 = $32.00 (after 90d transition)
    - minus 5,000 GB of objects expiring at 365d within 6 months = -$122.05
      amortised over the first 6 months
  MONTHLY_SAVING: $335.05 (~73% reduction)
  ANNUAL_SAVING: $4,020.60
  CAVEATS:
    - Standard-IA 30-day minimum: objects deleted before day 30 still bill.
    - Glacier IR 90-day minimum applies.
    - Glacier IR retrieval is $0.03/GB if logs are queried — budget separately.
    - Lifecycle transitions are asynchronous (24h typical); do not alarm on lag.
IMPLEMENTATION:
  1. CONFIRM: About to put-bucket-lifecycle-configuration on bucket
     app-logs-prod in account <acct> region us-east-1. This enables 3 rules
     (logs-lifecycle, noncurrent-cleanup, multipart-abort). Proceed? (yes/no)
  2. aws s3api put-bucket-lifecycle-configuration --bucket app-logs-prod \
       --lifecycle-configuration file://lifecycle.json
  3. Verify: aws s3api get-bucket-lifecycle-configuration --bucket app-logs-prod
  4. Backfill existing Standard objects older than 30 days via S3 Batch
     Operations (lifecycle only transitions new objects going forward):
     aws s3control create-job --account-id <acct> \
       --operation '{"S3CopyObject": {"TargetStorageClass": "STANDARD_IA"}}' \
       --manifest-location s3://manifest-bucket/manifest.json \
       --report-spec '{"ReportFormat":"Report_2026-08-07",...}"
```

## What the skill caught that a generic assistant misses

1. **Noncurrent-version dimension is the headline.** A generic assistant
   proposes a single transition rule to Standard-IA and stops. The skill
   catches that 40% of the bucket's bytes are noncurrent versions on a
   versioned bucket with no `NoncurrentVersionExpiration` rule — that
   dimension alone is ~$160/month of the savings.

2. **Multipart upload abort rule.** A generic assistant mentions multipart
   "in passing" or recommends a manual cleanup loop. The skill produces the
   exact lifecycle rule (`AbortIncompleteMultipartUpload`) that prevents
   future leaks and immediately aborts the 14 existing ones.

3. **Dollar estimate net of minimum-duration charges.** A generic assistant
   says "you'll save money." The skill computes the projected monthly cost
   per storage class, surfaces the 30-day and 90-day minimum-duration
   caveats, and warns that Glacier IR retrieval is $0.03/GB on read.

4. **Backfill via S3 Batch Operations.** A generic assistant applies the
   lifecycle rule and waits months for objects to age into the cheaper
   tiers. The skill notes that lifecycle only applies to objects going
   forward and pairs the recommendation with `s3control create-job` for
   immediate backfill of existing objects.

5. **CONFIRM gate before applying.** A generic assistant emits the put-bucket-
   lifecycle command directly. The skill emits `CONFIRM:` and waits for
   operator approval — a wrong prefix can mass-transition or mass-delete
   objects irreversibly.

6. **Object Lock / directory bucket pre-flight.** The skill would have
   surfaced a CONFIG finding if Object Lock retention conflicted with the
   proposed `Expiration` rule, and would have skipped the lifecycle dimension
   entirely if the bucket were a directory bucket (S3 Express One Zone) —
   directory buckets do not support lifecycle.

## Slash-command invocation

```
/aws:optimize-s3-lifecycle
```

Or via the orchestrator:

```
/aws:pipeline
You: "design a lifecycle policy for app-logs-prod and project savings"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: s3-lifecycle-optimizer]` and hands off
to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "optimise S3 storage cost on app-logs-prod"
# [Phase: Optimize | Skills routed: s3-lifecycle-optimizer]
```

## Live-account follow-up (optional, requires AWS CLI)

After applying the lifecycle, validate the posture:

```bash
# Verify the lifecycle rules are in place
aws s3api get-bucket-lifecycle-configuration --bucket app-logs-prod \
  --profile default --output json

# Confirm no incomplete multipart uploads remain
aws s3api list-multipart-uploads --bucket app-logs-prod \
  --profile default --output json

# Re-check Storage Lens after 30 days for the noncurrent-byte trend
aws s3control get-storage-lens-configuration --config-id default \
  --account-id 111111111111 --profile default
```

Then monitor S3 Storage Lens daily export for the storage-class distribution
shift and confirm the projected monthly cost reduction over the first 30-90
days as transitions execute.
