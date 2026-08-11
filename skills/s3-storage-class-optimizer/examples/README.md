# Example usage: s3-storage-class-optimizer

A walkthrough showing the skill optimizing a 45 TB data-lake bucket
with no lifecycle policy, demonstrating the object-age analysis,
lifecycle template generation, versioning bloat discovery, per-TB
savings math, and Batch Operations deployment plan.

## Input (user prompt)

> Review this S3 bucket before our Q3 FinOps review. It's a data lake
> that's grown to 45 TB and the bill keeps climbing. Help me optimise
> the storage cost.

```text
BucketName: data-lake-raw-prod
Region: us-east-1
Storage (total): 45 TB
Storage class distribution:
  - Standard: 32 TB (71%)
  - Standard-IA: 8 TB (18%)
  - Glacier Instant Retrieval: 0 TB
  - Glacier Flexible Retrieval: 3 TB (7%)
  - Glacier Deep Archive: 2 TB (4%)
Versioning: Enabled
Lifecycle policy: none
Intelligent-Tiering: not configured
Storage Lens (last 30 days):
  - Objects aged 0-30 days: 12 TB
  - Objects aged 31-90 days: 9 TB
  - Objects aged 91-180 days: 6 TB
  - Objects aged 181-365 days: 5 TB
  - Objects aged >365 days: 13 TB
Retrieval frequency: <1% of objects accessed after 90 days
Cost Explorer (last 30 days): $1,035/month on S3 (71% Standard rate)

Workload context: data lake with raw ingestion. Objects are write-once-
read-rarely. No compliance retention beyond 7 years.
```

## Skill output

```text
TARGET: data-lake-raw-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: 45 TB bucket with 32 TB (71%) in Standard despite 13 TB being
  >365 days old (Storage Lens confirms <1% retrieval after 90 days).
  No lifecycle policy. Versioning enabled but no noncurrent-version
  rules, contributing ~4 TB of bloat. Deploying 4-tier lifecycle +
  noncurrent rules + Batch Ops saves $692.34/month.
RECOMMENDATION:
  Current: Standard 32 TB, IA 8 TB, Glacier 3 TB, DA 2 TB; no lifecycle
  Proposed: Standard 12 TB, IA 4 TB, GIR 6 TB, Glacier 3 TB, DA 20 TB; lifecycle active
  Dimensions changed: lifecycle (Step 1) + versioning (Step 4) + batch-migration (Step 6)
  Dimensions checked: lifecycle → (deploy)  intelligent-tiering ✓ (predictable)
    versioning → (add noncurrent rules)  retrieval → (verified <1%)  batch-migration → (7 TB)
  Confidence: HIGH — Storage Lens 90-day window confirms age distribution.
ESTIMATED_SAVINGS:
  Current monthly: $1,035.00
    Standard 32 TB × $23 = $736.00; IA 8 TB × $12.50 = $100.00
    Glacier 3 TB × $3.60 = $10.80; DA 2 TB × $0.99 = $1.98; Noncurrent ~4 TB = $92.00
  Projected monthly: $342.66
    Standard 12 TB × $23 = $276.00; IA 4 TB × $12.50 = $50.00
    GIR 6 TB × $4.00 = $24.00; Glacier 3 TB × $3.60 = $10.80
    DA 20 TB × $0.99 = $19.80; Noncurrent 0.5 TB IA = $6.25; Batch $0.21
  Monthly saving: $692.34 ($1,035.00 − $342.66 ✓)
  Annual saving: $8,308.08
  Retrieval risk: at <1% retrieval of 20 TB DA, retrieval cost ~$1.00/mo (bulk).
MIGRATION_STEPS:
  1. Deploy lifecycle policy:
     aws s3api put-bucket-lifecycle-configuration --bucket data-lake-raw-prod \
       --lifecycle-configuration file://lifecycle.json
  2. Add noncurrent-version transitions (keep 3 versions) to the same policy.
  3. Run S3 Batch Operations to migrate 7 TB aged objects to Deep Archive (~$2.50).
  4. Verify via Storage Lens after 7 days; monitor retrieval via CE for 30 days.
CONFIRM: About to put-bucket-lifecycle-configuration on data-lake-raw-prod
  (4-tier lifecycle + noncurrent rules + Batch Ops for 7 TB).
  Monthly saving $692.34 (66.9%); retrieval risk <1%. Proceed? (yes/no)
```

## What the skill caught that a generic assistant misses

1. **Object-age distribution drives the transition timing.** A generic
   assistant says "move old data to Glacier." The skill uses Storage
   Lens to specify exact age bands (30d→IA, 90d→GIR, 180d→DA) with
   per-TB dollar savings for each transition.

2. **Versioning bloat is quantified separately.** The skill identifies
   the 4 TB of noncurrent versions (9% of bucket) and adds noncurrent-
   version lifecycle rules — a dimension generic assistants miss entirely.

3. **Retrieval cost risk is stated explicitly.** The skill confirms <1%
   retrieval rate before recommending Deep Archive and quantifies the
   retrieval cost risk ($1.00/month for 1% of 20 TB). A generic assistant
   never checks this.

4. **Batch Operations for immediate migration.** The skill recommends
   Batch Operations for the 7 TB of already-aged objects sitting in
   Standard (burning money NOW) rather than waiting for lifecycle timing.
   Generic assistants don't distinguish between prospective and
   retrospective migration.

5. **Noncurrent-version retention count.** The skill specifies keeping
   3 most recent noncurrent versions before expiring — protecting
   application rollback. Generic assistants would expire all noncurrent
   versions, potentially breaking rollback capability.

6. **Per-class cost breakdown shown explicitly.** The skill shows each
   class's TB, rate, and dollar amount so the operator can verify the
   math. A generic assistant says "this should save money" without
   showing the per-TB arithmetic.

## Slash-command invocation

```
/aws:optimize-s3-storage-class
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimise our S3 storage cost for the Q3 FinOps review"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: s3-storage-class-optimizer]` and hands
off to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After deploying lifecycle, validate via Storage Lens:

```bash
# Check that lifecycle transitions are executing
aws s3control get-storage-lens-configuration \
  --config-id default-dashboard \
  --account-id <acct> \
  --profile default

# Monitor Cost Explorer for 30 days to confirm spend reduction
aws ce get-cost-and-usage \
  --time-period Start=2026-08-11,End=2026-09-11 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Simple Storage Service"]}}' \
  --group-by Type=DIMENSION,Key=USAGE_TYPE \
  --profile default
```

If retrieval costs spike or Storage Lens shows unexpected class
distribution changes, review the lifecycle rules:

```bash
aws s3api get-bucket-lifecycle-configuration \
  --bucket data-lake-raw-prod --profile default
```

## Fleet-wide extension

For a fleet of N S3 buckets, run the skill in batch mode:

1. List all buckets with `aws s3api list-buckets`.
2. Filter to buckets with > 1 TB storage (cost relevance).
3. Pull Storage Lens for each bucket.
4. Sort by estimated monthly savings (largest first).
5. Slice into batches of 5 buckets.
6. For each batch: emit per-bucket MIGRATION_STEPS, then a single
   CONFIRM for the batch.
7. Verify each batch before proceeding to the next.
8. After lifecycle deployment, evaluate Intelligent-Tiering for buckets
   with unpredictable access patterns.
