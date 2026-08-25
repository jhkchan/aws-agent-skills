---
name: cloudtrail-cost-optimizer
description: 'Optimises AWS CloudTrail cost across seven dimensions: trail consolidation (single organization trail replaces N per-region or member-account trails, eliminating duplicate log volume and per-trail KMS/SNS overhead), management-vs-data-event volume analysis (data events are ~10x costlier per event than management events — curate S3/Lambda data event sources), S3 lifecycle policy for log files (Glacier Instant/Deep Archive transition after 90 days eliminates ~80% of Standard storage cost), CloudTrail Lake event-data-store cost (per-GB ingestion at $0.75/GB-month plus retention — partition with event-category filters), CloudWatch Logs delivery cost (avoid dual-publishing CloudTrail to both S3 and CloudWatch Logs when only one consumer exists), SNS notification cost ($0.50 per million notifications — consolidate trail SNS topics), KMS key cost per trail (one CMK shared across org trail, not one per trail), Insights event cost ($0.50 per 100k management events — enable only for accounts with anomalous activity...'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted trail configurations and Cost Explorer exports. Live-account optimization uses aws cloudtrail describe-trails, get-event-selectors, get-insights-selectors, get-event-data-store, aws organizations describe-organization, list-accounts, aws s3api get-bucket-lifecycle-configuration, head-bucket, aws kms describe-key, get-key-rotation-status, aws ce...
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Governance
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: Optimising CloudTrail spend, consolidating multi-region or member trails into a single org trail, curating data event sources (S3/Lambda data events), tuning S3 lifecycle for log buckets, reviewing CloudTrail Lake event data store ingestion cost, disabling dual-publishing to CloudWatch Logs, consolidating KMS keys per trail, evaluating CloudTrail Insights cost, or running a governance FinOps sweep.
  when_not_to_use: CloudTrail functional troubleshooting (use cloudtrail-missing-events-troubleshooter or cloudtrail-gap-troubleshooter), CloudTrail Lake query authoring (use cloudtrail-lake-operator), or CloudTrail alert automation (use cloudtrail-alert-automator). This skill focuses on cost-driven optimization decisions, not on whether events are missing or alerts fire.
  activation_triggers: optimise CloudTrail cost, CloudTrail trail consolidation, CloudTrail org trail vs member trail, CloudTrail data event volume, CloudTrail S3 lifecycle, CloudTrail log file Glacier transition, CloudTrail Lake event data store cost, CloudTrail CloudWatch Logs delivery cost, CloudTrail KMS key per trail, CloudTrail Insights event cost, CloudTrail log file integrity validation, CloudTrail SNS notification cost, CloudTrail organizational trail deduplication, CloudTrail Athena partition projection, CloudTrail FinOps savings, CloudTrail monthly savings estimate, reduce CloudTrail bill, governance cost review
  invocation_schema: 'Input: either (a) a CloudTrail trail name + live-account context, (b) an Organizations account list with per-trail configuration summary, OR (c) a Cost Explorer export of CloudTrail spend with at least 30 days of observation plus trail configurations. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ ESTIMATED_SAVINGS/MIGRATION_STEPS block per trail (or per account for consolidation cases), where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE.'
  invocation_example: "# Minimal valid input (offline finding classification):\nTrailName: aws-organizational-trail\nIsOrganizationTrail: true\nIsMultiRegionTrail: true\nIncludeManagementEvents: true\nDataEventSources:\n  - S3 (all buckets) — 142,000,000 events/month\n  - Lambda (all functions) — 8,400,000 events/month\nInsightsEnabled: true (both ApiCallRateInsight and ApiCallErrorInsight)\nKMSKeyId: alias/cloudtrail-org-cmk\nCloudWatchLogsLogGroupArn: arn:aws:logs:us-east-1:111111111111:log-group:cloudtrail-org\nS3Bucket: org-cloudtrail-logs-us-east-1\nS3LifecyclePolicy: none\nRegion: us-east-1\nMonthlySpend: $1,847.32\nDataEventMonthlyVolume: 150.4M events\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CloudTrail, trail consolidation, organization trail, cost optimization, data events, management events, S3 lifecycle, Glacier transition, CloudTrail Lake, event data store, CloudWatch Logs, SNS notification, KMS key, Insights, log file integrity, Athena partition projection, Requester Pays, FinOps, governance, audit logging
  tags: cloudtrail, governance, cost-optimization, finops, audit-logging, organizational-trail, s3-lifecycle
---

# CloudTrail Cost Optimizer

## What this skill does

Translates a CloudTrail trail configuration into a concrete cost-
optimization recommendation with a dollar-denominated savings estimate.
The verdict is the highest-leverage action across seven dimensions —
trail consolidation, data-event curation, S3 lifecycle, CloudTrail Lake,
CloudWatch Logs delivery, KMS key sharing, and Insights tuning — applied
in priority order. Always pairs the recommendation with exact CLI
commands (or CloudFormation/Terraform snippets for trail recreation).

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Four headline rules and the cost formula | First read |
| Mindset | Why org-trail consolidation is the #1 lever | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying a trail |
| Pre-flight data gate | Trail config, S3 lifecycle, Cost Explorer | Before any recommendation |
| Step 0 non-obvious behaviours | Data event cost curve, Lake vs S3, digest PUTs | Edge cases |
| Step 1 Trail consolidation | Org trail replaces N member trails | The headline savings dimension |
| Step 2 Data event curation | S3/Lambda data event volume reduction | High-volume accounts |
| Step 3 S3 lifecycle for logs | Glacier transition, versioning cleanup | Long-retention trails |
| Step 4 CloudTrail Lake cost | Event data store ingestion + retention | EDS-based analysis |
| Step 5 CloudWatch Logs delivery | Dual-publishing elimination | S3-only consumers |
| Step 6 KMS, SNS, Insights | Shared CMK, topic consolidation, Insights gating | Per-trial overhead |
| Step 7 Athena partition projection | Log query cost control | Cost analysis queries |
| Step 8 Impact estimation | The cost formula and worked math | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | CONFIRM gate, log integrity, retention SLA | Before any apply CLI |

## Quick start

- Org trail consolidation is the #1 lever (N member trails re-emit the org's management events) — rationale in `references/advanced-patterns.md`.
- **Cost formula (memorise this):**
  `monthly_cost = (data_events × $0.10/100k)
               + (management_events × $0.00 free)
               + (s3_storage_GB × $0.023 Standard)
               + (lake_ingestion_GB × $0.75)
               + (kms_requests × $0.03/10k)
               + (sns_notifications × $0.50/1M)
               + (insights_events × $0.50/100k)`
- Data events are 10x costlier (curate to high-value sources) and S3 lifecycle is a one-click ~80% storage cut — details in `references/advanced-patterns.md`.

## Mindset

→ Governance-vs-spend framing and the four principles (capture once, rank data events, logs are cold data, Lake-for-query/S3-for-archive) — `references/advanced-patterns.md`.

## Quick reference — verdict thresholds

| Observation (30-90 day window) | Verdict | Recommendation |
|---|---|---|
| > 1 trail per org AND none has `IsOrganizationTrail=true` | **FURTHER_OPTIMIZATION_AVAILABLE** (consolidation) | Step 1 — create single org trail, delete member trails |
| Org trail exists AND member trails remain active (duplicate capture) | **FURTHER_OPTIMIZATION_AVAILABLE** (consolidation) | Step 1 — delete member trails; org trail already covers |
| S3 data events = `All Buckets` AND high-volume low-value buckets (logs, ELB, CDN) present | **FURTHER_OPTIMIZATION_AVAILABLE** (data curation) | Step 2 — switch to basic-event-selector with explicit bucket list |
| Lambda data events = `All Functions` AND > 1000 functions with > 80% low-audit-value | **FURTHER_OPTIMIZATION_AVAILABLE** (data curation) | Step 2 — curate function ARNs or disable Lambda data events |
| S3 log bucket lifecycle policy absent OR Standard-only beyond 90 days | **FURTHER_OPTIMIZATION_AVAILABLE** (lifecycle) | Step 3 — add Glacier Instant Retrieval @ 90d, Deep Archive @ 180d |
| CloudTrail Lake EDS ingesting > 50 GB/month of free-tier-redundant data | **FURTHER_OPTIMIZATION_AVAILABLE** (Lake) | Step 4 — add event-category filter, narrow EDS scope |
| CloudTrail publishing to both S3 AND CloudWatch Logs AND only S3 consumers exist | **FURTHER_OPTIMIZATION_AVAILABLE** (Logs) | Step 5 — disable CloudWatchLogsLogGroupArn |
| Each trail has its own KMS CMK AND > 3 trails in the org | **FURTHER_OPTIMIZATION_AVAILABLE** (KMS) | Step 6 — share one CMK across all trails |
| CloudTrail Insights enabled on ALL trails AND no anomalous findings in 90 days | **FURTHER_OPTIMIZATION_AVAILABLE** (Insights) | Step 6 — disable Insights on low-risk trails |
| Org trail + curated data events + Glacier lifecycle + single CMK + Lake sized for interactive queries only | **OPTIMIZED** | None — continue monitoring |
| Cost Explorer CloudTrail line absent or window < 30 days | **NEED_MORE_INFO** | Pull 30-90 day Cost Explorer, re-evaluate |
| All dimensions verified AND a change was applied and confirmed this session | **OPTIMIZED** | Emit post-state verification |

## Pre-flight: data gate (run before any optimization decision)

Optimization decisions are only as good as the underlying data. Pull
these signals before any recommendation. Full CLI sequences are in
`references/cloudtrail-pricing-and-inventory.md`.

**Required data sources** (summarized — see reference for full CLI):
→ All 9 data-source commands (trail configs, selectors, org structure, S3 lifecycle, bucket size, EDS, KMS, Cost Explorer) — `references/diagnostic-commands.md`.

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `describe-trails` returns empty `trailList` | **NEED_MORE_INFO**. CloudTrail may be disabled or IAM denies cloudtrail:DescribeTrails. |
| 30-day Cost Explorer window shows $0 CloudTrail spend | Trail may be in free tier; check data-event dimension separately. |
| S3 `BucketSizeBytes` metric absent for CloudTrail prefix | Bucket untagged or metrics not enabled. Fall back to S3 inventory report. |
| `get-event-selectors` returns `CloudTrail Insights not enabled` | Insights dimension is no-op; skip Step 6 Insights sub-check. |
| `list-event-data-stores` empty | CloudTrail Lake not configured; skip Step 4. |
| Observation window < 30 days | **NEED_MORE_INFO**. Minimum 30 days; 90 days preferred for seasonality. |
| Trail `Status != RUNNING` (logging suspended) | Skip optimization; surface as BLOCKED. Resume logging first. |

When Cost Explorer and CloudTrail metrics disagree, Cost Explorer is
authoritative for the dollar figure; CloudTrail metrics are authoritative
for event counts.

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation
→ All 12 gotchas (free first management trail, org trail auto-multi-region, no cross-trail dedup, lifecycle hits digests, double EDS ingest, Logs billed by bytes, KMS per-call, Insights per-events-analyzed, Requester Pays, Athena full scans, digest PUTs, EventBridge per-event) — `references/advanced-patterns.md`.

### Step 1: Trail consolidation (the #1 lever)

→ Why consolidation is the primary cost lever — `references/advanced-patterns.md`.

**The consolidation math:** worked math in `references/cloudtrail-worked-examples.md`.

→ Data-event duplicate-cost compounding and the org-management-account prerequisite — `references/advanced-patterns.md`.

**Decision gate after consolidation analysis:**

| Trail inventory | Verdict | Action |
|---|---|---|
| Org trail exists AND no member trails | No consolidation finding | Proceed to other dimensions. |
| Org trail exists AND member trails present | **FURTHER_OPTIMIZATION_AVAILABLE** | Delete member trails; org trail covers all member events. |
| No org trail AND > 1 trail across accounts | **FURTHER_OPTIMIZATION_AVAILABLE** | Create org trail, migrate consumers, delete member trails. |
| No org trail AND 1 trail per account (standard) | **FURTHER_OPTIMIZATION_AVAILABLE** | Convert to org trail (single creation in mgmt account). |
| Standalone account (not in org) | Skip Step 1 | No consolidation possible. |

→ Org-trail creation and member-trail deletion CLI — `references/diagnostic-commands.md`.

### Step 2: Data event curation

→ Pricing comparison (management events free on first trail; data events $0.10/100k) — `references/cloudtrail-pricing-and-inventory.md`.

**Decision tree:**
```
Is the trail capturing S3 data events on All Buckets?
├── NO → S3 data event check passes.
└── YES → Are > 20% of events from low-value buckets (logs, ELB,
           CDN, CloudTrail's own bucket)?
    ├── NO → S3 data events are justified.
    └── YES → **FURTHER_OPTIMIZATION_AVAILABLE** (curate bucket list)

Is the trail capturing Lambda data events on All Functions?
├── NO → Lambda data event check passes.
└── YES → Are > 50% of functions low-audit-value (cron jobs, internal
           health checks, dev-stage functions)?
    ├── NO → Lambda data events are justified.
    └── YES → **FURTHER_OPTIMIZATION_AVAILABLE** (curate or disable)
```

→ Selector-form guidance and the put-event-selectors CLI — `references/cloudtrail-pricing-and-inventory.md`.

**Data-event saving from curation:** worked math in `references/cloudtrail-worked-examples.md`.

### Step 3: S3 lifecycle for log files

CloudTrail log files are write-once-read-rarely. Standard storage beyond
90 days is wasted spend; Glacier Instant Retrieval keeps millisecond
read latency at 19% of Standard cost.

**Storage class cost comparison:** table in `references/cloudtrail-pricing-and-inventory.md`.

**Recommended lifecycle policy** (full JSON in
`references/cloudtrail-pricing-and-inventory.md`):
- Day 30 → Intelligent-Tiering (auto-tiering; ~$0.0025/GB archive tier)
- Day 90 → Glacier Instant Retrieval ($0.004/GB-month, ms latency)
- Day 180 → Deep Archive ($0.00099/GB-month, 12-hour restore)
- Day 365 → Expire (or your compliance retention SLA)

→ put-bucket-lifecycle-configuration CLI — `references/diagnostic-commands.md`.

**Storage saving math:** worked math in `references/cloudtrail-worked-examples.md`.

### Step 4: CloudTrail Lake event data store cost

→ Lake pricing model (ingestion $0.75/GB one-time + retention $0.023/GB) — `references/cloudtrail-pricing-and-inventory.md`.

**Decision tree:**
```
Is the EDS ingesting all event categories (management + data + insight)?
├── NO → EDS scope is curated; check ingestion GB.
└── YES → Are data events needed for the EDS use case?
    ├── NO → **FURTHER_OPTIMIZATION_AVAILABLE** (filter to management)
    └── YES → Can high-volume low-value sources be excluded?
        ├── NO → EDS is justified.
        └── YES → **FURTHER_OPTIMIZATION_AVAILABLE** (narrow EDS scope)
```

→ update-event-data-store CLI with event-category filter — `references/diagnostic-commands.md`.

**Lake cost math:** worked math in `references/cloudtrail-worked-examples.md`.

### Step 5: CloudWatch Logs delivery cost

CloudTrail can publish to both S3 and CloudWatch Logs. Logs ingestion
bills by bytes at $0.50/GB — typically 5x more expensive than S3 for
the same events.

**Decision tree:**
```
Is CloudTrail publishing to CloudWatch Logs?
├── NO → Logs check passes.
└── YES → Are there CloudWatch Logs consumers (metric filters, alarms,
           Logs Insights queries)?
    ├── YES → Are they high-value enough to justify 5x storage cost?
    │        ├── YES → Keep Logs delivery.
    │        └── NO → **FURTHER_OPTIMIZATION_AVAILABLE** (migrate to Athena-on-S3)
    └── NO → **FURTHER_OPTIMIZATION_AVAILABLE** (disable Logs delivery)
```

→ update-trail --no-cloud-watch-logs-log-group-arn CLI — `references/diagnostic-commands.md`.

**Logs delivery cost math:** worked math in `references/cloudtrail-worked-examples.md`.

### Step 6: KMS, SNS, and Insights tuning

These per-trial overheads are individually small but multiply across
trail count.

**KMS key consolidation:** cost math in `references/cloudtrail-worked-examples.md`.

**KMS policy snippet allowing CloudTrail service to use a shared key**
lives in `references/cloudtrail-pricing-and-inventory.md` (the policy
grants `kms:GenerateDataKey*` to `cloudtrail.amazonaws.com` scoped by
`aws:SourceArn` to the trail ARN).

→ SNS consolidation and Insights gating guidance — `references/advanced-patterns.md`.

→ stop-insights-logging CLI — `references/diagnostic-commands.md`.

### Step 7: Athena partition projection for cost analysis

→ Full Athena partition projection deep dive (scan-cost math, DDL pointer) — `references/advanced-patterns.md`.

### Step 8: Impact estimation

Compute the monthly savings for each recommendation:

```
current_monthly_cost =
  (data_events / 100000 × $0.10) +
  (s3_storage_GB × $0.023) +
  (lake_ingestion_GB × $0.75) +
  (logs_ingestion_GB × $0.50) +
  (insights_events / 100000 × $0.50) +
  (kms_keys × $1.50) +
  (sns_notifications / 1000000 × $0.50)

projected_monthly_cost = <recompute each term after changes>

monthly_saving = current_monthly_cost - projected_monthly_cost
```

Always state assumptions: data event volume, S3 storage size, Lake
ingestion rate, Logs ingestion rate, Insights event volume, KMS key
count, SNS topic count, pricing region.

### Step 9: Final verdict

- Any dimension recommends a change → **FURTHER_OPTIMIZATION_AVAILABLE**.
- All dimensions pass AND org trail + curated data events + lifecycle +
  single CMK + Lake scoped to interactive queries → **OPTIMIZED**.
- Change applied and verified this session → **OPTIMIZED** (post-state).
- Data insufficient (trail inventory absent, window < 30 days) →
  **NEED_MORE_INFO**.

Never emit `FURTHER_OPTIMIZATION_AVAILABLE` without first discharging
every `NEED_MORE_INFO`/`BLOCKED` gate.

## Output format

→ Full per-operation label contract (TARGET / VERDICT / REASON / RECOMMENDATION / ESTIMATED_SAVINGS / MIGRATION_STEPS / CONFIRM) — `references/cloudtrail-worked-examples.md`. The STRICT output contract below remains authoritative.

Full worked examples (org-trail consolidation, data-event curation, S3
lifecycle rollout, CloudTrail Lake scoping, already-optimized, end-to-
end walkthrough) are in `references/cloudtrail-worked-examples.md`.

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
misclassification or an arithmetic contradiction that breaks downstream
FinOps automation. Self-check EVERY emitted block against these rules
before returning the response.

### Required output structure

Every response MUST be a single block using these literal labels, in this
order. Do NOT substitute markdown headings, camelCase, or bold variants.

```text
TARGET: <trail-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <trail inventory + data events + storage class + Lake + Logs>
  Proposed: <consolidated inventory + curated events + Glacier + Lake scope>
  Dimensions changed: <consolidation | data_events | lifecycle | lake | logs | kms_sns_insights | athena>
  Dimensions checked: <list ALL seven, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>    ← MUST show subtotals per cost term
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
   the verdict MUST be `OPTIMIZED`. A cost-neutral compliance
   improvement is surfaced in REASON, NOT as a dollar saving.

2. **NEVER show savings math that does not balance.**
   `Current monthly − Projected monthly` MUST equal `Monthly saving`,
   rounded to 2 decimal places.

3. **NEVER emit scratch lines** ("WAIT — recompute", "Hmm, let me redo",
   "corrected:") in the output. Finalize the math before emitting.

4. **NEVER recommend org trail consolidation without verifying the
   account is the org management account.** Creating an org trail from
   a member account fails. Surface this as a prerequisite.

5. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all seven dimensions, each marked
   ✓ (no finding) or → (finding).

6. **NEVER recommend disabling log file integrity validation without
   confirming S3 Object Lock provides equivalent tamper-evidence.**
   Disabling validation halves digest PUT cost but loses the audit
   attestation if Object Lock isn't enforced.

7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE with verified math

Every field below is internally consistent. Copy this shape exactly.
Additional full worked examples (org-trail consolidation, data-event
curation, S3 lifecycle, CloudTrail Lake scoping, already-optimized,
NEED_MORE_INFO) are in `references/cloudtrail-worked-examples.md`.

```text
TARGET: aws-organizational-trail
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Organization trail capturing S3 data events on All Buckets
  includes 113M events/month from log and CDN buckets (80% of total)
  that have no audit value. S3 log bucket has no lifecycle policy,
  retaining 500 GB in Standard at $0.023/GB. Combined curation +
  lifecycle drops monthly CloudTrail spend 62%.
RECOMMENDATION:
  Current: org trail + All-Buckets S3 data events + Standard storage + no Lake
  Proposed: org trail + curated S3 data events (8 high-value buckets) + Glacier IR @ 90d
  Dimensions changed: data_events (Step 2) + lifecycle (Step 3)
  Dimensions checked: consolidation ✓  data_events → (curate)
    lifecycle → (no policy)  lake ✓  logs ✓  kms_sns_insights ✓  athena ✓
  Confidence: HIGH — S3 metrics confirm 113M/142M events are low-value
    bucket writes; lifecycle math is deterministic; us-east-1 pricing.
ESTIMATED_SAVINGS:
  Current monthly: $1,847.32
    data_events: $142.00  s3_storage: $11.50  kms_keys: $1.50
    sns: $0.70  insights: $0  logs: $0  lake: $0  athena_scans: $1,692.62
  Projected monthly: $697.32
    data_events: $29.00 (curated)  s3_storage: $1.79 (Glacier IR + Deep Archive)
    kms_keys: $1.50  sns: $0.30  insights: $0  logs: $0  lake: $0  athena: $664.73
  Monthly saving: $1,150.00   ($1,847.32 − $697.32 = $1,150.00 ✓)
  Annual saving: $13,800.00
MIGRATION_STEPS:
  1. Apply advanced event selectors with curated bucket list:
     aws cloudtrail put-event-selectors --trail-name aws-organizational-trail \
       --advanced-event-selectors file://curated-selectors.json
  2. Apply S3 lifecycle policy to the log bucket:
     aws s3api put-bucket-lifecycle-configuration \
       --bucket org-cloudtrail-logs-us-east-1 \
       --lifecycle-configuration file://cloudtrail-lifecycle.json
  3. Verify lifecycle policy took effect (no immediate object transitions):
     aws s3api get-bucket-lifecycle-configuration \
       --bucket org-cloudtrail-logs-us-east-1
  4. After 30 days, query S3 storage metrics to confirm Intelligent
     Tiering is taking effect.
CONFIRM: About to put-event-selectors on aws-organizational-trail
  (All Buckets → 8 high-value buckets) and apply S3 lifecycle to
  org-cloudtrail-logs-us-east-1. Monthly saving $1,150.00 (62%).
  Proceed? (yes/no)
```

**Self-check before emit:**
- [ ] `Current monthly − Projected monthly == Monthly saving` (2 decimals)?
- [ ] `Monthly saving × 12 == Annual saving`?
- [ ] All seven dimensions listed in `Dimensions checked`?
- [ ] Every `→` dimension has a corresponding MIGRATION_STEPS entry?
- [ ] No scratch/recompute text in the block?

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has a concrete, savings-bearing recommendation. |
| `OPTIMIZED` | Either (a) all dimensions pass (org trail + curated data events + lifecycle + single CMK + Lake scoped), OR (b) a change was applied and verified this session. |
| `NEED_MORE_INFO` | Data gate failed: trail inventory absent, Cost Explorer window < 30 days, or S3 metrics unavailable. |
| `BLOCKED` | Hard precondition prevents evaluation: trail Status != RUNNING (logging suspended), IAM denies cloudtrail:DescribeTrails. |

**Zero-savings rule:** If MONTHLY_SAVING == $0.00 for every dimension,
verdict MUST be `OPTIMIZED`, never `FURTHER_OPTIMIZATION_AVAILABLE`.
Exception: a compliance improvement without cost change is surfaced in
REASON, not as dollar savings.

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend org trail consolidation without verifying the
   account is the org management account.** Member accounts cannot
   create org trails; the API call fails.
2. **NEVER recommend disabling management events to reduce cost.**
   Management events are free on the first trail per region. Disabling
   breaks audit completeness for ~zero savings.
3. **NEVER recommend Deep Archive transition without confirming the
   audit RTO tolerates 12-hour restore.** For incident-response use
   cases, Glacier Instant Retrieval (ms-latency) is the right choice.
4. **NEVER recommend curating data events without confirming the
   bucket list is complete.** Missing a high-value bucket creates a
   silent audit blind spot.
5. **NEVER recommend disabling CloudWatch Logs delivery without
   auditing for existing metric filters, alarms, or Logs Insights
   queries on the log group.** Disabling breaks downstream monitoring.

Extended anti-patterns in `references/cloudtrail-worked-examples.md`.

## Pre-flight safety checks (run before any remediation CLI)

→ Full checklist (confirmation gate, org-trail coverage before deletion, selector snapshot, single-prefix lifecycle test, Object Lock check, EDS export-first, KMS policy update, Insights irreversibility, 5-trail batches) — `references/diagnostic-commands.md`.

## Recent AWS features (2024-2026)

→ All four updates (Lake enhancements, advanced event selectors GA, Glacier Instant Retrieval, Insights for data events) — `references/advanced-patterns.md`.

## References

- `references/cloudtrail-pricing-and-inventory.md` — pricing tables,
  trail inventory CLI, event selector syntax, KMS key policy templates,
  S3 lifecycle JSON, Athena partition projection DDL, regional pricing
  multipliers, cost calculation worked examples.
- `references/cloudtrail-worked-examples.md` — org-trail consolidation,
  data-event curation, S3 lifecycle, CloudTrail Lake scoping, already-
  optimized, end-to-end walkthrough, extended NEVER list, edge cases.

## References (load on demand)

- [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — pre-flight data-source commands; per-step apply CLI (org trail, selectors, lifecycle, EDS, Logs, Insights); pre-remediation safety checks
- [`references/cloudtrail-worked-examples.md`](references/cloudtrail-worked-examples.md) — per-step cost math and the per-operation output format, plus the pre-existing full worked examples per dimension
- [`references/cloudtrail-pricing-and-inventory.md`](references/cloudtrail-pricing-and-inventory.md) — pricing comparisons and selector forms, plus the pre-existing pricing tables, inventory CLI, KMS policy, lifecycle JSON, Athena DDL
- [`references/advanced-patterns.md`](references/advanced-patterns.md) — Step 0 gotchas, mindset principles, Step 1 / 6 / 7 rationale, recent AWS features (2024-2026)

## Domain

AWS CloudOps / Governance Audit Logging Cost Optimization & FinOps.

## AWS documentation

- **AWS CloudTrail User Guide** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-user-guide.html
- **AWS CloudTrail pricing** — https://aws.amazon.com/cloudtrail/pricing/
- **CloudTrail organizational trails** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html
- **CloudTrail event selectors** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-data-events-with-cloudtrail.html
- **CloudTrail Lake** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake.html
- **CloudTrail Insights** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-insights-events-with-cloudtrail.html
- **S3 lifecycle configuration** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html
- **Athena partition projection** — https://docs.aws.amazon.com/athena/latest/ug/partition-projection.html
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
