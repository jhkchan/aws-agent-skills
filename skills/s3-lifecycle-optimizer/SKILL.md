---
name: s3-lifecycle-optimizer
description: >-
  Optimises S3 storage cost through lifecycle-policy design, storage-class
  selection, and access-pattern analysis. Invents the right transition and
  expiration rules per workload archetype (logs, compliance archive,
  application data, versioned buckets, multipart-upload leaks), projects
  monthly savings net of minimum-duration and retrieval charges, and emits
  a deterministic verdict (OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL)
  per bucket with the exact put-bucket-lifecycle-configuration payload and
  estimated dollar impact. Use when reviewing S3 spend, designing lifecycle
  policies, choosing between Standard-IA / One-Zone-IA / Intelligent-Tiering
  / Glacier tiers, pruning noncurrent versions, aborting stale multipart
  uploads, or projecting savings from a storage-class migration.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline configuration classification.
  Live-account audits use aws s3api list-buckets, aws s3api
  get-bucket-lifecycle-configuration, aws s3api list-objects-v2 (with
  --page-size for inventory), aws s3api list-multipart-uploads, aws s3api
  get-bucket-versioning, and aws s3control get-storage-lens-configuration
  (AWS CLI v2, SSO or key-based credentials). Pricing is us-east-1 published
  rates as of 2026; re-state the regional rates from the reference matrix
  before producing dollar estimates for other regions.
keywords:
  - S3
  - lifecycle policy
  - storage class
  - Standard-IA
  - One-Zone-IA
  - Intelligent-Tiering
  - Glacier Instant Retrieval
  - Glacier Flexible Retrieval
  - Glacier Deep Archive
  - S3 Express One Zone
  - directory bucket
  - noncurrent version
  - multipart upload
  - S3 Storage Lens
  - S3 Object Lock
  - S3 Batch Operations
  - S3 Tables
  - put-bucket-lifecycle-configuration
  - storage cost optimization
tags: [s3, storage, cost-optimization, lifecycle, storage-class, glacier, intelligent-tiering, object-lock, finops]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: Storage
  task_type: optimize
  skill_class: capability
  verdict_shape: "OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL"
  when_to_use: >-
    Reviewing S3 spend, designing or auditing lifecycle policies, selecting
    storage classes for infrequently accessed data, projecting savings from
    Standard -> Standard-IA / Intelligent-Tiering / Glacier transitions,
    pruning noncurrent versions on versioned buckets, aborting stale
    multipart uploads, or hardening compliance archives with Object Lock.
  activation_triggers:
    - "optimise S3 storage cost"
    - "design S3 lifecycle policy"
    - "S3 storage class analysis"
    - "move S3 data to Glacier"
    - "S3 Intelligent-Tiering vs Standard-IA"
    - "prune noncurrent S3 versions"
    - "abort stale S3 multipart uploads"
    - "S3 Object Lock retention"
    - "S3 lifecycle transition rules"
    - "S3 cost optimization review"
    - "Glacier Deep Archive lifecycle"
    - "S3 Batch Operations storage class"
  invocation_schema: >-
    Input: either (a) a bucket configuration (lifecycle configuration JSON,
    versioning status, Storage Lens metrics summary, optional object-age
    histogram), OR (b) a bucket name for live-account optimisation. Output:
    deterministic BUCKET/VERDICT/REASON/RECOMMENDATION/SAVINGS/IMPLEMENTATION
    block per bucket, where VERDICT is one of OPTIMIZED, OPPORTUNITY_FOUND,
    ALREADY_OPTIMAL.
---

# S3 Lifecycle Optimizer

## What this skill does

Translates S3 storage posture into a concrete lifecycle policy and a
dollar-denominated savings estimate. The verdict is the **highest-leverage
action** across four dimensions — storage-class mix, lifecycle transitions,
noncurrent-version cleanup, and multipart-upload hygiene — applied in priority
order. Always pairs the recommendation with the exact
`put-bucket-lifecycle-configuration` payload so the operator can paste, review,
and apply.

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `OPPORTUNITY_FOUND` | One or more dimensions has a cost-saving or risk-reducing lifecycle change available | Emit recommended policy + savings estimate |
| `OPTIMIZED` | A lifecycle change was applied this session and verified | Emit post-state verification and recompute savings |
| `ALREADY_OPTIMAL` | Lifecycle policy covers all applicable dimensions; no savings available | No action — confirm posture |

**Priority order for opportunity dimensions (apply in this sequence, aggregate
all that apply into a single recommendation):**

1. **Noncurrent version cleanup** (versioned buckets) — typically the largest
   hidden line on long-lived buckets.
2. **Multipart upload cleanup** — silent cost leak, free to fix.
3. **Storage-class transitions** for current objects — the headline saving.
4. **Expiration** for compliance or log workloads — stops the bleed at source.
5. **Object Lock / retention posture** — compliance-only, not a saving lever
   but surfaces alongside lifecycle for archive workflows.

**Cost baseline (us-east-1, 2026, USD per GB-month):**

| Storage class | $/GB-mo | Min size | Min duration | Retrieval cost | Best for |
|---|---|---|---|---|---|
| Standard | 0.023 | — | — | free | Daily/weekly access |
| Standard-IA | 0.0125 | 128 KB | 30 days | $0.01/GB | Monthly access, rapid retrieve |
| One-Zone-IA | 0.01 | 128 KB | 30 days | $0.01/GB + AZ-loss risk | Re-creatable infrequent data |
| Intelligent-Tiering | 0.023 (then auto-tiers) | — | 30/90/180 per tier | free (monitor) | Unknown / mixed patterns |
| Glacier Instant Retrieval | 0.004 | 128 KB | 90 days | $0.03/GB + $0.0005/req | Quarterly access, ms retrieve |
| Glacier Flexible Retrieval | 0.0036 | — | 90 days | $0.0025-10/GB (tiered) | Archive, hours retrieve |
| Glacier Deep Archive | 0.00099 | — | 180 days | $0.02-10/GB (tiered) | Long-term archive, 12h retrieve |
| S3 Express One Zone (directory bucket) | 0.16 | — | — | free | ML/AI latency-critical |
| Reduced Redundancy (RRS) | 0.024 | — | — | free | Legacy — do not use |

Full pricing matrix including request and monitoring fees lives in
`references/storage-class-pricing-matrix.md` — load it before producing
dollar estimates for non-us-east-1 regions.

## Mindset

**One-line takeaway:** the verdict is the **largest net-positive saving** after
accounting for minimum-duration charges and retrieval fees — driven by four
S3 realities:

- **Lifecycle transitions are free to set but cost-prohibitive to undo.** A
  premature Glacier transition on objects that turn out to be accessed weekly
  incurs retrieval fees that wipe out months of savings. Always ground the
  recommendation in observed access patterns (Storage Lens, CloudTrail
  `GetObject`, or tags) before tiering.
- **Minimum-duration charges dominate for short-lived objects.** Moving a
  5-day-old object to Standard-IA bills the full 30-day IA charge even if it
  is deleted on day 6. For logs that roll over weekly, IA is the wrong tier.
- **Noncurrent versions are the silent S3 bill.** A versioned bucket with no
  `NoncurrentVersionExpiration` rule accumulates every prior version of every
  object indefinitely — 100 TB of "current" data routinely hides 400 TB of
  noncurrent bytes that nobody looks at.
- **Multipart uploads that never complete bill forever.** `AbortMultipartUpload`
  is a one-line lifecycle rule that stops indefinite accumulation of orphaned
  parts; almost every bucket operated >1 year has leaked parts.

## Pre-flight: bucket metadata gate

Run before classification. Misclassifying these produces false positives.

**Pagination:** `list-objects-v2` paginates at 1,000 keys/page. For a full
inventory use S3 Inventory (daily export) or `list-objects-v2 --page-size 1000
--starting-token` drained to completion. For large buckets, **do not** iterate
all keys live — pull Storage Lens metrics instead (`get-storage-lens-configuration`
plus the daily CSV/Parquet export).

**Live-account pre-flight (skip if offline audit):**
1. `aws s3api get-bucket-versioning` — if `Status != Enabled`, noncurrent-version
   rules are no-ops; skip that dimension.
2. `aws s3api get-bucket-lifecycle-configuration` — capture current rules to
   compare against the recommendation.
3. `aws s3api list-multipart-uploads --bucket <name>` — pending uploads older
   than 7 days are a leak.
4. `aws s3control get-storage-lens-configuration --config-id default` —
   noncurrent-byte %, storage-class distribution, object-age histogram.
5. `aws s3api get-object-lock-configuration` — if Object Lock is enabled, any
   lifecycle rule MUST respect the retention period; violating it is a no-op.
6. `aws s3api list-buckets --query "Buckets[*].Name"` — sweep every bucket in
   every region; cross-region cost variance is material.

**Malformed input:** if the input JSON is invalid or missing required fields,
emit `VERDICT: ERROR` with `REASON: Bucket configuration is not valid JSON or
is missing required fields — cannot classify.` and `REMEDIATION: Re-fetch with
aws s3api get-bucket-lifecycle-configuration --bucket <name> --output json and
re-audit.`

| Bucket attribute | Effect on audit |
|---|---|
| Versioning `Enabled` | Run noncurrent-version dimension. |
| Versioning `Suspended` | New versions still created with null version-id; existing noncurrent versions still bill. Run dimension. |
| Versioning never enabled | Skip noncurrent dimension. |
| Object Lock `Enabled` | Lifecycle MUST NOT expire objects before retention expiry. Validate per-rule. |
| Object Lock `Governance` mode | Retention can be bypassed with `s3:BypassGovernanceRetention`. Note alongside lifecycle. |
| Bucket has `Intelligent-Tiering` S3 Lifecycle rule already | Compare actual tier distribution from Storage Lens before re-recommending. |
| Bucket is a **directory bucket** (S3 Express One Zone, name suffix `--x-s3`) | Lifecycle and Object Lock are NOT supported on directory buckets. Skip the policy dimensions; verdict is ALREADY_OPTIMAL for latency-critical ML/AI workloads. |
| Bucket is a **general-access bucket with S3 Tables** (Apache Iceberg) | Tables have their own lifecycle; do not propose `Expiration` on table data — surface as a finding only. |
| Requester-pays bucket | Transitions still bill the bucket owner; retrieval bills the requester. Note in savings estimate. |

## Process — optimisation logic (apply in order, aggregate all applicable)

### Step 0: Expert knowledge — non-obvious S3 lifecycle behaviors

These behaviors are easy to misjudge without operational S3 experience.
Each changes a recommendation if ignored:

- **Transition `Days` counts from object creation, not from policy creation.**
  A rule that says "transition to Standard-IA after 30 days" applies to objects
  that are already 60 days old the moment the rule is added — they transition
  immediately. This is usually what you want, but surprises operators.

- **Minimum-duration charges bill regardless of when the object is deleted.**
  Standard-IA bills 30 days minimum, Glacier tiers bill 90/180 days minimum.
  If the workload deletes objects sooner, the storage class is more expensive
  than Standard. Always model minimum-duration cost vs Standard before
  recommending a transition.

- **Small-object surcharge on IA tiers.** Standard-IA and One-Zone-IA have a
  minimum billable size of 128 KB. Objects smaller than 128 KB are billed as
  if they were 128 KB — for buckets of small JSON/config files, IA is often
  MORE expensive than Standard.

- **Intelligent-Tiering has a monitoring fee of $0.0025 per 1,000 objects.**
  For buckets of millions of small objects, the monitoring fee can exceed the
  transition savings. Threshold: Intelligent-Tiering wins when average object
  size > 128 KB and access pattern is genuinely mixed.

- **Glacier retrieval is not free.** Standard retrieval from Glacier Flexible
  is $2.50-10 per TB (5-12 hours), Expedited is $10-30 per TB (1-5 min). Glacier
  Deep Archive Standard is $2-10 per TB (12 hours), Bulk is $2.50/TB (48h).
  Always warn that the saving is a storage saving; retrieval is à la carte.

- **Lifecycle rules are eventually applied.** S3 processes lifecycle transitions
  asynchronously, typically once per day. A rule added at 09:00 may not execute
  until the next lifecycle run. Do not alarm on a 24-hour lag.

- **A lifecycle rule with a filter that matches no objects is silently a no-op.**
  `Filter: { Prefix: "logs/2024/" }` on a bucket where logs are under
  `2025/logs/` matches nothing. Always cross-check the prefix against the actual
  key layout before declaring ALREADY_OPTIMAL.

- **`ExpirationInDays` deletes the current version. `NoncurrentVersionExpiration`
  deletes prior versions.** Conflating them produces data loss: setting
  `ExpirationInDays: 30` on a versioned bucket with no noncurrent rule deletes
  the current version (creating a new noncurrent version) but leaves all prior
  noncurrent versions intact — increasing storage instead of reducing it.

- **S3 Batch Operations complements lifecycle for one-time migrations.**
  Lifecycle applies to future objects going forward, but existing objects only
  transition when their `Days` threshold is reached. To immediately move
  existing Standard objects to Glacier, use `create-job` with
  `S3CopyObject` and the target storage class — lifecycle handles the
  forward path, Batch handles the backfill.

- **Intelligent-Tiering Archive configurations are tunable.** The default
  Archive tier moves objects after 90 consecutive days of no access; Deep
  Archive moves after 180. Both are configurable via
  `Tierings[{AccessTier: ARCHIVE_ACCESS, Days: N}]` — for known-cold data,
  shorter windows capture savings faster.

- **S3 Object Lock retention is enforced before lifecycle expiration.** If
  an object has a `COMPLIANCE` mode retention period ending in 2030, a
  lifecycle rule with `ExpirationInDays: 365` will NOT delete it until 2030.
  The rule is a no-op for the locked object; surface this so the operator
  understands the lifecycle does not bypass compliance.

- **Cross-Region Replication (CRR) preserves storage class by default.**
  Replicating a Standard object to a destination bucket copies it as Standard
  unless the replication rule specifies a different storage class. Destination
  lifecycle rules apply independently — design them in tandem.

- **S3 Tables (managed Apache Iceberg) have their own lifecycle.** Do not
  propose `Expiration` rules on table data prefixes; Iceberg compaction and
  snapshot expiration are managed via table APIs. Surface as a finding only.

- **Directory buckets (S3 Express One Zone) do not support lifecycle, Object
  Lock, or Glacier tiers.** They are designed for single-AZ, ms-latency ML/AI
  workloads at $0.16/GB. Verdict for a directory bucket is ALREADY_OPTIMAL
  for its intended use case; surface the cost-per-GB as a finding.

### Step 1: Noncurrent version cleanup (versioned buckets)

If the bucket has versioning `Enabled` or `Suspended`:

- **Pull noncurrent byte % from Storage Lens.** A bucket with >20% noncurrent
  bytes is a high-confidence opportunity. >50% is severe.
- **Recommended default rule:**
  - Transition noncurrent versions to Standard-IA after 30 days.
  - Transition to Glacier Instant Retrieval after 90 days.
  - Expire noncurrent versions after 90-180 days (tune by workload).
- **Pattern — versioning cleanup:**
  ```json
  {
    "ID": "noncurrent-version-cleanup",
    "Status": "Enabled",
    "Filter": {},
    "NoncurrentVersionTransitions": [
      { "NoncurrentDays": 30, "NewNoncurrentStorageClass": "STANDARD_IA" },
      { "NoncurrentDays": 90, "NewNoncurrentStorageClass": "GLACIER_IR" }
    ],
    "NoncurrentVersionExpiration": { "NoncurrentDays": 180 }
  }
  ```
- **Savings estimate:** `noncurrent_bytes_GB × (Standard_rate - IA_rate)` for
  the first 30 days, then taper. Most versioned buckets save 40-70% on the
  noncurrent dimension alone.

If versioning is `Enabled` and no `NoncurrentVersionExpiration` rule exists:
**OPPORTUNITY_FOUND** on this dimension.

### Step 2: Multipart upload cleanup

- **Pull pending multipart uploads:** `aws s3api list-multipart-uploads --bucket <name>`.
  Any upload with `Initiated` > 7 days ago is a leak.
- **Recommended rule (always include, even on buckets without known leaks):**
  ```json
  {
    "ID": "abort-incomplete-multipart-uploads",
    "Status": "Enabled",
    "Filter": {},
    "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
  }
  ```
- **Savings estimate:** pending parts bill at Standard rate. A 100 GB
  half-uploaded file costs $2.30/month indefinitely. The rule pays for itself
  in zero cost.

If any multipart upload is >7 days old OR no abort rule exists:
**OPPORTUNITY_FOUND** on this dimension.

### Step 3: Storage-class transition design (current objects)

Apply per workload archetype. Pick the pattern by access pattern, not by
data type.

**Archetype A — Logs and temporary data (high write, low read after 30 days):**
```json
{
  "ID": "logs-lifecycle",
  "Status": "Enabled",
  "Filter": { "Prefix": "logs/" },
  "Transitions": [
    { "Days": 30, "StorageClass": "STANDARD_IA" },
    { "Days": 90, "StorageClass": "GLACIER_IR" },
    { "Days": 180, "StorageClass": "GLACIER" }
  ],
  "Expiration": { "Days": 365 }
}
```
Pattern: Standard -> 30d IA -> 90d Glacier IR -> 180d Glacier -> 365d Expire.

**Archetype B — Compliance archives (write-once, read-rarely, 7-year retention):**
```json
{
  "ID": "compliance-archive",
  "Status": "Enabled",
  "Filter": { "Prefix": "archive/" },
  "Transitions": [
    { "Days": 90, "StorageClass": "GLACIER_DEEP_ARCHIVE" }
  ]
}
```
Pattern: Standard -> 90d Deep Archive -> Expire at retention horizon (e.g., 2555 days for 7 years).

**Archetype C — Application data with unknown / mixed access patterns:**
```json
{
  "ID": "app-data-intelligent-tiering",
  "Status": "Enabled",
  "Filter": { "Prefix": "app/" },
  "Transitions": [
    { "Days": 0, "StorageClass": "INTELLIGENT_TIERING" }
  ]
}
```
Pattern: Standard -> Intelligent-Tiering (let AWS manage transitions).
**Threshold check:** only recommend Intelligent-Tiering when average object
size > 128 KB AND access pattern is genuinely mixed. For small objects, the
$0.0025/1,000 monitoring fee exceeds the saving.

**Archetype D — Backup / DR target (write-nightly, read-never unless disaster):**
```json
{
  "ID": "backup-tier",
  "Status": "Enabled",
  "Filter": { "Prefix": "backup/" },
  "Transitions": [
    { "Days": 30, "StorageClass": "GLACIER_IR" },
    { "Days": 90, "StorageClass": "GLACIER" }
  ]
}
```
Pattern: Standard -> 30d Glacier IR (quarterly DR test) -> 90d Glacier.

**Archetype E — ML/AI training corpus (frequent random access during training,
then cold):**
- Use **S3 Express One Zone directory bucket** ($0.16/GB) for the active
  training set — ms-latency matters more than $/GB.
- After training, copy the corpus to a general-access bucket and apply Archetype A
  or B. Directory buckets do not support lifecycle transitions out.

**Net saving calculation per archetype:**
- `current_monthly = current_GB × current_storage_class_rate`
- `projected_monthly = sum(tier_GB × tier_rate) + min_duration_charge`
- `monthly_saving = current_monthly - projected_monthly`
- Surface `monthly_saving` AND `annual_saving` in the output.

If no transition rule exists AND current objects are >30 days old on average:
**OPPORTUNITY_FOUND** on this dimension.

### Step 4: Expiration for compliance or log workloads

- **Logs:** expire after the operational lookup window (typically 90-365 days).
- **Compliance:** expire at the regulatory minimum (e.g., 2555 days for 7-year
  retention). Never expire before the regulatory minimum — that creates a
  compliance violation.
- **Temp / scratch:** expire aggressively (1-7 days).

If the bucket has no `Expiration` rule and the workload archetype calls for one:
**OPPORTUNITY_FOUND** on this dimension.

### Step 5: Object Lock / retention posture

- **If Object Lock is not enabled and the workload is compliance-archive:**
  recommend enabling with `COMPLIANCE` mode and the regulatory retention period.
- **If Object Lock is in `GOVERNANCE` mode for compliance data:** surface that
  governance mode can be bypassed by any principal with
  `s3:BypassGovernanceRetention` — recommend `COMPLIANCE` mode.
- **If Object Lock is enabled and lifecycle expiration is shorter than the
  retention period:** surface as a CONFIG finding — the rule is silently a no-op
  on locked objects.

This dimension surfaces findings but does not change the verdict unless the
lifecycle rule itself is misconfigured against the retention period.

### Step 6: Aggregation — emit the highest-leverage recommendation

Aggregate ALL applicable dimensions into a single recommended lifecycle
configuration. The verdict is `OPPORTUNITY_FOUND` if any dimension has a saving
or risk-reducing change. The recommendation includes the full
`put-bucket-lifecycle-configuration` payload combining all rules.

If no dimension has an opportunity (lifecycle covers all applicable rules
correctly, no leaks, no misconfigurations): **ALREADY_OPTIMAL**.

If the recommendation was applied this session and verified:
**OPTIMIZED**.

## Output format (per bucket)

```text
BUCKET: <bucket-name>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences citing the highest-leverage dimension and step number>
RECOMMENDATION:
  <lifecycle configuration JSON or "No changes required">
SAVINGS:
  CURRENT_MONTHLY: $<X.XX>
  PROJECTED_MONTHLY: $<Y.YY>
  MONTHLY_SAVING: $<X.XX - Y.YY>
  ANNUAL_SAVING: $<12 × monthly>
  CAVEATS: <minimum-duration charges, retrieval fee warnings, monitoring fees>
IMPLEMENTATION:
  1. aws s3api put-bucket-lifecycle-configuration --bucket <name> --lifecycle-configuration file://lifecycle.json
  2. <verification command>
  3. <backfill via S3 Batch Operations if existing objects need immediate transition>
```

### Worked example — logs bucket with no lifecycle

```text
BUCKET: app-logs-prod
VERDICT: OPPORTUNITY_FOUND
REASON: Bucket is versioned with 12 TB of noncurrent bytes (62% of total) and
no lifecycle policy (Step 1, Step 3, Step 4). All 19.4 TB sit in Standard at
$0.023/GB-mo. Recommended pattern: logs-lifecycle (Archetype A) +
noncurrent cleanup + multipart abort.
RECOMMENDATION:
  {
    "Rules": [
      {
        "ID": "logs-lifecycle",
        "Status": "Enabled",
        "Filter": { "Prefix": "logs/" },
        "Transitions": [
          { "Days": 30, "StorageClass": "STANDARD_IA" },
          { "Days": 90, "StorageClass": "GLACIER_IR" },
          { "Days": 180, "StorageClass": "GLACIER" }
        ],
        "Expiration": { "Days": 365 }
      },
      {
        "ID": "noncurrent-version-cleanup",
        "Status": "Enabled",
        "Filter": {},
        "NoncurrentVersionTransitions": [
          { "NoncurrentDays": 30, "NewNoncurrentStorageClass": "STANDARD_IA" },
          { "NoncurrentDays": 90, "NewNoncurrentStorageClass": "GLACIER_IR" }
        ],
        "NoncurrentVersionExpiration": { "NoncurrentDays": 180 }
      },
      {
        "ID": "abort-incomplete-multipart-uploads",
        "Status": "Enabled",
        "Filter": {},
        "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
      }
    ]
  }
SAVINGS:
  CURRENT_MONTHLY: $446.20  (19,400 GB × $0.023)
  PROJECTED_MONTHLY: $139.96
    - 2,400 GB current at Standard (< 30d) × $0.023 = $55.20
    - 1,400 GB current at Standard-IA (30-90d) × $0.0125 = $17.50
    - 2,000 GB current at Glacier IR (90-180d) × $0.004 = $8.00
    - 1,600 GB current at Glacier (180-365d) × $0.0036 = $5.76
    - 3,000 GB noncurrent at Standard-IA (30-90d) × $0.0125 = $37.50
    - 4,000 GB noncurrent at Glacier IR (90-180d) × $0.004 = $16.00
    - 5,000 GB noncurrent expired (> 180d) = $0.00
    - Arithmetic check: 55.20 + 17.50 + 8.00 + 5.76 + 37.50 + 16.00 = $139.96
  MONTHLY_SAVING: $306.24  ($446.20 − $139.96)
  ANNUAL_SAVING: $3,674.88
  CAVEATS:
    - Standard-IA 30-day minimum: objects deleted before day 30 still bill.
    - Glacier IR 90-day minimum applies.
    - Glacier IR retrieval is $0.03/GB if logs are queried — budget separately.
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
       --manifest-location <manifest-bucket> \
       --report-spec '<report-config>'
```

### Worked example — already optimal compliance bucket

```text
BUCKET: compliance-archive-7yr
VERDICT: ALREADY_OPTIMAL
REASON: Bucket already transitions objects to Glacier Deep Archive at 90 days,
has Object Lock in COMPLIANCE mode with 2555-day retention, and no incomplete
multipart uploads.
RECOMMENDATION: No changes required.
SAVINGS:
  CURRENT_MONTHLY: $19.80  (20,000 GB × $0.00099 Deep Archive)
  PROJECTED_MONTHLY: $19.80
  MONTHLY_SAVING: $0.00
  ANNUAL_SAVING: $0.00
  CAVEATS: Glacier Deep Archive retrieval is $2-10/TB Standard, 12h latency.
IMPLEMENTATION: None required. Posture is correct for the workload archetype.
```

### Worked example — Intelligent-Tiering trap (small objects, proposed plan rejected)

This example demonstrates the **zero-savings rule**: when the proposed
transition would cost MORE than the current tier, the verdict is
`ALREADY_OPTIMAL` for the transition dimension — never
`OPPORTUNITY_FOUND` with $0 or negative savings.

```text
BUCKET: app-config-state
VERDICT: ALREADY_OPTIMAL
REASON: Proposed Intelligent-Tiering transition on 8.2M objects averaging
  4.2 KB each is MORE expensive than Standard. The monitoring fee alone
  ($20.50/month) exceeds total current cost. The 128 KB minimum billable
  size on the Infrequent tier makes tiering even more costly if objects
  drop. The proposed plan is rejected (Step 3 Archetype C threshold check
  fails: average object size < 128 KB).
RECOMMENDATION: No storage-class transition. Standard is already the cheapest
  tier for this object-size profile. Optionally add AbortIncompleteMultipartUpload
  hygiene rule (zero-cost, preventive).
SAVINGS:
  CURRENT_MONTHLY: $10.09
    - Storage: 32.0 GiB × $0.023 = $0.74
    - GETs: 8.2M × 3/month × $0.00038/1K = $9.35
    - PUTs: negligible (write-once workload)
  PROJECTED_MONTHLY (Intelligent-Tiering, best case — all in Frequent tier):
    - Monitoring fee: 8,200,000 / 1,000 × $0.0025 = $20.50
    - Storage: 32.0 GiB × $0.023 = $0.74
    - GETs: 8.2M × 3/month × $0.00038/1K = $9.35 (unchanged)
    - Total projected: $30.59
  MONTHLY_SAVING: -$20.50  (NEGATIVE — monitoring fee alone exceeds saving)
  ANNUAL_SAVING: -$246.00
  CAVEATS: The proposed plan INCREASES cost by $20.50/month (the monitoring
    fee). If objects auto-tier to Infrequent Access, cost rises further
    due to the 128 KB minimum billable size (8.2M × 128 KB = 1,025 GiB
    billable vs 32 GiB actual — a 32x storage inflation). The verdict is
    ALREADY_OPTIMAL because Standard is already the cheapest applicable
    tier. The operator should NOT proceed with Intelligent-Tiering.
IMPLEMENTATION:
  1. Do NOT apply the proposed Intelligent-Tiering transition.
  2. Optional hygiene rule (zero-cost):
     {
       "Rules": [{
         "ID": "abort-incomplete-multipart-uploads",
         "Status": "Enabled",
         "Filter": {},
         "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
       }]
     }
  3. Re-evaluate if average object size grows > 128 KB in the future.
```

**Why this verdict is ALREADY_OPTIMAL, not OPPORTUNITY_FOUND:** the
proposed plan was a transition to Intelligent-Tiering, but the math
shows it costs MORE than Standard for this object profile. There is
no saving to capture — the cheapest applicable tier is already in
place. Emitting `OPPORTUNITY_FOUND` with `$0.00` or negative savings
is a hard error per the Verdict consistency rules above.

### Worked example — compliance archive with no lifecycle (OPPORTUNITY_FOUND with correct math)

This example demonstrates the **positive-savings rule**: when a
compliance archive has no lifecycle and objects sit in Standard at
120+ days old, transitioning to Deep Archive captures real savings.
The verdict is `OPPORTUNITY_FOUND` because the math shows positive
monthly savings.

```text
BUCKET: compliance-archive-7yr
VERDICT: OPPORTUNITY_FOUND
REASON: Compliance archive with 5,000 GiB in Standard at 120 days average
  age, no lifecycle, accessed < 1x/year. Transitioning to Glacier Deep
  Archive at 90 days captures 95.7% storage saving. Versioning is Enabled
  with 0 noncurrent bytes (write-once workload). Object Lock not configured
  — surface as a parallel compliance finding (Step 5).
RECOMMENDATION:
  {
    "Rules": [
      {
        "ID": "compliance-archive-deep-archive",
        "Status": "Enabled",
        "Filter": { "Prefix": "" },
        "Transitions": [
          { "Days": 90, "StorageClass": "GLACIER_DEEP_ARCHIVE" }
        ]
      },
      {
        "ID": "abort-incomplete-multipart-uploads",
        "Status": "Enabled",
        "Filter": {},
        "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
      }
    ]
  }
SAVINGS:
  CURRENT_MONTHLY: $115.00  (5,000 GiB × $0.023 Standard)
  PROJECTED_MONTHLY: $4.95  (5,000 GiB × $0.00099 Deep Archive)
  MONTHLY_SAVING: $110.05
  ANNUAL_SAVING: $1,320.60
  CAVEATS:
    - Deep Archive 180-day minimum duration: objects deleted before day 180
      still bill. Workload is write-once with 7-year retention — no conflict.
    - Retrieval is $2-10/TB Standard (12h), $2.50/TB Bulk (48h). Budget
      separately if regulatory retrieval is likely.
    - Object Lock is NOT configured. For a compliance archive, recommend
      enabling Object Lock in COMPLIANCE mode with 2555-day retention
      (Step 5 finding — not a verdict change).
IMPLEMENTATION:
  1. CONFIRM: About to put-bucket-lifecycle-configuration on bucket
     compliance-archive-7yr. This enables Deep Archive transition at 90d
     and multipart abort. Proceed? (yes/no)
  2. aws s3api put-bucket-lifecycle-configuration \
       --bucket compliance-archive-7yr \
       --lifecycle-configuration file://lifecycle.json
  3. Verify: aws s3api get-bucket-lifecycle-configuration \
       --bucket compliance-archive-7yr
  4. Backfill existing objects > 90 days old via S3 Batch Operations
     (lifecycle only applies to objects reaching 90 days AFTER the rule
     is created):
     aws s3control create-job --account-id <acct> \
       --operation '{"S3CopyObject": {"TargetStorageClass": "GLACIER_DEEP_ARCHIVE"}}' \
       --manifest-location s3://<manifest-bucket>/manifest.csv \
       --report-spec '<report-config>' \
       --role-arn arn:aws:iam::<acct>:role/<batch-role>
```

## Verdict consistency rules (prevent misclassification)

The skill MUST emit verdicts that are mathematically and logically
self-consistent. The following rules are mandatory checks before any
output is finalized:

1. **Zero-savings rule.** If `MONTHLY_SAVING == $0.00` for every
   dimension, the verdict MUST be `ALREADY_OPTIMAL`, never
   `OPPORTUNITY_FOUND`. A finding with "OPPORTUNITY_FOUND" and
   "$0.00 monthly saving" in the same output block is a contradiction
   and a hard error.

2. **Negative-savings rule.** If the projected monthly cost is HIGHER
   than current (e.g., Intelligent-Tiering monitoring fee exceeds the
   transition saving, or minimum-duration charges net out negative),
   the verdict for that dimension is "no action" and MUST NOT be
   aggregated into `OPPORTUNITY_FOUND`. Either pick a different
   storage class or emit `ALREADY_OPTIMAL` with the reasoning that the
   current tier is already cheapest.

3. **OPPORTUNITY_FOUND requires a non-zero savings line.** When emitting
   `OPPORTUNITY_FOUND`, the SAVINGS block must show a positive
   `MONTHLY_SAVING` for at least one dimension. If no dimension has
   positive savings, downgrade to `ALREADY_OPTIMAL`.

4. **SAVINGS arithmetic check.** `CURRENT_MONTHLY − PROJECTED_MONTHLY`
   MUST equal `MONTHLY_SAVING`. If the three numbers don't reconcile,
   re-compute before emitting. Round to 2 decimal places.

5. **Dimension coverage rule.** For a versioned bucket,
   `OPPORTUNITY_FOUND` MUST include either a `NoncurrentVersionExpiration`
   rule OR a documented reason why one is not applicable (e.g., "Object
   Lock COMPLIANCE mode requires version retention"). An
   `OPPORTUNITY_FOUND` on a versioned bucket with only `Expiration`
   (current-version) rules is incomplete — it leaves noncurrent bytes
   accumulating indefinitely.

6. **Storage-class transition must include retrieval caveats.** Any
   transition to a Glacier tier MUST include the retrieval cost and
   latency in `CAVEATS`. A bare `Transitions` rule without retrieval
   cost disclosure is non-compliant.

7. **Intelligent-Tiering object-size gate.** Recommending Intelligent-
   Tiering on a bucket where the average object size < 128 KB MUST
   surface the monitoring-fee calculation and confirm it does not
   exceed the transition saving.

8. **Filter-prefix reality check.** Before emitting `OPPORTUNITY_FOUND`
   on a transition rule, verify the proposed `Filter.Prefix` matches
   actual key prefixes in Storage Lens or `list-objects-v2 --prefix`.
   A rule with a non-matching prefix is silently a no-op.

These rules are evaluated AFTER Step 6 aggregation but BEFORE emitting
the output block. If any rule fails, re-run the relevant step.

## Error handling — CLI and data-source failures

The workflow depends on S3 API, S3 Control API (Storage Lens), and
optional CloudTrail data. Each can fail independently; silent failures
produce misclassifications (especially false `ALREADY_OPTIMAL` on
buckets where Storage Lens is not enabled).

### Storage Lens failures

| Failure mode | Detection | Handling |
|---|---|---|
| `get-storage-lens-configuration` returns `NoSuchConfiguration` | API error | Storage Lens is not enabled. Fall back to `list-objects-v2` with `--page-size 1000` for a sample; flag the recommendation as MEDIUM confidence due to absent access-pattern data. Surface "Enable Storage Lens" as a parallel finding. |
| Storage Lens enabled but `ExportVersion` > 7 days stale | `ExportDataFreshness` check | Noncurrent-byte % and storage-class distribution may not reflect recent changes. Re-pull if possible; otherwise flag as MEDIUM confidence. |
| Storage Lens shows 0 noncurrent bytes on a versioned bucket | Cross-check with `list-object-versions --noncurrent-versions` | Iflist shows noncurrent versions but Storage Lens shows 0, the dashboard is misconfigured. Trust the direct API call. |

### S3 API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `get-bucket-lifecycle-configuration` returns `NoSuchLifecycleConfiguration` (404) | HTTP 404 | This is NORMAL — the bucket has no lifecycle. Proceed with full recommendation; do NOT treat as an error. |
| `get-bucket-versioning` returns `{}` (empty) | Response body empty | Versioning was never enabled. Skip the noncurrent-version dimension entirely. |
| `list-multipart-uploads` returns empty `Uploads` array | `len(Uploads) == 0` | No stale multipart uploads. Still emit the `AbortIncompleteMultipartUpload` rule as preventive; do not mark multipart dimension as OPPORTUNITY_FOUND. |
| `put-bucket-lifecycle-configuration` fails with `MalformedXML` | API error | The JSON payload has a schema error. Common causes: `NoncurrentDays` < 1, `Filter` and `Prefix` at the same rule level, or unsupported `StorageClass` value. Validate against the S3 Lifecycle schema and retry. |
| `list-objects-v2` returns `AccessDenied` | API error | The role lacks `s3:ListBucket` on the bucket. Surface as a BLOCKED finding; recommend the operator grant `s3:ListBucket` and `s3:GetLifecycleConfiguration` to the audit role. |
| `list-objects-v2` is paginating > 100 pages on a large bucket | Pagination count | STOP iterating live. Use S3 Inventory (daily export) or Storage Lens aggregate metrics instead. Live iteration of a billion-object bucket can take hours and incur request charges. |

### Object Lock interaction failures

| Failure mode | Detection | Handling |
|---|---|---|
| Lifecycle `ExpirationInDays` shorter than Object Lock retention | Cross-check `get-object-lock-configuration` retention period vs `ExpirationInDays` | The rule is silently a no-op on locked objects. Surface as a CONFIG finding; do not change the verdict based on the (silently ineffective) expiration rule. |
| Object Lock `GOVERNANCE` mode on compliance data | `Mode == GOVERNANCE` for a compliance workload | Surface that any principal with `s3:BypassGovernanceRetention` can shorten retention. Recommend `COMPLIANCE` mode. This is a finding, not a verdict change. |

### Batch Operations failures

| Failure mode | Detection | Handling |
|---|---|---|
| `create-job` fails with `AccessDenied` | API error | The role lacks `s3control:CreateJob`. Batch Operations requires a dedicated role with `s3:ObjectLambda`/`s3:ReplicateObject` permissions. Surface the IAM requirement in the IMPLEMENTATION block. |
| Batch job manifest generation fails | Manifest S3 location not writable | The manifest bucket must be in the same region as the Batch Operations job. Verify region alignment before emitting the IMPLEMENTATION step. |

### Rate-limit and large-batch guidance

For fleet-wide lifecycle audits covering > 100 buckets:

1. **Serialize, do not parallelize** the `put-bucket-lifecycle-configuration`
   calls across buckets in the same region. S3 Control API has a
   sustained rate limit of ~5 lifecycle-configuration puts per second
   per account; parallel puts will throttle.
2. **Page list-buckets by region** using `--region <region>` on each
   call. A global `list-buckets` returns buckets across all regions,
   but lifecycle configuration is region-specific.
3. **For > 1,000 buckets**, split into batches of 50 buckets per
   operator CONFIRM gate. Each batch emits a single consolidated
   CONFIRM; the operator reviews the savings rollup before applying.
4. **Verify propagation** after each batch: lifecycle rules are
   eventually consistent (~24 hours for first execution). Surface this
   in the post-apply verification step.

## Rollback procedure (beyond JSON backup)

The pre-flight captures a JSON backup of the current lifecycle config.
Rollback is a three-step procedure — the JSON backup alone is
insufficient because lifecycle rules are eventually consistent and
objects may have already transitioned.

1. **Restore the prior configuration:**
   ```bash
   aws s3api put-bucket-lifecycle-configuration \
     --bucket <name> \
     --lifecycle-configuration file://<name>-lifecycle-backup-<timestamp>.json
   ```
   This stops FUTURE transitions but does not revert objects that have
   already moved to a cheaper tier.

2. **Identify objects that transitioned during the bad window:**
   ```bash
   # Find objects that transitioned to the target storage class
   # between the bad-put timestamp and the rollback timestamp.
   aws s3api list-objects-v2 --bucket <name> \
     --query "Contents[?StorageClass=='STANDARD_IA']" \
     --output json > transitioned-objects.json
   ```
   For large buckets, use S3 Inventory (daily export) filtered by
   storage-class column instead of `list-objects-v2`.

3. **Restore the storage class of affected objects via S3 Batch
   Operations:**
   ```bash
   aws s3control create-job --account-id <acct> \
     --operation '{"S3CopyObject": {"TargetStorageClass": "STANDARD",
       "ReplaceMetadata": {"ContentType": "application/octet-stream"}}}' \
     --manifest-location s3://<manifest-bucket>/manifest.csv \
     --report-spec '{"ReportFormat":"Report_20170828","Bucket":"s3://<report-bucket>","Enabled":true,"ReportScope":"AllTasks"}' \
     --role-arn arn:aws:iam::<acct>:role/<batch-role> \
     --client-request-token $(uuidgen)
   ```
   This copies each object back to Standard. The copy operation incurs
   request and data-transfer charges — include them in the rollback
   cost estimate.

4. **Verify Storage Lens metrics stabilize** within 24-48 hours post-
   rollback. The noncurrent-byte % and storage-class distribution
   should return to pre-bad-put levels.

**Cost of rollback:** a bad lifecycle put on a 100 TB bucket that
triggers a mass Standard → Standard-IA transition costs ~$50-150 in
request fees (1 PUT per object on transition) plus ~$1,000-2,000 in
Batch Operations copy-back fees. Surface this in the CONFIRM gate
before applying any lifecycle change on a large bucket.

## Cross-region cost variance detail

The Quick reference pricing table is us-east-1 baseline. S3 pricing
varies materially by region; a recommendation that saves money in
us-east-1 may save MORE or LESS in another region:

| Region | Standard $/GB-mo | Standard-IA $/GB-mo | Deep Archive $/GB-mo | Notes |
|---|---|---|---|---|
| us-east-1, us-west-2 | 0.023 | 0.0125 | 0.00099 | Baseline |
| eu-west-1 (Ireland) | 0.024 | 0.013 | 0.001 | ~4% premium |
| eu-central-1 (Frankfurt) | 0.0245 | 0.013 | 0.001 | ~7% premium; high egress |
| ap-southeast-1 (Singapore) | 0.025 | 0.0141 | 0.001 | ~9% premium |
| ap-southeast-2 (Sydney) | 0.025 | 0.014 | 0.0011 | ~9% premium |
| ap-northeast-1 (Tokyo) | 0.025 | 0.0138 | 0.0011 | ~9% premium |
| ap-south-1 (Mumbai) | 0.0259 | 0.0144 | 0.00114 | ~13% premium |
| sa-east-1 (São Paulo) | 0.0309 | 0.01688 | 0.00153 | ~35% premium; egress highest |
| af-south-1 (Cape Town) | 0.0304 | 0.0166 | 0.00153 | ~32% premium |

**Decision impact:**

- **High-premium regions (sa-east-1, af-south-1):** lifecycle
  transitions capture MORE savings because the gap between Standard
  and Glacier is wider. Recommend AGGRESSIVE transitions (earlier
  `Days` thresholds) — the math favours moving to Glacier IR or
  Flexible sooner.
- **Low-premium regions (us-east-1, us-east-2):** the savings delta
  is smaller; the Intelligent-Tiering monitoring fee and minimum-
  duration charges eat a larger share of the saving. Be more
  conservative on small-object buckets.
- **Always re-state the regional rate** in the SAVINGS block when the
  bucket is not in us-east-1. Pull the rate from the AWS Pricing API
  (`aws pricing get-products --service-code AmazonS3 --filters ...`)
  rather than estimating from the multiplier.

## Anti-Patterns — NEVER

- NEVER recommend a transition to Standard-IA or One-Zone-IA for objects
  smaller than 128 KB. The minimum billable size makes IA MORE expensive than
  Standard. Always check average object size from Storage Lens before
  recommending IA tiers.

- NEVER recommend a storage-class transition without modeling minimum-duration
  charges. An object moved to Standard-IA on day 5 and deleted on day 6 bills
  30 days of IA charges — net more expensive than Standard. Surface
  `CAVEATS: 30-day minimum-duration charge applies` on every IA recommendation.

- NEVER propose `ExpirationInDays` on a versioned bucket without a
  corresponding `NoncurrentVersionExpiration` rule. Expiration on the current
  version creates a new noncurrent version — without cleanup, the bucket grows
  instead of shrinks. This is the single most common lifecycle misconfiguration.

- NEVER recommend Glacier Flexible Retrieval or Deep Archive for objects that
  are accessed more than once per quarter. Retrieval fees ($2.50-30/TB) wipe
  out the storage saving in a single retrieval. Glacier is for archive only.

- NEVER recommend Intelligent-Tiering on a bucket of millions of small objects
  without surfacing the monitoring fee. At $0.0025/1,000 objects, a bucket of
  10M small JSON files costs $25/month in monitoring alone — often more than
  the transition saving.

- NEVER enable Object Lock in COMPLIANCE mode without confirming the retention
  period with the operator. COMPLIANCE mode retention CANNOT be shortened or
  bypassed, even by root. A wrong retention period is a permanent lock.

- NEVER propose lifecycle transitions on a directory bucket (S3 Express One
  Zone). Directory buckets do not support lifecycle, Object Lock, or Glacier
  tiers. Surface the cost-per-GB ($0.16) as a finding; the verdict for a
  directory bucket is ALREADY_OPTIMAL for latency-critical ML/AI workloads.

- NEVER propose `Expiration` rules on S3 Tables data prefixes. Apache Iceberg
  tables manage their own lifecycle via table APIs. Surface as a finding only.

- NEVER assume `lifecycle-configuration` returns an empty object when no rules
  exist. It returns a 404 `NoSuchLifecycleConfiguration` error — handle
  gracefully and proceed with the recommendation.

- NEVER auto-apply `put-bucket-lifecycle-configuration` without the CONFIRM
  gate. A wrong prefix or filter can mass-transition or mass-delete objects.
  Always emit `CONFIRM: About to <action>...` and wait for explicit operator
  approval.

- NEVER trust a single Storage Lens snapshot. Lifecycle recommendations should
  use at least 30 days of Storage Lens data to capture the access-pattern trend.
  A 1-day snapshot can misclassify a daily-access bucket as cold.

- NEVER recommend deleting noncurrent versions without confirming the workload
  can tolerate loss of version history. Some compliance frameworks require
  version retention — surface Object Lock as the parallel control.

- NEVER assume Cross-Region Replication (CRR) preserves the SOURCE storage
  class. CRR defaults to copying objects in the **destination bucket's
  default storage class** (Standard unless the replication rule overrides
  it). A common anti-pattern: source bucket transitions to Glacier Deep
  Archive, but the CRR destination remains in Standard indefinitely —
  doubling the storage bill instead of halving it. **Why this happens:**
  replication rules are independent of lifecycle rules; lifecycle does not
  propagate across the replication boundary. Always design source AND
  destination lifecycle rules in tandem, OR explicitly set
  `ExistingObjectReplication: false` and `StorageClass` on the replication
  rule to match the source tier.

- NEVER emit `OPPORTUNITY_FOUND` on a bucket where the projected monthly
  cost equals or exceeds the current monthly cost. The verdict requires
  a positive net saving — minimum-duration charges, Intelligent-Tiering
  monitoring fees, and request fees on bulk transitions can net out
  negative. If the math shows $0 or negative saving, the verdict is
  `ALREADY_OPTIMAL` for that dimension, not `OPPORTUNITY_FOUND`.

- NEVER recommend a lifecycle transition on a bucket without first
  confirming the average object size from Storage Lens. A bucket of
  millions of < 128 KB objects costs MORE in any IA tier than in Standard,
  due to the 128 KB minimum billable size. Surface the object-size
  distribution as the gating check before any transition recommendation.

- NEVER conflate `ExpirationInDays` (current version) with
  `NoncurrentVersionExpiration.NoncurrentDays` (prior versions). The two
  are independent — a rule that expires the current version creates a
  new noncurrent version on a versioned bucket, INCREASING storage if no
  parallel noncurrent rule exists. This is the single most common
  lifecycle misconfiguration in production S3 environments.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`put-bucket-lifecycle-configuration`, `delete-bucket-lifecycle`,
  `create-job` for Batch Operations), emit: `CONFIRM: About to <action> on
  bucket <name> in account <account> region <region>. This affects
  <consequence>. Proceed? (yes/no)`. Do NOT execute until the operator
  confirms.

- **Capture current state for rollback.** Before applying:
  `aws s3api get-bucket-lifecycle-configuration --bucket <name> --output json >
  /tmp/<name>-lifecycle-backup-$(date +%s).json`. S3 lifecycle is not versioned
  — a put replaces the entire configuration atomically.

- **Verify Object Lock retention before expiration.** If the bucket has Object
  Lock, every proposed `ExpirationInDays` MUST be >= the longest retention
  period. Otherwise the rule is silently a no-op on locked objects — surface
  as a finding, not an error.

- **Verify versioning status before noncurrent rules.** If versioning is
  `Suspended`, `NoncurrentVersionTransitions` still applies to existing
  noncurrent versions. If versioning was never enabled, skip the dimension.

- **Filter scope check.** Before applying, verify the filter prefix matches the
  intended key layout. `Prefix: "logs/"` on a bucket with keys under
  `application/logs/` matches nothing.

- **Intelligent-Tiering Archive configuration check.** When recommending
  Intelligent-Tiering with custom Archive tiers, verify the
  `Tierings[].Days` values are valid (>= 90 for ARCHIVE_ACCESS, >= 180 for
  DEEP_ARCHIVE_ACCESS).

- **Batch Operations IAM check.** `s3control create-job` requires a role with
  `s3:ObjectLambda`/`s3:ReplicateObject` permissions depending on the
  operation. Verify the role exists before recommending Batch.

## Recent AWS features (2024-2026)

- **S3 Intelligent-Tiering Archive configurations (2024-2025):** Intelligent-
  Tiering now supports configurable Archive Access and Deep Archive Access
  tiers (`Tierings[{AccessTier: ARCHIVE_ACCESS, Days: N}]`). Default is 90/180
  days; tunable for known-cold data to capture savings faster. No retrieval fee
  on the tier transition itself; standard Glacier retrieval fees apply on read.

- **S3 Storage Lens (general availability, expanded 2024-2026):** Organization-
  wide dashboards with 29+ metrics including noncurrent-byte %, storage-class
  distribution, object-age histogram, and prefix-level drill-down. Always pull
  Storage Lens before recommending a transition — it provides the access-pattern
  evidence the recommendation needs.

- **S3 Tables (managed Apache Iceberg, 2025):** Tabular data stored in S3 with
  Iceberg table format, supporting ACID transactions, schema evolution, and
  time travel. Tables have their own lifecycle (snapshot expiration,
  compaction) — do NOT propose S3 lifecycle rules on table data prefixes.

- **S3 Express One Zone (directory buckets, 2023-2025):** Single-AZ directory
  buckets with ms-latency HEAD/GET, designed for ML/AI training and high-
  performance analytics. $0.16/GB, no lifecycle support, no Object Lock.
  Use for the active training set; tier to general-access buckets after.

- **Glacier Instant Retrieval (GA):** Millisecond-latency retrieval at $0.004/GB
  with 90-day minimum. The right tier for quarterly-accessed data that still
  needs ms reads (analytics, compliance lookups).

- **S3 Batch Operations (expanded):** Supports `S3CopyObject` with
  `TargetStorageClass` for one-time backfill migrations of existing objects
  (lifecycle only transitions new objects going forward). Pair with lifecycle
  for the complete migration path.

- **S3 Object Lock expanded retention options:** `COMPLIANCE` mode now supports
  per-object legal hold alongside retention period. Use legal hold for
  indefinite holds (litigation, investigation); use retention period for
  regulatory horizons.

## Domain

AWS CloudOps / S3 Storage Cost Optimisation & Lifecycle Design.

## AWS documentation

- **Amazon S3 User Guide** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
- **Managing your storage lifecycle** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html
- **Amazon S3 Storage Classes** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html
- **S3 Intelligent-Tiering** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html#sc-d behavior-data-retrieval
- **S3 Storage Lens** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage_lens_basics_metrics.html
- **S3 Object Lock** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html
- **S3 Batch Operations** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops.html
- **AWS CLI Command Reference: s3api** — https://docs.aws.amazon.com/cli/latest/reference/s3api/
- **S3 Express One Zone** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-express-one-zone.html
- **S3 Tables** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/tables.html
