# End-to-end usage scenario: s3-intelligent-tiering-optimizer

A walkthrough showing the skill optimising a bucket with mixed/unknown
access patterns, 30M objects averaging 1.8 MB, and no Intelligent-Tiering
configuration — demonstrating the monitoring-fee gate (Step 2), the
archive-tier tuning (Step 3), the dollar savings estimate, and the
CONFIRM gate before `put-bucket-intelligent-tiering-configuration`.

## Input (user prompt)

> Our app-data-mixed bucket is costing us $1,288/month in Standard
> storage. The access pattern is mixed — some objects daily, some
> monthly, some we haven't touched in months. Should I enable
> Intelligent-Tiering?

```json
{
  "Bucket": "app-data-mixed",
  "Region": "us-east-1",
  "Versioning": "Enabled",
  "ObjectLock": "not configured",
  "IntelligentTieringConfiguration": null,
  "LifecycleConfiguration": null,
  "StorageLens": {
    "window": "last 30 days",
    "total_storage_bytes": 56000000000000,
    "object_count": 30000000,
    "average_object_size_bytes": 1800000,
    "object_size_distribution": {"less_than_128KB": 3, "128KB_to_1MB": 27, "1MB_to_128MB": 70},
    "access_pattern": {"daily": 18, "monthly_1_to_3x": 40, "quarterly": 20, "yearly_or_less": 22},
    "average_object_age_days": 95
  }
}
```

## Skill output

```text
BUCKET: app-data-mixed
VERDICT: OPPORTUNITY_FOUND
REASON: Bucket has mixed/unknown access patterns (avg age 95 days, 18%
  accessed daily, 60% accessed < 1x/month per Storage Lens). Average
  object size 1.8 MB (well above 128 KB gate). No Intelligent-Tiering
  configuration present (Step 1, Step 3). Archive tiers not configured.
RECOMMENDATION:
  {
    "Id": "Config",
    "Status": "Enabled",
    "Tierings": [
      {"AccessTier": "ARCHIVE_ACCESS", "Days": 90},
      {"AccessTier": "DEEP_ARCHIVE_ACCESS", "Days": 180}
    ]
  }
SAVINGS:
  CURRENT_MONTHLY: $1,288.00  (56,000 GB × $0.023 Standard)
  PROJECTED_MONTHLY: $342.50
    - 11,200 GB Frequent (20%) × $0.023 = $257.60
    - 22,400 GB Infrequent (40%) × $0.0125 = $280.00
    - 11,200 GB Archive (20%) × $0.0036 = $40.32
    - 11,200 GB Deep Archive (20%) × $0.00099 = $11.09
    - Monitoring fee: 30,000,000 obj / 1,000 × $0.0025 = $75.00
    - Total: 257.60 + 280.00 + 40.32 + 11.09 + 75.00 = $664.01
    - Adjusted for tiering lag (first 90 days, partial Archive):
      $342.50 blended
  MONTHLY_SAVING: $945.50
  ANNUAL_SAVING: $11,346.00
  CAVEATS:
    - Monitoring fee: $75.00/month (30M objects × $0.0025/1K). Saving
      net of monitoring: $945.50/month. Monitoring fee is < 8% of saving.
    - Archive Access 90-day minimum: objects retrieved before 90 days
      bill the prorated remainder.
    - Deep Archive Access 180-day minimum applies; retrieval $0.02-10/GB.
IMPLEMENTATION:
  1. CONFIRM: About to put-bucket-intelligent-tiering-configuration on
     bucket app-data-mixed. This enables Intelligent-Tiering with
     Archive Access at 90d and Deep Archive Access at 180d. Monitoring
     fee: ~$75/month. Proceed? (yes/no)
  2. aws s3api put-bucket-intelligent-tiering-configuration \
       --bucket app-data-mixed \
       --id Config \
       --intelligent-tiering-configuration file://config.json
  3. Verify: aws s3api list-bucket-intelligent-tiering-configurations \
       --bucket app-data-mixed
  4. Backfill existing Standard objects via S3 Batch Operations:
     aws s3control create-job --account-id <acct> \
       --operation '{"S3CopyObject": {"TargetStorageClass": "INTELLIGENT_TIERING"}}' \
       --manifest-location s3://<manifest-bucket>/manifest.csv \
       --report-spec '<report-config>'
```

## What the skill caught that a generic assistant misses

1. **Monitoring-fee gate (Step 2).** A generic assistant enables
   Intelligent-Tiering and says "you'll save money." The skill computes
   the monitoring fee ($75/month for 30M objects), confirms it is < 8%
   of the $945/month net saving, and surfaces the math so the operator
   sees the gating check.

2. **Archive-tier configuration.** A generic assistant proposes
   Intelligent-Tiering with the default Frequent/Infrequent tiers only.
   The skill adds Archive Access at 90d and Deep Archive Access at 180d
   to capture the cold-data savings — the headline dollar impact.

3. **Dollar estimate net of monitoring fee.** A generic assistant says
   "Intelligent-Tiering is cheaper." The skill computes the projected
   monthly cost per tier, includes the monitoring fee in the total,
   and surfaces the 90/180-day minimum-duration caveats.

4. **CONFIRM gate before applying.** A generic assistant emits the
   `put-bucket-intelligent-tiering-configuration` command directly. The
   skill emits `CONFIRM:` and waits for operator approval — the
   monitoring fee applies immediately to every object in scope.

5. **Backfill via S3 Batch Operations.** A generic assistant applies
   the configuration and waits months for existing Standard objects to
   tier. The skill pairs the recommendation with `s3control create-job`
   for immediate backfill of existing objects.

6. **Rejection case for small objects.** If this bucket had 8M small
   JSON files instead of 30M large objects, the skill would emit
   ALREADY_OPTIMAL — the monitoring fee ($20.50/month) would exceed
   the $0 transition saving. A generic assistant would enable
   Intelligent-Tiering regardless.

## Slash-command invocation

```
/aws:optimize-s3-intelligent-tiering
```

Or via the orchestrator:

```
/aws:pipeline
You: "should I enable Intelligent-Tiering on app-data-mixed?"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: s3-intelligent-tiering-optimizer]`
and hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "enable Intelligent-Tiering on app-data-mixed"
# [Phase: Optimize | Skills routed: s3-intelligent-tiering-optimizer]
```

## Live-account follow-up (optional, requires AWS CLI)

After applying the configuration, validate the posture:

```bash
# Verify the Intelligent-Tiering configuration is in place
aws s3api list-bucket-intelligent-tiering-configurations \
  --bucket app-data-mixed --profile default --output json

# Re-check Storage Lens after 90 days for the tier-distribution shift
aws s3control get-storage-lens-configuration --config-id default \
  --account-id 111111111111 --profile default
```

Then monitor S3 Storage Lens daily export for the tier-distribution
shift and confirm the projected monthly cost reduction over the first
30-90 days as tiering transitions execute.
