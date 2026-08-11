---
name: s3-intelligent-tiering-optimizer
description: >-
  Optimises S3 storage cost with Intelligent-Tiering: enables
  bucket-level IntelligentTieringConfiguration, tunes the Archive Access
  (90-day) and Deep Archive Access (180-day) tiers, models the $0.0025
  per-1,000-objects monitoring fee, and emits a deterministic verdict
  (OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL) per bucket with the
  exact put-bucket-intelligent-tiering-configuration payload and a net
  dollar savings estimate. Use when deciding whether to enable
  Intelligent-Tiering on a bucket with unknown or mixed access
  patterns, when the monitoring fee might exceed the saving on small
  objects (<128 KB), when predictable access patterns make
  lifecycle rules cheaper, or when archive-tier timing needs tuning.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). No AWS CLI required for offline configuration
  classification. Live-account audits use aws s3api
  list-bucket-intelligent-tiering-configurations,
  put-bucket-intelligent-tiering-configuration,
  get-bucket-intelligent-tiering-configuration,
  list-objects-v2 (with --page-size for inventory), and aws s3control
  get-storage-lens-configuration (AWS CLI v2, SSO or key-based
  credentials). Pricing is us-east-1 published rates as of 2026;
  re-state the regional rates from the reference matrix before
  producing dollar estimates for other regions.
keywords:
  - S3
  - Intelligent-Tiering
  - storage class
  - IntelligentTieringConfiguration
  - Archive Access
  - Deep Archive Access
  - monitoring fee
  - small object fee aggregation
  - Frequent Access tier
  - Infrequent Access tier
  - storage cost optimization
  - access pattern analysis
  - put-bucket-intelligent-tiering-configuration
  - Storage Lens
  - lifecycle vs Intelligent-Tiering
  - S3 Batch Operations
tags: [s3, storage, cost-optimization, intelligent-tiering, access-pattern, finops]
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
  lifecycle_status: active
  verdict_shape: "OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL"
  when_to_use: >-
    Deciding whether to enable S3 Intelligent-Tiering on a bucket with
    unknown or mixed access patterns, tuning the Archive Access and
    Deep Archive Access tier timing, modelling the $0.0025/1,000-objects
    monitoring fee against savings, deciding between Intelligent-Tiering
    and a fixed lifecycle policy for predictable workloads, or auditing
    whether an existing Intelligent-Tiering configuration is optimal.
  activation_triggers:
    - "enable S3 Intelligent-Tiering"
    - "Intelligent-Tiering monitoring fee"
    - "S3 Intelligent-Tiering vs lifecycle"
    - "S3 archive tier configuration"
    - "S3 Deep Archive Access tier"
    - "S3 access pattern analysis"
    - "should I use Intelligent-Tiering"
    - "IntelligentTieringConfiguration"
    - "put-bucket-intelligent-tiering-configuration"
    - "S3 small object fee aggregation"
    - "S3 storage cost optimization"
  invocation_schema: >-
    Input: either (a) a bucket configuration (IntelligentTieringConfiguration
    JSON, Storage Lens metrics summary, optional object-size histogram),
    OR (b) a bucket name for live-account optimisation. Output:
    deterministic BUCKET/VERDICT/REASON/RECOMMENDATION/SAVINGS/IMPLEMENTATION
    block per bucket, where VERDICT is one of OPTIMIZED,
    OPPORTUNITY_FOUND, ALREADY_OPTIMAL.
---

# S3 Intelligent-Tiering Optimizer

## What this skill does

Translates an S3 access-pattern posture into a concrete
Intelligent-Tiering configuration (IntelligentTieringConfiguration) and a
dollar-denominated net savings estimate. The verdict is the
**highest-leverage action** across four dimensions — Intelligent-Tiering
eligibility, archive-tier tuning, monitoring-fee math, and
fixed-lifecycle-vs-Intelligent-Tiering trade-off — applied in priority
order. Always pairs the recommendation with the exact
`put-bucket-intelligent-tiering-configuration` payload so the operator can
paste, review, and apply. When Intelligent-Tiering is NOT the right tier,
emits `ALREADY_OPTIMAL` with the explicit reason (small-object surcharge,
predictable access pattern, or a fixed lifecycle rule being cheaper).

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds + Intelligent-Tiering tier table | Before any operation |
| **§ Decision tree** | When Intelligent-Tiering wins vs Standard / lifecycle | Choosing the storage tier |
| **§ Expert heuristic** | The non-obvious rules (monitoring-fee gate, 128 KB minimum, tiering-incrementality) | Understanding the cost model |
| **§ Pre-flight** | Bucket metadata gate — directory bucket, Object Lock, existing config | Before executing any CLI |
| **§ Process** | Per-bucket optimisation logic (Steps 0-5) | When classifying a bucket |
| **§ STRICT output contract** | The deterministic BUCKET/VERDICT/REASON/RECOMMENDATION/SAVINGS/IMPLEMENTATION template | Formatting the response |
| **§ Anti-Patterns** | Top-5 NEVER list — the most common misconfigurations | Review before risky operations |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `OPPORTUNITY_FOUND` | Intelligent-Tiering is eligible and net-saving-positive AND one of (not enabled, archive tiers unconfigured, wrong filter scope, wrong tier timing) | Emit recommended IntelligentTieringConfiguration JSON + savings estimate |
| `OPTIMIZED` | An Intelligent-Tiering configuration change was applied this session and verified | Emit post-state verification and recompute savings |
| `ALREADY_OPTIMAL` | Intelligent-Tiering is ineligible (small objects, predictable access, directory bucket) OR already optimally configured | No action — confirm posture |

**Priority order for evaluation dimensions (apply in this sequence,
aggregate all applicable into a single recommendation):**

1. **Eligibility gate** — directory buckets, S3 Tables prefixes, and
   Object-Lock-only compliance archives do not benefit from
   Intelligent-Tiering. Resolve first to avoid wasted analysis.
2. **Monitoring-fee gate** — the $0.0025/1,000-objects fee must not exceed
   the transition saving. The gate is mandatory for buckets with a high
   count of small objects.
3. **Archive-tier tuning** — most under-configured Intelligent-Tiering
   setups use the defaults only; Archive Access at 90 days and Deep
   Archive Access at 180 days are tunable for known-cold data.
4. **Intelligent-Tiering-vs-lifecycle trade-off** — for predictable
   access patterns a fixed lifecycle rule is cheaper (no monitoring fee);
   surface the comparison.

**Cost baseline summary (us-east-1, 2026, USD per GB-month):**

| Tier | $/GB-mo | Trigger | Monitoring | Retrieval |
|---|---|---|---|---|
| Frequent Access | 0.023 | Default (hot) | $0.0025/1K obj (whole bucket) | free |
| Infrequent Access | 0.0125 | 30 consecutive days no access | included | $0.01/GB |
| Archive Access | 0.0036 | 90 consecutive days no access (configurable) | included | $0.03/GB Std |
| Deep Archive Access | 0.00099 | 180 consecutive days no access (configurable) | included | $0.02-10/GB tiered |

For comparison: Standard $0.023, Standard-IA $0.0125 (30-day minimum),
Glacier Instant Retrieval $0.004 (90-day minimum), Glacier Deep Archive
$0.00099 (180-day minimum). Intelligent-Tiering has NO minimum-duration
charge on the Frequent/Infrequent tiers — the only IA-style tier with
that property — which is the basis of its value proposition for unknown
patterns. **Load `references/intelligent-tiering-cost-model.md` before
producing dollar estimates** — it contains the full request-fee table,
retrieval-tier breakdowns, regional multipliers, and the small-object-fee
aggregation math. The inline table is a quick-selection aid, not a
quoting source.

## Decision tree — when Intelligent-Tiering wins

Read top-to-bottom; **first match wins**. Always pair the verdict with
access-pattern evidence from Storage Lens — a tree verdict without
observed access data is a guess.

```
START: Is the average object size >= 128 KB?
├── NO  → Standard (IA minimum billable size 128 KB; monitoring fee
│         would exceed transition saving). Verdict: ALREADY_OPTIMAL
│         for Intelligent-Tiering. Surface small-object fee aggregation
│         (Step 0) as a parallel finding.
└── YES → Is the access pattern genuinely UNKNOWN or MIXED?
    ├── NO  → Is the pattern predictable?
    │   ├── Daily/weekly access → Standard. Cheaper than
    │   │   Intelligent-Tiering (no monitoring fee).
    │   ├── Monthly access      → Fixed lifecycle to Standard-IA at 30d
    │   │   (no monitoring fee, same $/GB as Infrequent tier).
    │   ├── Quarterly+ access   → Fixed lifecycle to Glacier IR / Deep
    │   │   Archive (cheaper than Archive Access tier for known-cold).
    │   └── UNKNOWN (no Storage Lens data) → Intelligent-Tiering is the
    │       safest default — the monitoring fee is the cost of access-
    │       pattern discovery. Plan a 90-day review.
    └── YES → Is the monitoring fee < the projected transition saving?
        ├── NO  → Standard (monitoring fee exceeds saving). Verdict:
        │       ALREADY_OPTIMAL with the math.
        └── YES → Intelligent-Tiering. Pick the archive-tier timing:
            ├── Known cold data, 12h-retrieve OK → Deep Archive Access
            │   at 90 days (override default 180; capture saving faster).
            ├── Known cold data, ms-retrieve needed → Archive Access
            │   at 90 days (Glacier-tier $0.0036/GB).
            └── Default (no tuning) → Archive Access 90d, Deep Archive
                Access 180d.
```

**Special-case branches (override the main tree):**

- **Directory bucket (S3 Express One Zone, name suffix `--x-s3`):**
  Intelligent-Tiering is NOT supported. Verdict is ALREADY_OPTIMAL for
  ML/AI latency-critical workloads. Do not run the tree.
- **Object Lock COMPLIANCE mode retention:** Intelligent-Tiering tier
  transitions are honoured, but archive tiers defeat compliance-lookup
  latency. Use Frequent Access only (no archive-tier configuration) for
  compliance workloads requiring periodic retrieval.
- **Cross-Region Replication destination:** Intelligent-Tiering applies
  to the destination independently of the source. Run the tree on both
  sides.
- **S3 Tables (Apache Iceberg) prefixes:** table lifecycle is managed
  via table APIs. Surface as a finding only; do not propose
  Intelligent-Tiering on table-data prefixes.

## Expert heuristic — the non-obvious rules

**One-line takeaway:** Intelligent-Tiering is the only S3 tier that
optimises the storage class on a per-object basis without a
minimum-duration charge on the Frequent/Infrequent tiers — but the
$0.0025/1,000-objects monitoring fee is the gating cost that decides
whether it wins. Five non-obvious rules drive the verdict:

- **Rule 1 — Monitoring fee is a flat tax on object count, not bytes.**
  A bucket of 10 million 1 KB objects pays $25/month in monitoring fees
  and captures ~$0 in transition saving (Infrequent-tier 128 KB minimum
  billable size means small objects don't actually move). The
  monitoring-fee gate (Step 2) is the single most important check.

- **Rule 2 — Intelligent-Tiering has no minimum-duration charge on
  Frequent/Infrequent.** A Standard-IA transition bills 30 days minimum
  even if the object is deleted on day 1. Intelligent-Tiering bills
  the Infrequent tier per-day, no minimum. This makes Intelligent-Tiering
  cheaper for short-lived-but-unknown-pattern workloads where
  lifecycle-driven IA would incur minimum-duration charges.

- **Rule 3 — Archive Access and Deep Archive Access DO have 90/180-day
  minimums.** The Frequent/Infrequent tiers are minimum-free; the
  archive tiers are NOT. A 60-day-old object moved to Archive Access and
  then retrieved bills the 90-day minimum. Always surface the
  minimum-duration caveat on archive-tier recommendations.

- **Rule 4 — Archive-tier timing is configurable (90/180 are defaults,
  not minimums).** `Tierings[{AccessTier: ARCHIVE_ACCESS, Days: 90}]`
  is the default lower bound; you can configure Days >= 90 for Archive
  Access and Days >= 180 for Deep Archive Access. Shorter windows
  capture savings faster on known-cold data.

- **Rule 5 — Intelligent-Tiering and lifecycle rules are separate
  systems.** A lifecycle rule transitions objects based on age;
  Intelligent-Tiering transitions based on access pattern. They can
  coexist on the same bucket but should not target the same prefix
  (double-tiering produces unpredictable results). Pick one per prefix.

## Pre-flight: bucket metadata gate

Run before classification. Misclassifying these produces false positives.

**Pagination:** `list-bucket-intelligent-tiering-configurations`
paginates at 100 configurations/page. For most buckets there is only one
configuration (named `Config` by default). `list-objects-v2` paginates
at 1,000 keys/page — for large buckets, do NOT iterate live; pull Storage
Lens aggregate metrics instead.

**Live-account pre-flight (skip if offline audit):**
1. `aws s3api list-bucket-intelligent-tiering-configurations --bucket
   <name>` — capture existing configurations (Id, Status, Tierings,
   Filter).
2. `aws s3api get-bucket-lifecycle-configuration --bucket <name>` —
   capture any lifecycle rules that overlap prefixes targeted for
   Intelligent-Tiering.
3. `aws s3control get-storage-lens-configuration --config-id default`
   — capture object-size distribution, access-pattern trend, average
   object age.
4. `aws s3api get-object-lock-configuration --bucket <name>` — if
   Object Lock is enabled, restrict archive-tier recommendations for
   compliance workloads.
5. `aws s3api list-objects-v2 --bucket <name> --page-size 1000
   --max-items 100` — sample the smallest 100 keys for the
   small-object heuristic (alternative: read the ObjectSizeDistribution
   from Storage Lens).
6. For directory buckets: bucket name suffix `--x-s3` signals no
   Intelligent-Tiering support; skip the configuration dimensions.

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Bucket configuration is not
valid JSON or is missing required fields — cannot classify.` and
`REMEDIATION: Re-fetch with aws s3api
list-bucket-intelligent-tiering-configurations --bucket <name> --output
json and re-audit.`

| Bucket attribute | Effect on audit |
|---|---|
| Bucket is a directory bucket (name suffix `--x-s3`) | Intelligent-Tiering NOT supported. Verdict: ALREADY_OPTIMAL for ML/AI workloads. |
| Bucket has S3 Tables prefixes (Apache Iceberg) | Do not propose Intelligent-Tiering on table-data prefixes; tables manage their own lifecycle. Surface as a finding only. |
| Object Lock `Enabled` COMPLIANCE mode | Restrict archive-tier recommendations for compliance workloads requiring periodic retrieval; Frequent Access only. |
| Existing IntelligentTieringConfiguration with Status `Enabled` | Compare actual tier distribution from Storage Lens before re-recommending. |
| Existing lifecycle rule with overlapping prefix | Surface the overlap; pick one system per prefix. |
| Cross-Region Replication destination | Intelligent-Tiering applies to the destination independently. Run the tree on both sides. |
| Requester-pays bucket | Monitoring fee bills the bucket owner; retrieval bills the requester. Note in savings estimate. |

## Process — optimisation logic (apply in order, aggregate all applicable)

### Step 0: Expert knowledge — non-obvious Intelligent-Tiering behaviors

These behaviors are easy to misjudge without operational S3 experience.
Each changes a recommendation if ignored:

- **The monitoring fee bills ALL objects in the configuration's filter
  scope, not just the ones that tier.** A configuration with
  `Filter: {Prefix: "data/"}` bills $0.0025/1,000 for every object under
  `data/`, even those that never leave the Frequent tier. The fee is the
  cost of access-pattern monitoring — it bills whether or not a tiering
  event occurs.

- **Archive-tier transitions are configurable.** Default: Archive Access
  after 90 consecutive days of no access, Deep Archive Access after 180.
  Override via `Tierings[{AccessTier: ARCHIVE_ACCESS, Days: N}]` where
  N >= 90, and `Tierings[{AccessTier: DEEP_ARCHIVE_ACCESS, Days: N}]`
  where N >= 180. For known-cold data, shorter windows capture savings
  faster.

- **Intelligent-Tiering does not have a minimum-duration charge on
  Frequent/Infrequent tiers.** This is unique among S3 IA-style tiers.
  Standard-IA, One-Zone-IA, and Glacier IR all carry 30/90-day
  minimums. For short-lived unknown-pattern workloads, Intelligent-
  Tiering is cheaper than a lifecycle-driven IA transition that incurs
  the minimum-duration charge.

- **Archive Access and Deep Archive Access tiers DO carry 90/180-day
  minimums.** The Frequent/Infrequent tiers being minimum-free does NOT
  extend to the archive tiers. Always surface the minimum-duration
  caveat on archive-tier recommendations.

- **The Infrequent tier has a 128 KB minimum billable size.** A 4 KB
  object that tiers to Infrequent is billed as 128 KB — a 32x storage-
  cost inflation. This is why the monitoring-fee gate is critical for
  small-object buckets.

- **Intelligent-Tiering tier transitions are not instantaneous.** S3
  evaluates access patterns once daily; tiering transitions occur over
  hours, not minutes. Do not alarm on a 24-hour lag between access
  pattern change and tier movement.

- **A configuration with a filter that matches no objects is silently a
  no-op.** `Filter: {Prefix: "logs/2024/"}` on a bucket where keys live
  under `2025/logs/` matches nothing. Cross-check the prefix against
  the actual key layout before declaring ALREADY_OPTIMAL.

- **Small object fee aggregation (2025-2026 feature).** For buckets
  with very large counts of small objects, AWS can aggregate the
  Intelligent-Tiering monitoring and small-object fees to reduce per-
  object billing overhead. This does NOT remove the monitoring fee —
  it aggregates how the fee is calculated for cost-allocation purposes.
  The monitoring fee still scales with object count; aggregation
  changes the billing presentation, not the cost.

- **Intelligent-Tiering and S3 Lifecycle can coexist on the same bucket
  but should not target the same prefix.** A lifecycle rule that
  transitions `app/logs/` to Standard-IA at 30 days AND an Intelligent-
  Tiering configuration scoped to `app/logs/` will produce unpredictable
  tier movement. Pick one system per prefix.

- **S3 Batch Operations complements Intelligent-Tiering for one-time
  migrations.** To immediately move existing Standard objects INTO
  Intelligent-Tiering (rather than waiting for the configuration to
  apply going forward), use `create-job` with `S3CopyObject` and
  `TargetStorageClass: INTELLIGENT_TIERING`.

- **Storage Lens provides the access-pattern evidence the
  configuration depends on.** Always pull Storage Lens metrics covering
  at least 30 days before recommending Intelligent-Tiering. A 1-day
  snapshot can misclassify a daily-access bucket as cold.

### Step 1: Eligibility gate

Resolve these before any further analysis. If any condition fails,
verdict is `ALREADY_OPTIMAL` for Intelligent-Tiering (with a documented
reason) — do NOT proceed to Step 2.

- **Directory bucket** (name suffix `--x-s3`): Intelligent-Tiering NOT
  supported. Surface the $0.16/GB cost as a finding.
- **S3 Tables prefixes** (Apache Iceberg): table-data prefixes manage
  their own lifecycle. Surface as a finding only.
- **Predictable access pattern with known frequency**: a fixed lifecycle
  rule is cheaper (no monitoring fee). See Step 4 for the trade-off.
- **Compliance archive with Object Lock COMPLIANCE mode requiring
  periodic retrieval**: Frequent Access only; archive tiers defeat the
  retrieval SLA.

### Step 2: Monitoring-fee gate (mandatory for small/many-object buckets)

The monitoring fee is `$0.0025 × object_count / 1000` per month. The
gate FAILS when the monitoring fee >= projected transition saving.

**Calculation:**
- `monitoring_fee_monthly = (object_count / 1000) × 0.0025`
- `projected_transition_saving_monthly = bytes_that_will_tier_GB ×
  (Frequent_rate - Infrequent_rate)` for the first tiering transition
- For small objects (< 128 KB), `bytes_that_will_tier` is effectively 0
  because the Infrequent tier's 128 KB minimum billable size prevents
  cost reduction. The monitoring fee is pure overhead.

**Threshold check:** if `monitoring_fee_monthly >
projected_transition_saving_monthly`, the verdict is `ALREADY_OPTIMAL`
for the Intelligent-Tiering dimension. Surface the calculation so the
operator sees the math.

**Small-object fee aggregation note:** for buckets with > 1 million
small objects, AWS may aggregate the per-object fees into a bulk
billing line. This does NOT change the monitoring-fee math — it changes
the cost-allocation presentation. The gate still applies.

### Step 3: Archive-tier tuning

For buckets where Intelligent-Tiering is eligible and the monitoring-fee
gate passes, evaluate the archive-tier configuration:

- **No archive tiers configured** (only Frequent + Infrequent):
  opportunity to add Archive Access at 90 days and Deep Archive Access
  at 180 days. Captures 84% storage saving on cold objects vs Standard.
- **Archive Access configured, Deep Archive Access missing:** add Deep
  Archive Access for data accessed less than yearly (12h retrieve OK).
- **Default timing (90/180 days) on known-cold data:** shorten to the
  minimum allowed (90 for Archive Access, 180 for Deep Archive Access)
  to capture savings faster.
- **Archive tiers configured on compliance workload requiring periodic
  retrieval:** surface as a finding — archive tiers defeat retrieval SLA.

### Step 4: Intelligent-Tiering-vs-lifecycle trade-off

For predictable access patterns, compare Intelligent-Tiering against a
fixed lifecycle rule:

| Pattern | Intelligent-Tiering cost | Fixed lifecycle cost | Winner |
|---|---|---|---|
| Daily access | $0.023 + monitoring | Standard $0.023 | Lifecycle (no monitoring fee) |
| Monthly access | Frequent + Infrequent auto, + monitoring | Standard -> Standard-IA at 30d | Lifecycle (same $/GB, no monitoring) |
| Quarterly access | + Archive Access auto, + monitoring | Standard -> Glacier IR at 90d | Lifecycle (Glacier IR $0.004 < Archive $0.0036? Tie — but no monitoring fee) |
| Yearly+ access | + Deep Archive Access, + monitoring | Standard -> Deep Archive at 180d | Lifecycle (no monitoring fee, same $/GB) |
| Unknown / mixed | Auto-tiers by pattern, + monitoring | Cannot predict rule | Intelligent-Tiering |

If a fixed lifecycle rule wins on cost (predictable pattern), the
verdict for the Intelligent-Tiering dimension is `ALREADY_OPTIMAL` with
a pointer to the lifecycle-optimizer skill.

### Step 5: Aggregation — emit the highest-leverage recommendation

Aggregate ALL applicable dimensions into a single recommended
IntelligentTieringConfiguration. The verdict is `OPPORTUNITY_FOUND` if
any dimension has a net-positive saving. If no dimension has an
opportunity: `ALREADY_OPTIMAL`. If the recommendation was applied this
session and verified: `OPTIMIZED`.

## STRICT output contract (per bucket)

```text
BUCKET: <bucket-name>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences citing the highest-leverage dimension and step number>
RECOMMENDATION:
  <IntelligentTieringConfiguration JSON or "No changes required">
SAVINGS:
  CURRENT_MONTHLY: $<X.XX>
  PROJECTED_MONTHLY: $<Y.YY>
  MONTHLY_SAVING: $<X.XX - Y.YY>
  ANNUAL_SAVING: $<12 × monthly>
  CAVEATS: <monitoring-fee math, archive-tier minimums, retrieval fees>
IMPLEMENTATION:
  1. aws s3api put-bucket-intelligent-tiering-configuration --bucket <name> --id <Config> --intelligent-tiering-configuration file://config.json
  2. <verification command>
  3. <backfill via S3 Batch Operations if existing objects need immediate tiering>
```

### Worked example — enable Intelligent-Tiering with archive tiers

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
      net of monitoring: $945.50/month. Monitoring fee is < 8% of saving
      — well within the gate.
    - Archive Access 90-day minimum: objects retrieved before 90 days
      bill the prorated remainder.
    - Deep Archive Access 180-day minimum applies; retrieval $0.02-10/GB.
    - Tiering transitions are asynchronous (~24h evaluation cycle).
IMPLEMENTATION:
  1. CONFIRM: About to put-bucket-intelligent-tiering-configuration on
     bucket app-data-mixed (account <acct>, region us-east-1). This
     enables Intelligent-Tiering with Archive Access at 90d and Deep
     Archive Access at 180d. The configuration applies to all objects
     (no filter). Monitoring fee: ~$75/month. Proceed? (yes/no)
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

### Worked example — small objects rejected by monitoring-fee gate

This example demonstrates the **negative-savings rule**: when the
monitoring fee exceeds the transition saving, the verdict is
`ALREADY_OPTIMAL`, never `OPPORTUNITY_FOUND` with negative savings.

```text
BUCKET: app-config-state
VERDICT: ALREADY_OPTIMAL
REASON: Bucket contains 8.2M objects averaging 4.2 KB each (Step 2
  monitoring-fee gate FAILS). The monitoring fee ($20.50/month) alone
  exceeds the entire projected transition saving ($0 — objects below
  the Infrequent tier's 128 KB minimum billable size cannot save).
  Intelligent-Tiering is REJECTED. Standard is already the cheapest
  tier for this object-size profile.
RECOMMENDATION: No changes required. Optionally enable small-object fee
  aggregation for cost-allocation visibility (does NOT change the
  monitoring-fee math).
SAVINGS:
  CURRENT_MONTHLY: $10.09
    - Storage: 32.0 GiB × $0.023 = $0.74
    - GETs: 8.2M × 3/month × $0.00038/1K = $9.35
    - PUTs: negligible (write-once workload)
  PROJECTED_MONTHLY (Intelligent-Tiering, best case):
    - Monitoring fee: 8,200,000 / 1,000 × $0.0025 = $20.50
    - Storage: 32.0 GiB × $0.023 = $0.74 (no saving — all objects < 128 KB)
    - GETs: 8.2M × 3/month × $0.00038/1K = $9.35
    - Total projected: $30.59
  MONTHLY_SAVING: -$20.50  (NEGATIVE — monitoring fee alone exceeds saving)
  ANNUAL_SAVING: -$246.00
  CAVEATS: The proposed plan INCREASES cost by $20.50/month. The verdict
    is ALREADY_OPTIMAL because Standard is already the cheapest applicable
    tier for this object-size profile. Do NOT enable Intelligent-Tiering.
IMPLEMENTATION: None required. Re-evaluate if average object size grows
  above 128 KB.
```

### Worked example — already optimal Intelligent-Tiering setup

```text
BUCKET: data-lake-curated
VERDICT: ALREADY_OPTIMAL
REASON: Bucket already has an Intelligent-Tiering configuration with
  Archive Access at 90 days and Deep Archive Access at 180 days, scoped
  to the correct prefix. Storage Lens shows the tier distribution matches
  the access pattern (Frequent 22%, Infrequent 45%, Archive 23%, Deep
  Archive 10%). Monitoring fee ($150/month) is < 7% of the net saving
  ($2,100/month).
RECOMMENDATION: No changes required.
SAVINGS:
  CURRENT_MONTHLY: $2,890.00  (current Intelligent-Tiering blended)
  PROJECTED_MONTHLY: $2,890.00  (no change)
  MONTHLY_SAVING: $0.00
  ANNUAL_SAVING: $0.00
  CAVEATS: Monitoring fee: $150.00/month (60M objects). Tier distribution
    is healthy — no tuning required.
IMPLEMENTATION: None required. Posture is correct for the workload.
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
   than current (e.g., monitoring fee exceeds the transition saving),
   the verdict for that dimension is "no action" and MUST NOT be
   aggregated into `OPPORTUNITY_FOUND`. Emit `ALREADY_OPTIMAL` with the
   reasoning that the current tier is already cheapest.

3. **Monitoring-fee gate.** Recommending Intelligent-Tiering on a bucket
   where `monitoring_fee_monthly > projected_transition_saving_monthly`
   is a hard error. Always surface the monitoring-fee calculation in the
   SAVINGS block before the verdict.

4. **128 KB minimum gate.** Recommending Intelligent-Tiering on a bucket
   where the average object size < 128 KB MUST surface the Infrequent-
   tier 128 KB minimum billable size and confirm it does not defeat the
   saving. For buckets where the majority of objects are < 128 KB, the
   verdict is `ALREADY_OPTIMAL`.

5. **SAVINGS arithmetic check.** `CURRENT_MONTHLY - PROJECTED_MONTHLY`
   MUST equal `MONTHLY_SAVING`. If the three numbers don't reconcile,
   re-compute before emitting. Round to 2 decimal places.

6. **Archive-tier minimum-duration disclosure.** Any recommendation
   configuring Archive Access or Deep Archive Access MUST include the
   90/180-day minimum-duration caveat and the retrieval-fee range in
   `CAVEATS`. A bare `Tierings` rule without these caveats is non-
   compliant.

7. **Filter-prefix reality check.** Before emitting `OPPORTUNITY_FOUND`
   on a configuration with a filter, verify the proposed filter prefix
   matches actual key prefixes in Storage Lens or `list-objects-v2
   --prefix`. A rule with a non-matching prefix is silently a no-op.

These rules are evaluated AFTER Step 5 aggregation but BEFORE emitting
the output block. If any rule fails, re-run the relevant step.

## Anti-Patterns — NEVER (top 5)

These are the five highest-impact mistakes. Each one materially
misleads the operator or produces a non-functional configuration.

1. **NEVER recommend Intelligent-Tiering on a bucket of small objects
   (< 128 KB) without surfacing the monitoring fee.** At $0.0025/1,000
   objects, a bucket of 10M small JSON files costs $25/month in
   monitoring alone — often more than the transition saving. The
   Infrequent tier's 128 KB minimum billable size means small objects
   do not actually save on tiering. Always run Step 2 (monitoring-fee
   gate) before recommending.

2. **NEVER conflate Intelligent-Tiering with S3 Lifecycle.** They are
   separate systems. Intelligent-Tiering uses `put-bucket-intelligent-
   tiering-configuration`; lifecycle uses
   `put-bucket-lifecycle-configuration`. They can coexist on the same
   bucket but should NOT target the same prefix — double-tiering
   produces unpredictable results. Pick one system per prefix.

3. **NEVER propose Intelligent-Tiering on a directory bucket (S3
   Express One Zone, name suffix `--x-s3`).** Directory buckets do not
   support Intelligent-Tiering, lifecycle, or Glacier tiers. Surface
   the $0.16/GB cost as a finding; the verdict for a directory bucket
   is ALREADY_OPTIMAL for latency-critical ML/AI workloads.

4. **NEVER assume the default archive-tier timing (90/180 days) is a
   minimum.** It is configurable. For known-cold data, shorter windows
   (down to the lower bound) capture savings faster. Always evaluate
   whether the defaults match the observed access pattern before
   declaring ALREADY_OPTIMAL.

5. **NEVER auto-apply `put-bucket-intelligent-tiering-configuration`
   without the CONFIRM gate.** A wrong filter scope can mass-tier
   objects, and the monitoring fee applies immediately to every object
   in scope. Always emit `CONFIRM: About to <action>...` and wait for
   explicit operator approval.

## Edge-case handling

These are buckets where the standard pattern produces wrong
recommendations without explicit handling:

| Pattern | Detection | Fix |
|---|---|---|
| **Small objects + frequent access** (50M objects < 128 KB, daily access) | `ObjectSizeDistribution` from Storage Lens: `<128KB` > 20% by count AND access > 1x/day | Verdict `ALREADY_OPTIMAL` (Standard cheapest). Monitoring fee would be pure overhead; Infrequent 128 KB minimum prevents saving. Surface small-object fee aggregation as a cost-allocation finding only. |
| **Compliance archive with periodic retrieval** (Object Lock COMPLIANCE, quarterly audit) | `get-object-lock-configuration`: COMPLIANCE mode with known retrieval cadence | Restrict to Frequent Access only. Verdict `ALREADY_OPTIMAL` for Intelligent-Tiering (archive tiers defeat retrieval SLA). A fixed lifecycle to Glacier IR for ms-retrieve is the correct pick. |
| **Mixed hot + cold prefix** (`app/hot/` daily, `app/archive/` yearly) | Storage Lens shows divergent access by prefix | Scope the configuration with `Filter: {Prefix: "app/archive/"}` to limit the monitoring fee to the cold prefix. Leaves the hot prefix on Standard (no wasted monitoring). |

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`put-bucket-intelligent-tiering-configuration`,
  `delete-bucket-intelligent-tiering-configuration`, `create-job` for
  Batch Operations), emit: `CONFIRM: About to <action> on bucket <name>
  in account <account> region <region>. This affects <consequence>.
  Proceed? (yes/no)`. Do NOT execute until the operator confirms.

- **Capture current state for rollback.** Before applying:
  `aws s3api list-bucket-intelligent-tiering-configurations --bucket
  <name> --output json > /tmp/<name>-it-config-backup-$(date +%s).json`.
  The configuration is not versioned; a put replaces it atomically.

- **Verify Object Lock posture before archive-tier recommendations.**
  If the bucket has Object Lock in COMPLIANCE mode with a retrieval SLA,
  do not recommend archive tiers.

- **Verify the filter prefix matches the actual key layout.** A wrong
  prefix is silently a no-op (or worse, scopes the configuration away
  from the intended objects).

- **Batch Operations IAM check.** `s3control create-job` requires a
  role with appropriate S3 permissions. Verify the role exists before
  recommending Batch.

## Rollback procedure

1. **Restore the prior configuration:**
   ```bash
   aws s3api put-bucket-intelligent-tiering-configuration \
     --bucket <name> --id Config \
     --intelligent-tiering-configuration file://<name>-it-config-backup-<timestamp>.json
   ```
   This stops FUTURE tiering but does not revert objects already moved.

2. **Identify tiered objects** via Storage Lens tier-distribution drift
   or S3 Inventory filtered by storage class.

3. **Restore storage class** via S3 Batch Operations with `S3CopyObject`
   and `TargetStorageClass: STANDARD`. Include copy-request charges in
   the rollback cost estimate.

## Error handling — CLI and data-source failures

| Failure mode | Detection | Handling |
|---|---|---|
| `list-bucket-intelligent-tiering-configurations` returns empty | `IntelligentTieringConfigurationList: []` | Normal — no configuration present. Proceed with recommendation. |
| `get-storage-lens-configuration` returns `NoSuchConfiguration` | API error | Storage Lens not enabled. Fall back to `list-objects-v2` sample; flag recommendation as MEDIUM confidence. |
| `put-bucket-intelligent-tiering-configuration` fails with `MalformedXML` | API error | JSON schema error. Common cause: `Days` < 90 for ARCHIVE_ACCESS or < 180 for DEEP_ARCHIVE_ACCESS. Validate the configuration and retry. |
| `put-bucket-intelligent-tiering-configuration` fails with `AccessDenied` | API error | Caller role lacks `s3:PutIntelligentTieringConfiguration`. Add the permission to the bucket policy or caller IAM. |
| `list-objects-v2` paginating > 100 pages on a large bucket | Pagination count | STOP iterating live. Use S3 Inventory or Storage Lens aggregate metrics. |
| Storage Lens shows 0 access data on a known-active bucket | Cross-check with CloudTrail `GetObject` events | Storage Lens may be misconfigured. Trust CloudTrail for access-pattern evidence. |

## Cross-region cost variance detail

S3 pricing varies by region. Always re-state the regional rate in the
SAVINGS block when the bucket is not in us-east-1. Monitoring fee is
flat ($0.0025/1K) across all regions.

| Region | Standard / IT-Frequent $/GB-mo | Notes |
|---|---|---|
| us-east-1, us-west-2 | 0.023 | Baseline |
| eu-west-1 (Ireland) | 0.024 | ~4% premium |
| ap-southeast-1 (Singapore) | 0.025 | ~9% premium |
| sa-east-1 (Sao Paulo) | 0.0309 | ~35% premium |

**Decision impact:** in high-premium regions, the gap between Frequent
and Archive tiers is wider, so Intelligent-Tiering captures MORE savings.
Be more aggressive on archive-tier timing in high-premium regions.

## Recent AWS features (2024-2026)

- **S3 Intelligent-Tiering small object fee aggregation (2025-2026):**
  For buckets with very large counts of small objects, AWS aggregates
  the per-object monitoring and small-object fees into bulk billing
  lines for cost-allocation visibility. This does NOT remove the
  monitoring fee — it changes how the fee is presented. The gate (Step 2)
  still applies.

- **Configurable Archive tier timing (2024-2025):** Archive Access
  (default 90 days) and Deep Archive Access (default 180 days) are now
  configurable via `Tierings[].Days`. Shorter windows capture savings
  faster on known-cold data.

- **Intelligent-Tiering filter scopes (2024):** Configurations support
  `Filter: {Prefix: "...", Tag: {...}}` to scope Intelligent-Tiering
  to specific object cohorts. Use to limit the monitoring fee to cold
  prefixes only.

- **S3 Storage Lens expanded (2024-2026):** 29+ metrics including
  object-size distribution, tier distribution, access-pattern trend.
  Always pull Storage Lens before recommending Intelligent-Tiering.

- **S3 Batch Operations expanded (2024-2025):** Supports `S3CopyObject`
  with `TargetStorageClass: INTELLIGENT_TIERING` for one-time backfill.

- **S3 Express One Zone directory buckets (2023-2025):** Single-AZ
  directory buckets with ms-latency. Do NOT support Intelligent-Tiering.
  Verdict: ALREADY_OPTIMAL for ML/AI workloads.

- **S3 Tables (managed Apache Iceberg, 2025):** Tables manage their
  own lifecycle; do NOT propose Intelligent-Tiering on table-data
  prefixes.

## Domain

AWS CloudOps / S3 Storage Cost Optimisation via Intelligent-Tiering.

## AWS documentation

- **Amazon S3 User Guide** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
- **S3 Intelligent-Tiering** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/intelligent-tiering.html
- **S3 Storage Classes** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html
- **Configuring Intelligent-Tiering** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/intelligent-tiering-overview.html
- **S3 Storage Lens** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage_lens_basics_metrics.html
- **S3 Batch Operations** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops.html
- **AWS CLI: s3api** — https://docs.aws.amazon.com/cli/latest/reference/s3api/
