---
name: s3-storage-class-optimizer
description: 'Optimises S3 storage cost across six dimensions: lifecycle policy configuration (Standard to Standard-IA to Glacier Instant to Glacier Flexible to Glacier Deep Archive transition timing with minimum-days constraints), Intelligent-Tiering activation with Archive Access and Deep Archive Access tiers, Storage Lens analysis for object-age distribution and prefix-level cost allocation, versioning cost impact (noncurrent object churn and delete-marker accumulation), retrieval-pattern matching (Glacier Instant vs Flexible vs Deep Archive trade-offs), and S3 Batch Operations for bulk storage-class migration. Uses S3 Storage Lens, object-level age metrics, and Cost Explorer S3 usage breakdown to project per-TB savings. Emits FURTHER_OPTIMIZATION_AVAILABLE with tier transitions and dollar savings, OPTIMIZED, or ALREADY_OPTIMAL.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline classification works from pasted Storage Lens exports and Cost Explorer data. Live-account optimization uses aws s3api list-buckets, aws s3api get-bucket-lifecycle-configuration, aws s3api get-bucket-versioning, aws s3api get-bucket-intelligent-tiering-configuration, aws s3control get-storage-lens-configuration, aws ce get-cost-and-usage, and aws s3api list-objects-v2 with --query for object-age...
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
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: Optimising S3 storage cost, deploying lifecycle policies, evaluating Intelligent-Tiering activation, analysing Storage Lens object-age distribution, diagnosing versioning bloat, choosing Glacier Instant vs Flexible vs Deep Archive, planning S3 Batch Operations for class migration, or running a storage FinOps review.
  when_not_to_use: S3 security or access-control auditing (use the S3 auditor skill), S3 performance optimisation for latency-sensitive workloads (Transfer Acceleration, CloudFront — use the CDN skills), or EBS volume cost optimisation (use ebs-volume-optimizer). This skill focuses on storage-class cost reduction, not access governance.
  activation_triggers: optimise S3 storage cost, S3 lifecycle policy, S3 Intelligent-Tiering, S3 Glacier migration, S3 Deep Archive, S3 Storage Lens analysis, S3 versioning cost, S3 noncurrent objects, S3 Batch Operations, S3 cost per TB, S3 Standard-IA transition, S3 delete marker cleanup, S3 prefix cost allocation, S3 FinOps review, reduce S3 bill, S3 storage class review
  invocation_schema: 'Input: either (a) a bucket identifier + live-account context, (b) a Storage Lens export or Cost Explorer S3 usage breakdown, OR (c) bucket configuration metadata (lifecycle config, versioning status, Intelligent-Tiering config) with object-age distribution. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ ESTIMATED_SAVINGS/MIGRATION_STEPS block per bucket, where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE, ALREADY_OPTIMAL.'
  invocation_example: "# Minimal valid input (offline classification):\nBucketName: data-lake-raw-prod\nRegion: us-east-1\nStorage (total): 45 TB\nStorage class distribution:\n  - Standard: 32 TB (71%)\n  - Standard-IA: 8 TB (18%)\n  - Glacier Instant Retrieval: 0 TB\n  - Glacier Flexible Retrieval: 3 TB (7%)\n  - Glacier Deep Archive: 2 TB (4%)\nVersioning: Enabled\nLifecycle policy: none\nIntelligent-Tiering: not configured\nStorage Lens (last 30 days):\n  - Objects aged 0-30 days: 12 TB\n  - Objects aged 31-90 days: 9 TB\n  - Objects aged 91-180 days: 6 TB\n  - Objects aged 181-365 days: 5 TB\n  - Objects aged >365 days: 13 TB\nRetrieval frequency: <1% of objects accessed after 90 days\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: S3, storage class, lifecycle policy, Intelligent-Tiering, Glacier, Deep Archive, Standard-IA, Glacier Instant Retrieval, Storage Lens, object age, versioning cost, noncurrent objects, S3 Batch Operations, cost optimization, FinOps, prefix grouping, MFA delete, delete markers, storage cost, per TB
  tags: s3, storage, cost-optimization, finops, lifecycle, intelligent-tiering, glacier
---

# S3 Storage Class Optimizer

## What this skill does

Translates an S3 bucket's storage-class distribution and object-age
profile into a concrete cost-optimization recommendation with a
dollar-denominated per-TB savings estimate. The verdict is the
highest-leverage action across six dimensions — lifecycle policy,
Intelligent-Tiering, Storage Lens analysis, versioning cost,
retrieval-pattern matching, and Batch Operations migration — applied
in priority order. Always pairs the recommendation with exact CLI
commands.

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Four headline rules and the cost formula | First read |
| Mindset | Why lifecycle + Intelligent-Tiering is the #1 lever | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying a bucket |
| Pre-flight data gate | Storage Lens, Cost Explorer, lifecycle config | Before any recommendation |
| Step 0 non-obvious behaviours | Min-days constraints, retrieval surprises | Edge cases |
| Step 1 Lifecycle policies | Standard to IA to Glacier to Deep Archive | The headline savings dimension |
| Step 2 Intelligent-Tiering | Archive Access, Deep Archive Access tiers | Unknown access patterns |
| Step 3 Storage Lens analysis | Object-age distribution, prefix grouping | Data-driven tiering |
| Step 4 Versioning cost impact | Noncurrent objects, delete markers | Versioned buckets |
| Step 5 Retrieval-pattern matching | Glacier Instant vs Flexible vs Deep Archive | Archive strategy |
| Step 6 S3 Batch Operations | Bulk class migration | Implementing the change |
| Step 7 Impact estimation | Per-TB cost formula and worked math | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | CONFIRM gate, MFA delete, rollback | Before any apply CLI |

## Quick start

- **Lifecycle is the #1 lever.** S3 Standard costs $23/TB-month; Deep
  Archive costs $0.99/TB-month — a 23x difference. If >365-day-old
  objects are sitting in Standard with <1% retrieval, lifecycle them
  to Deep Archive immediately.
- **Cost formula (memorise this):**
  `monthly_cost = storage_TB × $/TB-month`
  The savings from a tier transition:
  `savings = affected_TB × (old_rate − new_rate)`
- **Intelligent-Tiering eliminates guessing.** For buckets with
  unpredictable access patterns, enable Intelligent-Tiering ($2.50/TB-
  month monitoring fee) instead of hand-crafting lifecycle rules. It
  auto-moves objects to Archive Access after 90 days and Deep Archive
  Access after 180 days with zero retrieval surprises.
- **Retrieval cost is the gotcha.** Glacier Flexible Retrieval charges
  $0.03/GB for standard retrieval (1-5 min) and $0.10/GB for bulk (5-12
  h). Deep Archive charges $0.02/GB for standard (12h) and $0.0025/GB
  for bulk (48h). A single 1 TB bulk retrieval from Deep Archive costs
  $2.50 — cheap. But a 1 TB expedited retrieval from Flexible costs
  $100. Always surface retrieval cost risk before recommending archive.

## Mindset

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md) — the four principles behind every recommendation.


## Quick reference — verdict thresholds

| Observation (30-day Storage Lens window) | Verdict | Recommendation |
|---|---|---|
| No lifecycle policy AND objects >30 days in Standard > 20% of bucket | **FURTHER_OPTIMIZATION_AVAILABLE** (lifecycle) | Step 1 — deploy lifecycle: Standard→IA at 30d,→Glacier Instant at 90d,→Deep Archive at 180d |
| No Intelligent-Tiering AND access pattern is unpredictable (mixed ages with sporadic reads) | **FURTHER_OPTIMIZATION_AVAILABLE** (Intelligent-Tiering) | Step 2 — enable Intelligent-Tiering with Archive Access at 90d, Deep Archive Access at 180d |
| Versioning Enabled AND no noncurrent-version lifecycle AND noncurrent versions > 10% of bucket size | **FURTHER_OPTIMIZATION_AVAILABLE** (versioning) | Step 4 — add noncurrent-version transitions + expirations |
| Objects in Glacier Flexible/Deep Archive AND retrieval rate > 10% of archive per month | **FURTHER_OPTIMIZATION_AVAILABLE** (retrieval mismatch) | Step 5 — evaluate Glacier Instant Retrieval or move back to Standard-IA |
| Objects in Standard-IA accessed > 2x/month | **FURTHER_OPTIMIZATION_AVAILABLE** (IA mismatch) | Step 5 — move accessed objects back to Standard (IA retrieval fee exceeds storage delta) |
| Lifecycle policy deployed AND Intelligent-Tiering on mixed-pattern prefixes AND versioning rules active AND no retrieval mismatch | **ALREADY_OPTIMAL** | None — continue monitoring |
| Storage Lens data absent or Cost Explorer window < 30 days | **NEED_MORE_INFO** | Pull 30-day Storage Lens + CE data, re-evaluate |
| Lifecycle policy deployed AND verified via post-change Storage Lens this session | **OPTIMIZED** | Emit post-state verification |

## Pre-flight: data gate (run before any optimization decision)

Optimization decisions require object-age distribution and cost
breakdown. Pull these before any recommendation. Full CLI sequences
are in `references/s3-pricing-and-storage-classes.md`.

→ Data-source CLI listing moved to [references/diagnostic-commands.md](references/diagnostic-commands.md); the short-circuit table below is the gate itself.


### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| Storage Lens not enabled | **NEED_MORE_INFO**. Enable S3 Storage Lens (free tier) or fall back to Cost Explorer + object sampling. |
| Cost Explorer `GetCostAndUsage` returns empty for S3 | Bucket may be in free tier or CE not enabled. Proceed with Storage Lens only; MEDIUM confidence. |
| Bucket empty (`ObjectCount = 0`) | **ALREADY_OPTIMAL** with note "empty bucket." |
| Object-age data < 30 days | **NEED_MORE_INFO**. Minimum 30-day window; 90 days preferred for lifecycle timing. |
| Lifecycle config is `NoSuchLifecycleConfiguration` | No policy — proceed to Step 1. This is the most common finding. |
| Versioning `Status != Enabled` AND noncurrent versions present | Impossible state; verify with `list-object-versions`. |
| Bucket has Object Lock enabled | Lifecycle expiration is blocked for locked objects. Factor into recommendations. |

When Storage Lens and Cost Explorer disagree, Storage Lens wins for
object-age and class distribution; Cost Explorer wins for dollar
amounts. Reconcile by cross-referencing class distribution with CE
usage types.

## Configuration dependency graph

→ Dependency-graph diagram moved to [references/advanced-patterns.md](references/advanced-patterns.md); the dependency rule below is the gate.


**Dependency rule:** Never recommend a lifecycle transition without
first verifying the retrieval pattern (Step 5 gate). A bucket with
high archive retrieval should NOT be pushed deeper into archive tiers.

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md) — non-obvious behaviours deep dive.


### Step 1: Lifecycle policy configuration (the #1 lever)

Lifecycle policies automate object transitions between storage classes
based on age. This is the highest-impact S3 cost optimization.

→ Lifecycle JSON template and minimum-days matrix moved to [references/advanced-patterns.md](references/advanced-patterns.md); the decision gate below carries every branch.


**Decision gate:**

| Object-age profile (from Storage Lens) | Lifecycle recommendation |
|---|---|
| >20% of objects aged >30 days still in Standard | Transition to Standard-IA at 30d |
| >15% of objects aged >90 days with infrequent access | Transition to Glacier IR at 90d |
| >10% of objects aged >180 days with <1% retrieval | Transition to Deep Archive at 180d |
| Objects aged >2555 days (7+ years) | Expiration if compliance permits |

→ Savings formulas moved to [references/advanced-patterns.md](references/advanced-patterns.md).


### Step 2: Intelligent-Tiering configuration

Intelligent-Tiering automatically moves objects between access tiers
based on usage patterns. It eliminates the need to predict access
frequency.

**When Intelligent-Tiering wins over lifecycle:**

| Scenario | Why Intelligent-Tiering |
|---|---|
| Access pattern is unpredictable (user uploads, shared docs) | Lifecycle can't adapt; IT monitors per-object |
| Mixed-age objects with sporadic reads | Lifecycle would misclassify active old objects |
| Small team / no bandwidth to tune lifecycle rules | IT is set-and-forget |
| Bucket has diverse prefixes with different patterns | IT operates per-object, not per-prefix |

**When lifecycle wins over Intelligent-Tiering:**

| Scenario | Why lifecycle |
|---|---|
| Predictable write-once-read-never (logs, backups) | No monitoring fee ($2.50/TB-mo saved) |
| Bucket < 1 TB | Monitoring fee exceeds savings |
| Regulatory retention with known expiry | Explicit expiration rule required |

→ Intelligent-Tiering CLI, tier configuration, and the 50 TB cost comparison moved to [references/advanced-patterns.md](references/advanced-patterns.md).


### Step 3: Storage Lens analysis and prefix-based grouping

Storage Lens provides bucket-level and prefix-level object-age
distribution, storage-class breakdown, and activity metrics. Use it
to drive data-driven tiering decisions.

**Key Storage Lens metrics for optimization:**

| Metric | What it reveals | Optimization signal |
|---|---|---|
| ObjectCount by age band | How many objects are old | Age drives lifecycle timing |
| StorageBytes by age band | How much storage is old | TB drives savings magnitude |
| NoncurrentVersionStorageBytes | Versioning bloat | If > 10% of current, add noncurrent rules |
| GetObject count by age | Which objects are still accessed | Old objects with high GETs should NOT be archived |
| DeleteMarkerCount | Delete marker accumulation | Schedule cleanup if > 100K |
| IncompleteMultipartUploadStorageBytes | Aborted multipart uploads | Add abort rule to reclaim storage |
| BytesDownloaded by class | Retrieval volume by class | Glacier/DA downloads reveal retrieval cost risk |

→ Prefix-grouping example moved to [references/advanced-patterns.md](references/advanced-patterns.md).


### Step 4: Versioning cost impact

Versioning retains every prior object version. Without lifecycle rules
on noncurrent versions, storage grows unbounded.

**Detection:**
```
noncurrent_pct = NoncurrentVersionStorageBytes /
                 (NoncurrentVersionStorageBytes + CurrentVersionStorageBytes)

If noncurrent_pct > 10% → versioning bloat finding
```

→ Noncurrent-version lifecycle template moved to [references/advanced-patterns.md](references/advanced-patterns.md).


Keeps the 3 most recent noncurrent versions; transitions older ones to
cheaper tiers; expires after 365 days.

→ Delete-marker cleanup command moved to [references/advanced-patterns.md](references/advanced-patterns.md).


### Step 5: Retrieval-pattern matching

Choosing the right archive tier depends on retrieval frequency and
latency tolerance.

→ Archive tier comparison table moved to [references/s3-pricing-and-storage-classes.md](references/s3-pricing-and-storage-classes.md); the detection gate below carries the decisions.


→ Retrieval cost surprise math moved to [references/advanced-patterns.md](references/advanced-patterns.md).


**Retrieval-mismatch detection gate:**
| Observed monthly retrieval rate | Recommendation |
|---|---|
| <1% of archive retrieved | Deep Archive is appropriate |
| 1-5% of archive retrieved | Glacier Flexible is appropriate |
| 5-10% of archive retrieved | Glacier IR is appropriate |
| >10% of archive retrieved | Move back to Standard-IA or Standard (retrieval cost exceeds savings) |

### Step 6: S3 Batch Operations for bulk class migration

Lifecycle policies only affect objects prospectively. To migrate
existing objects to a cheaper tier immediately, use S3 Batch Operations.

→ Batch Operations COPY commands moved to [references/advanced-patterns.md](references/advanced-patterns.md).


**Cost:** $0.25 per million objects. For 10M objects: $2.50 — negligible
vs monthly savings. Use Batch Ops for immediate migration of existing
objects; use lifecycle for future objects.

### Step 7: Impact estimation

Compute the monthly savings for each recommendation:

→ Impact-estimation formulas moved to [references/advanced-patterns.md](references/advanced-patterns.md).


Always state assumptions: TB per class, transition timing, retrieval
rate, pricing region, Intelligent-Tiering monitoring fee.

### Step 8: Final verdict

- Any dimension recommends a change → **FURTHER_OPTIMIZATION_AVAILABLE**.
- All dimensions pass (lifecycle deployed, versioning rules active,
  no retrieval mismatch, no IA mismatch) → **ALREADY_OPTIMAL**.
- Change applied and verified this session → **OPTIMIZED**.
- Data insufficient (Storage Lens absent, window < 30 days) →
  **NEED_MORE_INFO**.

Never emit `FURTHER_OPTIMIZATION_AVAILABLE` without first discharging
every `NEED_MORE_INFO`/`BLOCKED` gate.

## Output format

```text
TARGET: <bucket-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <TB by class>, <versioning status>, <lifecycle status>, <IT status>
  Proposed: <TB by class after changes>, <new lifecycle rules>, <IT config>
  Dimensions changed: <lifecycle | intelligent-tiering | versioning | retrieval | batch-migration>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
  Assumptions: <list (TB per class, retrieval rate, pricing region, etc.)>
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <bucket-name> in <region>.
  Proceed? (yes/no)"
```

Full worked examples are in `references/worked-examples.md`.

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
misclassification or an arithmetic contradiction that breaks downstream
FinOps automation. Self-check EVERY emitted block against these rules
before returning the response.

### Required output structure

Every response MUST be a single block using these literal labels, in
this order. Do NOT substitute markdown headings, camelCase, or bold
variants.

```text
TARGET: <bucket-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <TB by class>, <versioning>, <lifecycle>, <IT config>
  Proposed: <TB by class>, <new lifecycle>, <new IT config>
  Dimensions changed: <lifecycle | intelligent-tiering | versioning | retrieval | batch-migration>
  Dimensions checked: <list ALL five, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>    ← MUST show per-class subtotals
  Projected monthly: $<amount>
  Monthly saving: $<amount>     ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>      ← MUST equal Monthly × 12
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: <confirmation prompt text>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` with
   `Monthly saving: $0.00`.** If every dimension nets zero cost delta,
   the verdict MUST be `ALREADY_OPTIMAL`.

2. **NEVER show savings math that does not balance.**
   `Current monthly − Projected monthly` MUST equal `Monthly saving`,
   rounded to 2 decimal places.

3. **NEVER emit scratch lines** ("WAIT — recompute", "Hmm, let me redo",
   "corrected:") in the output. Finalize the math before emitting.

4. **NEVER recommend a lifecycle transition without citing Storage
   Lens or object-age evidence.** The REASON MUST name the evidence
   source (Storage Lens age band, CE usage type, object sampling).

5. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all five dimensions, each marked
   ✓ (no finding) or → (finding).

6. **NEVER recommend Deep Archive without stating the retrieval cost
   risk.** The REASON or ASSUMPTIONS MUST include retrieval-rate
   context and minimum 180-day storage duration.

7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE

Every field below is internally consistent. Copy this shape exactly.

```text
TARGET: data-lake-raw-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: 45 TB bucket with 32 TB (71%) in Standard despite 13 TB being
  >365 days old (Storage Lens confirms <1% retrieval after 90 days).
  No lifecycle policy. Versioning enabled but no noncurrent-version
  rules, contributing 4 TB of bloat. Deploying 4-tier lifecycle +
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

**Self-check before emit:**
- [ ] `Current monthly − Projected monthly == Monthly saving` (2 decimals)?
- [ ] `Monthly saving × 12 == Annual saving`?
- [ ] All five dimensions listed in `Dimensions checked`?
- [ ] Every `→` dimension has a corresponding MIGRATION_STEPS entry?
- [ ] Retrieval-cost risk stated if recommending any archive tier?
- [ ] No scratch/recompute text in the block?

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has a concrete, savings-bearing recommendation. |
| `OPTIMIZED` | A change was applied and verified this session; Storage Lens confirms the new class distribution. |
| `ALREADY_OPTIMAL` | All dimensions pass (lifecycle deployed, versioning rules active, no retrieval mismatch, no IA mismatch). |
| `NEED_MORE_INFO` | Data gate failed: Storage Lens absent, window < 30 days, or CE data unavailable. |
| `BLOCKED` | Hard precondition prevents evaluation: Object Lock active, bucket in another account. |

**Zero-savings rule:** If MONTHLY_SAVING == $0.00 for every dimension,
verdict MUST be `ALREADY_OPTIMAL`, never `FURTHER_OPTIMIZATION_AVAILABLE`.

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend Deep Archive without stating the 180-day minimum
   storage duration and the retrieval cost.** An object deleted from
   Deep Archive before 180 days incurs a prorated charge. A surprise
   retrieval can cost more than the storage saved.

2. **NEVER recommend Standard-IA for objects accessed more than twice
   per month.** IA charges $0.01/GB retrieval. At 2 accesses/month of
   a 1 MB object: $0.00002 storage saving vs $0.00002 retrieval cost
   — breakeven. Above 2 accesses, Standard is cheaper.

3. **NEVER enable Intelligent-Tiering on buckets < 1 TB without
   warning that the monitoring fee may exceed savings.** The $2.50/TB-
   month fee on 0.5 TB is $1.25/month — if the savings from auto-
   tiering are < $1.25, IT loses money.

4. **NEVER deploy a lifecycle policy with a transition that violates
   the minimum-days constraint.** S3 silently ignores transitions that
   don't meet the minimum age. The policy will appear active but no
   objects will transition.

5. **NEVER recommend One Zone-IA for compliance or irreplaceable data.**
   One Zone-IA stores data in a single AZ. An AZ failure means data
   loss. Use only for reproducible or transient data.

Extended anti-patterns in `references/s3-pricing-and-storage-classes.md`.

## Pre-flight safety checks (run before any remediation CLI)

→ Pre-flight safety checklist moved to [references/diagnostic-commands.md](references/diagnostic-commands.md).


## Recent AWS features (2024-2026)

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md) — recent AWS features (2024-2026).


## References

- `references/s3-pricing-and-storage-classes.md` — pricing tables,
  minimum-days matrix, Intelligent-Tiering configuration, Batch
  Operations guide, extended NEVER list, regional pricing multipliers.
- `references/worked-examples.md` — full worked examples (lifecycle
  deployment, Intelligent-Tiering activation, versioning bloat, already-
  optimal, NEED_MORE_INFO, end-to-end walkthrough).

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — mindset deep dive, dependency-graph diagram, Step 0 gotchas, step templates/formulas, recent AWS features.
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — data-gate CLI sources and pre-remediation safety checks.
- [references/s3-pricing-and-storage-classes.md](references/s3-pricing-and-storage-classes.md) — pre-existing; pricing tables and minimum-days matrix; extended with the archive tier comparison.
- [references/worked-examples.md](references/worked-examples.md) — pre-existing; full worked examples and the end-to-end walkthrough.

## Domain

AWS CloudOps / S3 Storage Cost Optimization & FinOps.

## AWS documentation

- **Amazon S3 Developer Guide** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
- **Amazon S3 pricing** — https://aws.amazon.com/s3/pricing/
- **S3 lifecycle configuration** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html
- **S3 Intelligent-Tiering** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html#sc-dynamic-data-access
- **S3 Storage Lens** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage_lens_basics_metrics.html
- **S3 Batch Operations** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops.html
- **S3 versioning** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html
- **S3 Glacier retrieval options** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/archived-objects.html
- **AWS CLI S3 reference** — https://docs.aws.amazon.com/cli/latest/reference/s3api/
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
