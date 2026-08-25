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

S3 cost optimization is a data-placement decision, not a throughput
exercise. The goal is the storage-class distribution that minimizes
total cost while preserving retrieval SLAs — not the absolute cheapest
tier regardless of access needs.

Four principles guide every recommendation:

- **Object age is the primary signal.** S3 access patterns are
  overwhelmingly write-once-read-rarely. The age of an object is the
  strongest predictor of future access. Lifecycle policies formalize
  this.
- **Retrieval cost can negate storage savings.** Moving 10 TB to Deep
  Archive saves $220/month in storage but a single full-restore costs
  $25 (bulk). If the business does monthly full restores, the retrieval
  cost ($300/year) may approach the storage savings ($2,640/year) —
  still net positive, but the operator must know.
- **Versioning multiplies cost invisibly.** Every PUT creates a new
  version in a versioned bucket. Without lifecycle rules on noncurrent
  versions, storage grows unbounded. Noncurrent transitions and
  expirations are the fix.
- **Intelligent-Tiering vs lifecycle is not either/or.** Use lifecycle
  for predictable patterns (logs, backups) and Intelligent-Tiering for
  unpredictable ones (user uploads, shared documents). Mixing is valid.

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

**Required data sources** (summarized — see reference for full CLI):
1. Bucket inventory: `aws s3api list-buckets --query 'Buckets[].Name'`
2. Lifecycle config: `aws s3api get-bucket-lifecycle-configuration`
3. Versioning status: `aws s3api get-bucket-versioning`
4. Intelligent-Tiering config: `aws s3api get-bucket-intelligent-tiering-configuration`
5. Storage Lens: `aws s3control get-storage-lens-configuration`
6. Cost Explorer S3 breakdown: `aws ce get-cost-and-usage --service S3`
7. Object-age sampling: `aws s3api list-objects-v2 --query 'Contents[?LastModified<...]'`

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

```
                    ┌──────────────────────┐
                    │  Storage Lens (data) │
                    │  Cost Explorer ($$)  │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
    ┌─────────────────┐ ┌────────────┐ ┌──────────────┐
    │ Lifecycle Policy│ │ Intelligent│ │ Versioning   │
    │ (Step 1)        │ │ -Tiering   │ │ Lifecycle    │
    │                 │ │ (Step 2)   │ │ (Step 4)     │
    └───────┬─────────┘ └─────┬──────┘ └──────┬───────┘
            │                 │               │
            ▼                 ▼               ▼
    ┌──────────────────────────────────────────────┐
    │          Retrieval-Pattern Gate (Step 5)      │
    │  Verify archive retrieval won't exceed budget │
    └──────────────────────┬───────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────┐
    │       S3 Batch Operations (Step 6)            │
    │       Bulk class migration execution          │
    └──────────────────────┬───────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────┐
    │          Impact Estimation (Step 7)           │
    │          Verdict + savings block               │
    └──────────────────────────────────────────────┘
```

**Dependency rule:** Never recommend a lifecycle transition without
first verifying the retrieval pattern (Step 5 gate). A bucket with
high archive retrieval should NOT be pushed deeper into archive tiers.

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

These operational gotchas route a recommendation away from the obvious
choice:

- **Minimum-days constraints are mandatory.** Standard→Standard-IA
  requires objects to be at least 30 days old. Standard-IA→Glacier
  Instant Retrieval requires 30 days in IA first. You cannot create
  a lifecycle rule that transitions to IA at 1 day.
- **Transition costs money.** Each lifecycle transition charges a
  per-request fee ($0.01/1,000 requests for Standard→IA). For buckets
  with millions of tiny objects, the transition request cost can
  exceed the first month's storage savings.
- **Intelligent-Tiering monitoring fee is flat.** $2.50/TB-month
  regardless of how many objects. For buckets < 1 TB, the monitoring
  fee may exceed the savings. Break-even: Intelligent-Tiering pays off
  when the storage savings from auto-tiering exceed $2.50/TB-month.
- **Glacier Instant Retrieval is NOT the same as Standard-IA.** GIR
  costs $4/TB-month (vs IA's $12.50) and provides millisecond access.
  It is ideal for long-lived data accessed once a quarter. Standard-IA
  costs $12.50/TB-month with a per-GB retrieval fee.
- **Deep Archive minimum storage duration is 180 days.** Moving an
  object to Deep Archive and deleting it before 180 days incurs an
  early-delete charge equal to the remaining storage cost.
- **Versioning creates invisible storage.** Every overwrite in a
  versioned bucket retains the prior version. Without noncurrent-
  version lifecycle rules, storage grows linearly with writes.
- **Delete markers count as objects.** In a versioned bucket, a DELETE
  operation creates a delete marker (0-byte). Millions of delete
  markers have negligible storage cost but bloat LIST operations.
- **MFA Delete blocks lifecycle expirations.** If MFA Delete is enabled
  on a versioned bucket, lifecycle expiration of current versions
  requires MFA approval. Plan accordingly.
- **S3 Batch Operations COPY changes class.** To migrate existing
  objects to a new storage class without waiting for lifecycle timing,
  use Batch Operations with a COPY job and `StorageClass` override.
- **One-zone IA is 20% cheaper but has no redundancy.** One Zone-IA
  costs $10.10/TB-month (vs Standard-IA $12.50). Data loss risk if
  the AZ fails. Use only for reproducible data.

### Step 1: Lifecycle policy configuration (the #1 lever)

Lifecycle policies automate object transitions between storage classes
based on age. This is the highest-impact S3 cost optimization.

**Standard lifecycle template (data-lake / log archive pattern):**

```json
{
  "Rules": [
    {
      "ID": "data-lake-tiering",
      "Status": "Enabled",
      "Filter": { "Prefix": "" },
      "Transitions": [
        { "Days": 30,  "StorageClass": "STANDARD_IA" },
        { "Days": 90,  "StorageClass": "GLACIER_IR" },
        { "Days": 180, "StorageClass": "GLACIER" },
        { "Days": 365, "StorageClass": "DEEP_ARCHIVE" }
      ],
      "Expiration": { "Days": 2555 }
    }
  ]
}
```

**Transition timing — minimum-days matrix:**

| Transition | Min days in current tier | Min days in Standard (cumulative) | Storage rate delta |
|---|---|---|---|
| Standard → Standard-IA | 30 | 30 | $23 → $12.50 (saves $10.50/TB-mo) |
| Standard → One Zone-IA | 30 | 30 | $23 → $10.10 (saves $12.90/TB-mo) |
| Standard → Glacier IR | 0 | 0 | $23 → $4.00 (saves $19.00/TB-mo) |
| Standard-IA → Glacier IR | 30 | 60 | $12.50 → $4.00 (saves $8.50/TB-mo) |
| Standard-IA → Glacier Flexible | 30 | 60 | $12.50 → $3.60 (saves $8.90/TB-mo) |
| Glacier IR → Glacier Flexible | 0 | 90 | $4.00 → $3.60 (saves $0.40/TB-mo) |
| Standard → Glacier Flexible | 1 | 1 | $23 → $3.60 (saves $19.40/TB-mo) |
| Standard → Deep Archive | 1 | 1 | $23 → $0.99 (saves $22.01/TB-mo) |
| Glacier Flexible → Deep Archive | 90 | 90 | $3.60 → $0.99 (saves $2.61/TB-mo) |

**Decision gate:**

| Object-age profile (from Storage Lens) | Lifecycle recommendation |
|---|---|
| >20% of objects aged >30 days still in Standard | Transition to Standard-IA at 30d |
| >15% of objects aged >90 days with infrequent access | Transition to Glacier IR at 90d |
| >10% of objects aged >180 days with <1% retrieval | Transition to Deep Archive at 180d |
| Objects aged >2555 days (7+ years) | Expiration if compliance permits |

**Per-TB savings calculation:**
```
savings_per_TB = affected_TB × (current_rate − new_rate)
transition_cost = (affected_TB / avg_object_size_GB) × $0.01/1000
net_monthly_savings = savings_per_TB − (transition_cost / months_to_amortize)
```

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

**Intelligent-Tiering tier configuration:**

```bash
aws s3api put-bucket-intelligent-tiering-configuration \
  --bucket my-bucket \
  --id ConfigID \
  --intelligent-tiering-configuration '{
    "Status": "Enabled",
    "Tierings": [
      {"Days": 90, "AccessTier": "ARCHIVE_ACCESS"},
      {"Days": 180, "AccessTier": "DEEP_ARCHIVE_ACCESS"}
    ]
  }'
```

**Cost comparison: Intelligent-Tiering vs lifecycle for 50 TB:**
```
Intelligent-Tiering: $125/mo monitoring + $483.25 storage = $608.25/mo
Lifecycle:           $0 monitoring + $429.85 storage = $429.85/mo
Lifecycle is $178.40/mo cheaper for predictable patterns.
But IT avoids misclassification risk for unpredictable access.
```

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

**Prefix-based grouping for cost allocation:**
```
Bucket: data-lake-prod
  /raw/logs/          — 20 TB, 95% >180d, <0.1% retrieval → DA at 180d (saves $380/mo)
  /raw/events/        — 10 TB, 60% >90d, <1% retrieval → GIR at 90d (saves $114/mo)
  /curated/reports/   — 8 TB, 80% <30d, 15% retrieval → keep Standard
  /archive/snapshots/ — 7 TB, 100% >365d, 0% retrieval → Batch Ops to DA (saves $154/mo)
```

### Step 4: Versioning cost impact

Versioning retains every prior object version. Without lifecycle rules
on noncurrent versions, storage grows unbounded.

**Detection:**
```
noncurrent_pct = NoncurrentVersionStorageBytes /
                 (NoncurrentVersionStorageBytes + CurrentVersionStorageBytes)

If noncurrent_pct > 10% → versioning bloat finding
```

**Noncurrent-version lifecycle template:**
```json
{
  "ID": "noncurrent-version-tiering",
  "Status": "Enabled",
  "NoncurrentVersionTransitions": [
    { "NoncurrentDays": 30,  "NewerNoncurrentVersions": 3, "NewStorageClass": "STANDARD_IA" },
    { "NoncurrentDays": 90,  "NewerNoncurrentVersions": 3, "NewStorageClass": "GLACIER_IR" },
    { "NoncurrentDays": 180, "NewerNoncurrentVersions": 3, "NewStorageClass": "DEEP_ARCHIVE" }
  ],
  "NoncurrentVersionExpiration": { "NoncurrentDays": 365, "NewerNoncurrentVersions": 3 }
}
```

Keeps the 3 most recent noncurrent versions; transitions older ones to
cheaper tiers; expires after 365 days.

**Delete marker cleanup:**
```bash
# Schedule a Batch Operations job to remove delete markers
# on objects where the delete marker is the only version
aws s3control create-job \
  --account-id <acct> \
  --operation '{"S3DeleteObjectTagging": {}}' \
  --manifest '{"Spec": {"Format": "S3BatchOperations_CSV_20180820",
               "Location": {"Bucket": "...","Key": "..."}}}'
```

### Step 5: Retrieval-pattern matching

Choosing the right archive tier depends on retrieval frequency and
latency tolerance.

**Archive tier comparison:**

| Tier | Storage $/TB-mo | Retrieval $/GB | Retrieval latency | Min storage duration | Use case |
|---|---|---|---|---|---|
| Standard-IA | $12.50 | $0.01 | ms | 30 days | Infrequent access, ms latency needed |
| One Zone-IA | $10.10 | $0.01 | ms | 30 days | Infrequent, reproducible data |
| Glacier IR | $4.00 | $0.03 | ms | 90 days | Quarterly access, ms latency |
| Glacier Flexible | $3.60 | $0.03 (std), $0.025 (bulk), $0.10 (exp) | 1-5 min (std), 5-12h (bulk) | 90 days | Annual access, minutes ok |
| Deep Archive | $0.99 | $0.02 (std), $0.0025 (bulk) | 12h (std), 48h (bulk) | 180 days | Compliance archive, hours ok |

**Retrieval cost surprise prevention:**
```
monthly_retrieval_cost = retrieved_GB × retrieval_rate

Example: 5 TB retrieved from Glacier Flexible per month (standard):
  5,120 GB × $0.03 = $153.60/month retrieval
  vs storage savings: 5 TB × ($12.50 - $3.60) = $44.50/month saved

  NET: the retrieval cost EXCEEDS the storage savings.
  This bucket should use Standard-IA, not Glacier Flexible.
```

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

**Batch Operations COPY with class override:**
```bash
# Generate manifest of Standard-class objects
aws s3api list-objects-v2 --bucket my-bucket \
  --query 'Contents[?StorageClass==`STANDARD`].[Key]' \
  --output text | awk '{print "my-bucket,"$1}' > manifest.csv
aws s3 cp manifest.csv s3://manifest-bucket/manifest.csv

# Create Batch Operations job
aws s3control create-job --account-id <acct> \
  --operation '{"S3ReplicateObject": {}}' \
  --report '{"Bucket":"s3://report-bucket","Enabled":true}' \
  --manifest '{"Spec":{"Format":"S3BatchOperations_CSV_20180820","Location":{"Bucket":"manifest-bucket","Key":"manifest.csv"}}}' \
  --role-arn arn:aws:iam::<acct>:role/S3BatchOperationsRole
```

**Cost:** $0.25 per million objects. For 10M objects: $2.50 — negligible
vs monthly savings. Use Batch Ops for immediate migration of existing
objects; use lifecycle for future objects.

### Step 7: Impact estimation

Compute the monthly savings for each recommendation:

```
current_monthly_cost =
  standard_TB × $23 + standard_ia_TB × $12.50 + one_zone_ia_TB × $10.10 +
  glacier_ir_TB × $4.00 + glacier_TB × $3.60 + deep_archive_TB × $0.99

projected_monthly_cost =
  projected_standard_TB × $23 + projected_ia_TB × $12.50 +
  projected_gir_TB × $4.00 + projected_glacier_TB × $3.60 +
  projected_deep_archive_TB × $0.99 + intelligent_tiering_monitoring_fee

monthly_saving = current_monthly_cost - projected_monthly_cost
```

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

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Test lifecycle on a prefix filter first.** Deploy the policy with
  a `Filter.Prefix` on a non-critical prefix; verify transitions; then
  widen to the whole bucket.
- **Verify MFA Delete status before lifecycle expiration.** If MFA
  Delete is enabled, lifecycle expiration of current versions will be
  blocked. Inform the operator.
- **Check Object Lock before recommending expiration.** Objects under
  Object Lock retention cannot be expired or overwritten until the lock
  expires.
- **Estimate transition request cost for small-object buckets.**
  Millions of tiny objects transitioning in one day can incur thousands
  of dollars in per-request fees.
- **Batch Operations jobs are irreversible.** A COPY job that overwrites
  objects in place with the wrong storage class is destructive. Always
  test on a manifest subset first.
- **Glacier/Deep Archive transitions are not instant.** S3 processes
  transitions asynchronously (typically within 12 hours). Do not expect
  immediate class change.
- **Noncurrent-version expiration is permanent.** Once expired, prior
  versions cannot be recovered. Verify the `NewerNoncurrentVersions`
  count before deploying.
- **Bulk-operation limit:** Process at most 5 buckets per batch. Sort
  by estimated savings, verify each batch before proceeding. Abort if
  any bucket shows unexpected retrieval cost spikes.

## Recent AWS features (2024-2026)

- **S3 Intelligent-Tiering Archive Access (2024-2025):** Configurable
  Archive Access at 90 days and Deep Archive Access at 180 days. No
  retrieval fees for moving between tiers within IT.
- **S3 Glacier Instant Retrieval (GIR) maturity:** Millisecond-latency
  archive at $4/TB-month. Increasingly the default choice for quarterly-
  access data that needs fast retrieval.
- **S3 Storage Lens prefix-level metrics (2024):** Object-age and
  activity breakdown by prefix. Requires Storage Lens Advanced (paid).
  Free tier provides bucket-level only.
- **S3 Batch Operations COPY with storage class (2024):** COPY job can
  override the storage class, enabling immediate bulk migration without
  waiting for lifecycle timing.
- **S3 Object Lambda cost (2024-2025):** Not directly a storage-class
  concern but affects total S3 bill. Flag if Object Lambda is in use.
- **Directory Buckets (S3 Express One Zone, 2024-2025):** Ultra-low-
  latency bucket type for ML/AI training data. Different pricing model
  ($0.16/GB-month + request fees). Out of scope for this skill but
  flag if detected.
- **S3 Tables (2025):** Managed Apache Iceberg tables on S3. Separate
  pricing from standard storage. Flag if detected.

## References

- `references/s3-pricing-and-storage-classes.md` — pricing tables,
  minimum-days matrix, Intelligent-Tiering configuration, Batch
  Operations guide, extended NEVER list, regional pricing multipliers.
- `references/worked-examples.md` — full worked examples (lifecycle
  deployment, Intelligent-Tiering activation, versioning bloat, already-
  optimal, NEED_MORE_INFO, end-to-end walkthrough).

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
