# Worked Examples — S3 Storage Class Optimizer

Full worked examples covering lifecycle deployment, Intelligent-Tiering
activation, versioning bloat, retrieval mismatch, already-optimal, and
end-to-end walkthrough. Loaded on demand — kept out of the main SKILL.md
body so the procedure stays scannable.

## Worked example — lifecycle deployment (no policy on aged data)

```text
TARGET: data-lake-raw-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: 45 TB bucket with no lifecycle policy. 32 TB in Standard despite
  13 TB being >365 days old with <1% retrieval (Storage Lens confirms).
  Deploying 4-tier lifecycle + noncurrent rules saves $692/month.
RECOMMENDATION:
  Current: Standard 32 TB, IA 8 TB, Glacier 3 TB, DA 2 TB; no lifecycle
  Proposed: Standard 12 TB, IA 4 TB, GIR 6 TB, Glacier 3 TB, DA 20 TB
  Dimensions changed: lifecycle (Step 1) + batch-migration (Step 6)
  Dimensions checked: lifecycle → (deploy)  intelligent-tiering ✓ (predictable)
    versioning ✓ (suspended)  retrieval → (verified <1%)  batch-migration → (7 TB)
  Confidence: HIGH — Storage Lens 90-day window confirms age distribution.
ESTIMATED_SAVINGS:
  Current monthly: $1,035.00
  Projected monthly: $342.66
  Monthly saving: $692.34 (66.9%)
  Annual saving: $8,308.08
MIGRATION_STEPS:
  1. Deploy lifecycle policy:
     aws s3api put-bucket-lifecycle-configuration \
       --bucket data-lake-raw-prod \
       --lifecycle-configuration file://lifecycle.json
  2. Run S3 Batch Operations to immediately migrate 7 TB aged objects
     to Deep Archive (~$2.50 one-time cost).
  3. Verify via Storage Lens after 7 days.
CONFIRM: About to put-bucket-lifecycle-configuration on data-lake-raw-prod.
  Monthly saving $692.34 (66.9%). Proceed? (yes/no)
```

## Worked example — Intelligent-Tiering activation (unpredictable access)

```text
TARGET: shared-documents-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: 20 TB bucket all in Standard with unpredictable access patterns.
  9 TB is >90 days old with sporadic reads. Lifecycle can't encode the
  pattern. Intelligent-Tiering auto-moves to Archive Access at 90d.
RECOMMENDATION:
  Current: Standard 20 TB; no Intelligent-Tiering, no lifecycle
  Proposed: Intelligent-Tiering enabled on all prefixes
  Dimensions changed: intelligent-tiering (Step 2)
  Dimensions checked: lifecycle ✓ (unpredictable, IT preferred)
    intelligent-tiering → (enable)  versioning ✓ (suspended)
    retrieval ✓ (IT handles per-object)  batch-migration ✓ (not needed)
  Confidence: HIGH — 20 TB >> 1 TB break-even for IT monitoring fee.
ESTIMATED_SAVINGS:
  Current monthly: $460.00 (20 TB × $23)
  Projected monthly: $287.50
    Frequent Access (active, ~8 TB): 8 × $23 = $184
    Infrequent Access (~4 TB): 4 × $12.50 = $50
    Archive Access (~5 TB): 5 × $1.25 = $6.25
    Deep Archive Access (~3 TB): 3 × $0.30 = $0.90
    Monitoring fee: 20 TB × $2.50 = $50
    (minus small objects <128KB that stay in Frequent: ~3.65 adjustment)
  Monthly saving: $172.50 (37.5%)
  Annual saving: $2,070.00
MIGRATION_STEPS:
  1. Enable Intelligent-Tiering on all objects:
     aws s3api put-bucket-intelligent-tiering-configuration \
       --bucket shared-documents-prod --id ConfigID \
       --intelligent-tiering-configuration '{"Status":"Enabled","Tierings":[{"Days":90,"AccessTier":"ARCHIVE_ACCESS"},{"Days":180,"AccessTier":"DEEP_ARCHIVE_ACCESS"}]}'
  2. Copy existing objects into Intelligent-Tiering class (Batch Operations).
  3. Monitor Storage Lens after 30 days for tier movement.
CONFIRM: About to enable Intelligent-Tiering on shared-documents-prod.
  Monthly saving $172.50 (37.5%). Proceed? (yes/no)
```

## Worked example — versioning bloat reclamation

```text
TARGET: app-documents-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: 50 TB versioned bucket with 12 TB (24%) noncurrent versions and
  no noncurrent-version lifecycle rules. Growing 8% per month. Adding
  noncurrent rules (keep 3 versions, expire at 365d) reclaims ~8 TB.
RECOMMENDATION:
  Current: 50 TB total (38 current + 12 noncurrent), no noncurrent rules
  Proposed: Keep 3 noncurrent versions per object; transition to IA at
    30d, Deep Archive at 180d, expire at 365d. Also abort incomplete
    multipart uploads (2 TB).
  Dimensions changed: versioning (Step 4)
  Dimensions checked: lifecycle → (deploy noncurrent)  intelligent-tiering ✓
    versioning → (add noncurrent rules)  retrieval ✓  batch-migration ✓
  Confidence: HIGH — Storage Lens confirms noncurrent growing 8%/month.
ESTIMATED_SAVINGS:
  Current monthly: $1,150.00 (50 TB × $23)
  Projected monthly: $897.00
    Current: 38 TB × $23 = $874
    Noncurrent (3 versions, ~4 TB in IA): 4 TB × $12.50 = $50
    Multipart cleanup: -2 TB = -$46
    Net: $874 + $50 - $46 + adjustment = $897.00
  Monthly saving: $253.00 (22%)
  Annual saving: $3,036.00
MIGRATION_STEPS:
  1. Add noncurrent-version lifecycle rules:
     aws s3api put-bucket-lifecycle-configuration \
       --bucket app-documents-prod \
       --lifecycle-configuration file://noncurrent-lifecycle.json
  2. Add incomplete multipart abort rule (AbortIncompleteMultipartUpload: 7 days).
  3. Optionally schedule Batch Operations to remove stale delete markers.
  4. Verify noncurrent storage decreasing via Storage Lens after 14 days.
CONFIRM: About to put-bucket-lifecycle-configuration on app-documents-prod
  (noncurrent rules + multipart abort). Monthly saving $253.00 (22%).
  Proceed? (yes/no)
```

## Worked example — already optimal

```text
TARGET: analytics-managed-prod
VERDICT: ALREADY_OPTIMAL
REASON: 10 TB bucket with lifecycle deployed 6 months ago, Intelligent-
  Tiering on unpredictable-access prefix, Storage Lens confirms correct
  tier distribution, <1% retrieval of archived objects. No dimension has
  positive savings.
RECOMMENDATION:
  Current: Standard 3 TB, IA 2 TB, GIR 2 TB, DA 3 TB; lifecycle active; IT on mixed prefix
  Dimensions checked: lifecycle ✓ (deployed)  intelligent-tiering ✓ (active)
    versioning ✓ (suspended)  retrieval ✓ (<1%)  batch-migration ✓ (not needed)
  Confidence: HIGH — Storage Lens confirms transitions executing correctly.
ESTIMATED_SAVINGS:
  Monthly: $0.00
  Annual: $0.00
MIGRATION_STEPS:
  - None required. Re-evaluate quarterly or if access pattern changes.
```

## Worked example — NEED_MORE_INFO (no Storage Lens)

```text
TARGET: legacy-archive-bucket
VERDICT: NEED_MORE_INFO
REASON: Storage Lens data is absent and Cost Explorer window is only 7
  days. Cannot determine object-age distribution or current storage-class
  breakdown. Cannot make a lifecycle recommendation without age data.
RECOMMENDATION:
  Current: unknown — pending Storage Lens data
  Proposed: pending data
  Confidence: LOW — no metrics to evaluate.
ESTIMATED_SAVINGS:
  Monthly: $0 (cannot quantify without baseline)
MIGRATION_STEPS:
  1. Enable S3 Storage Lens (free tier):
     aws s3control put-storage-lens-configuration ...
  2. Wait 30 days for representative object-age data.
  3. Re-evaluate with Storage Lens + CE data.
  Do NOT deploy lifecycle without age distribution data.
```

## End-to-end optimisation walkthrough (45 TB data lake)

**Function profile:**
- Bucket: `data-lake-raw-prod`
- Region: us-east-1
- Storage: 45 TB
- Versioning: Enabled (but no noncurrent rules)
- Lifecycle: none
- IT: not configured

**Step 1 — Analyse Storage Lens:**
```
Age distribution:
  0-30d: 12 TB    → keep in Standard
  31-90d: 9 TB   → transition to Standard-IA
  91-180d: 6 TB  → transition to Glacier IR
  181-365d: 5 TB → transition to Glacier Flexible or Deep Archive
  >365d: 13 TB   → transition to Deep Archive immediately
```

**Step 2 — Check retrieval pattern:** <1% retrieval after 90 days.
Deep Archive at 180d is safe.

**Step 3 — Check versioning:** 4 TB noncurrent, no rules → add noncurrent.

**Step 4 — Calculate savings:**
```
Current: 45 TB × blended rate ≈ $1,035/month
Projected: $342.66/month
Saving: $692.34/month (66.9%), $8,308.08/year
```

**Step 5 — Emit the output block** (see lifecycle deployment worked example above).
