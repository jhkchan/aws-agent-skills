---
name: s3-lifecycle-optimizer
description: Optimises S3 storage cost through lifecycle-policy design, storage-class selection, and access-pattern analysis. Invents the right transition and expiration rules per workload archetype (logs, compliance archive, application data, versioned buckets, multipart-upload leaks), projects monthly savings net of minimum-duration and retrieval charges, and emits a deterministic verdict (OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL) per bucket with the exact put-bucket-lifecycle-configuration payload and estimated dollar impact. Use when reviewing S3 spend, designing lifecycle policies, choosing between Standard-IA / One-Zone-IA / Intelligent-Tiering / Glacier tiers, pruning noncurrent versions, aborting stale multipart uploads, or projecting savings from a storage-class migration.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline configuration classification. Live-account audits use aws s3api list-buckets, aws s3api get-bucket-lifecycle-configuration, aws s3api list-objects-v2 (with --page-size for inventory), aws s3api list-multipart-uploads, aws s3api get-bucket-versioning, and aws s3control get-storage-lens-configuration (AWS CLI v2, SSO or key-based credentials). Pricing is us-east-1 published rates...
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  task_type: optimize
  skill_class: capability
  verdict_shape: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
  when_to_use: Reviewing S3 spend, designing or auditing lifecycle policies, selecting storage classes for infrequently accessed data, projecting savings from Standard -> Standard-IA / Intelligent-Tiering / Glacier transitions, pruning noncurrent versions on versioned buckets, aborting stale multipart uploads, or hardening compliance archives with Object Lock.
  activation_triggers: optimise S3 storage cost, design S3 lifecycle policy, S3 storage class analysis, move S3 data to Glacier, S3 Intelligent-Tiering vs Standard-IA, prune noncurrent S3 versions, abort stale S3 multipart uploads, S3 Object Lock retention, S3 lifecycle transition rules, S3 cost optimization review, Glacier Deep Archive lifecycle, S3 Batch Operations storage class
  invocation_schema: 'Input: either (a) a bucket configuration (lifecycle configuration JSON, versioning status, Storage Lens metrics summary, optional object-age histogram), OR (b) a bucket name for live-account optimisation. Output: deterministic BUCKET/VERDICT/REASON/RECOMMENDATION/SAVINGS/IMPLEMENTATION block per bucket, where VERDICT is one of OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: S3, lifecycle policy, storage class, Standard-IA, One-Zone-IA, Intelligent-Tiering, Glacier Instant Retrieval, Glacier Flexible Retrieval, Glacier Deep Archive, S3 Express One Zone, directory bucket, noncurrent version, multipart upload, S3 Storage Lens, S3 Object Lock, S3 Batch Operations, S3 Tables, put-bucket-lifecycle-configuration, storage cost optimization
  tags: s3, storage, cost-optimization, lifecycle, storage-class, glacier, intelligent-tiering, object-lock, finops
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


→ Cost baseline table moved to [references/storage-class-pricing-matrix.md](references/storage-class-pricing-matrix.md) — load it before producing dollar estimates.

## Decision tree for storage class selection

Use this tree when Step 3 (storage-class transition design) needs a
definitive pick. Read top-to-bottom; **first match wins**. Always pair the
pick with the access-pattern evidence from Storage Lens (Step 0) — a
tree verdict without observed access data is a guess.

```
START: Is the object accessed daily or weekly?
├── YES → Standard ($0.023/GB-mo)
│         No transition. Standard is cheapest for frequent access.
└── NO → Is it accessed roughly monthly (1-3 times/month)?
    ├── YES → Is avg object size >= 128 KB?
    │   ├── YES → Standard-IA ($0.0125/GB, 30-day minimum, $0.01/GB retrieval)
    │   │         Caveat: 30-day minimum-duration charge on early delete.
    │   └── NO  → Standard (IA 128 KB minimum billable size makes IA costlier
    │             for small objects — see Edge-case handling).
    └── NO → Is it accessed quarterly (every ~90 days)?
        ├── YES → Glacier Instant Retrieval ($0.004/GB, 90-day min, ms retrieve)
        │         Caveat: $0.03/GB retrieval + $0.0005/req; 90-day minimum.
        └── NO → Is it accessed yearly or less?
            ├── YES → Is 12-hour retrieval latency acceptable?
            │   ├── YES → Glacier Deep Archive ($0.00099/GB, 180-day min)
            │   │         Cheapest tier. Retrieval $0.02-10/GB, 12h Std / 48h Bulk.
            │   └── NO  → Glacier Flexible Retrieval ($0.0036/GB, 90-day min)
            │             Hours retrieval; $0.0025-10/GB tiered (Exp/Std/Bulk).
            └── UNKNOWN (no access data)
                → Intelligent-Tiering ($0.023 entry, $0.0025/1K monitor)
                  ONLY if avg object size >= 128 KB AND access pattern is
                  genuinely mixed. Otherwise Standard is cheaper
                  (Step 3 Archetype C threshold check).
```

**Special-case branches (override the main tree):**

- **Versioned bucket + noncurrent versions:** always add
  `NoncurrentVersionExpiration` regardless of the current-object pick. The
  tree answers the *current* tier; noncurrent cleanup is a parallel dimension
  (Step 1).
- **Object Lock COMPLIANCE mode:** the retention period overrides any
  `ExpirationInDays`. Run the tree on the post-retention state, not on
  creation date.
- **Directory bucket (S3 Express One Zone, name suffix `--x-s3`):** lifecycle
  and Glacier tiers are NOT supported. Verdict is ALREADY_OPTIMAL for ML/AI
  latency-critical workloads. Do not run the tree.
- **S3 Tables (Apache Iceberg) data:** table lifecycle is managed via table
  APIs, not S3 lifecycle. Surface as a finding only; do not run the tree.
- **Cross-Region Replication destination:** destination defaults to Standard
  unless the replication rule sets `StorageClass`. Run the tree independently
  on source AND destination — lifecycle does not propagate across the
  replication boundary.
- **Re-creatable, single-AZ-tolerant data (e.g., regenerated backups):**
  One-Zone-IA ($0.01/GB) is 20% cheaper than Standard-IA but loses the
  multi-AZ durability guarantee. Only use when data loss in one AZ is
  recoverable from source.

## Mindset

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md) — the four S3 realities behind the verdict rule.
## Pre-flight: bucket metadata gate

Run before classification. Misclassifying these produces false positives.


→ Pagination guidance and the 6-command live-account pre-flight listing moved to [references/diagnostic-commands.md](references/diagnostic-commands.md); the attribute table below is the gate itself.

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

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md) — non-obvious lifecycle behaviors deep dive.
### Step 1: Noncurrent version cleanup (versioned buckets)

If the bucket has versioning `Enabled` or `Suspended`:

→ Rule templates and savings detail moved to [references/advanced-patterns.md](references/advanced-patterns.md).

If versioning is `Enabled` and no `NoncurrentVersionExpiration` rule exists:
**OPPORTUNITY_FOUND** on this dimension.

### Step 2: Multipart upload cleanup

- **Pull pending multipart uploads:** `aws s3api list-multipart-uploads --bucket <name>`.
  Any upload with `Initiated` > 7 days ago is a leak.

→ Abort-rule JSON moved to [references/advanced-patterns.md](references/advanced-patterns.md).

If any multipart upload is >7 days old OR no abort rule exists:
**OPPORTUNITY_FOUND** on this dimension.

### Step 3: Storage-class transition design (current objects)

Apply per workload archetype. Pick the pattern by access pattern, not by
data type.


→ The four archetype JSON templates moved to [references/advanced-patterns.md](references/advanced-patterns.md); the pattern lines below carry every branch decision.
**Archetype A — Logs and temporary data (high write, low read after 30 days):**
Pattern: Standard -> 30d IA -> 90d Glacier IR -> 180d Glacier -> 365d Expire.

**Archetype B — Compliance archives (write-once, read-rarely, 7-year retention):**
Pattern: Standard -> 90d Deep Archive -> Expire at retention horizon (e.g., 2555 days for 7 years).

**Archetype C — Application data with unknown / mixed access patterns:**
Pattern: Standard -> Intelligent-Tiering (let AWS manage transitions).
**Threshold check:** only recommend Intelligent-Tiering when average object
size > 128 KB AND access pattern is genuinely mixed. For small objects, the
$0.0025/1,000 monitoring fee exceeds the saving.

**Archetype D — Backup / DR target (write-nightly, read-never unless disaster):**
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

→ Secondary example moved to [references/worked-examples.md](references/worked-examples.md).
### Worked example — Intelligent-Tiering trap (small objects, proposed plan rejected)

→ Secondary example moved to [references/worked-examples.md](references/worked-examples.md).
## Worked example: end-to-end audit of a 5 TB mixed-workload bucket

→ End-to-end audit walkthrough moved to [references/worked-examples.md](references/worked-examples.md).
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

→ Error-handling deep dive and failure-mode tables moved to [references/error-handling.md](references/error-handling.md).
## Rollback procedure (beyond JSON backup)

→ Moved to [references/error-handling.md](references/error-handling.md).
## Cross-region cost variance detail

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md).
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

## Edge-case handling

→ Edge-case catalog moved to [references/advanced-patterns.md](references/advanced-patterns.md).
## Pre-flight safety checks (run before any remediation CLI)

→ Command listing moved to [references/diagnostic-commands.md](references/diagnostic-commands.md).
## Recent AWS features (2024-2026)

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md).
## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert knowledge, step rule templates (Steps 1-3 JSON), cross-region variance, edge cases, recent AWS features, AWS documentation links.
- [references/worked-examples.md](references/worked-examples.md) — secondary worked examples (already-optimal, IT trap, 5 TB end-to-end audit).
- [references/error-handling.md](references/error-handling.md) — error handling for CLI/data-source failures + rollback procedure.
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight gate commands + pre-remediation safety checks.
- [references/storage-class-pricing-matrix.md](references/storage-class-pricing-matrix.md) — pre-existing; extended with the cost baseline table — load before dollar estimates.

## Domain

AWS CloudOps / S3 Storage Cost Optimisation & Lifecycle Design.

## AWS documentation

→ Link list moved to [references/advanced-patterns.md](references/advanced-patterns.md).
