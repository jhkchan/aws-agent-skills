---
name: cloudwatch-logs-cost-optimizer
description: 'Optimises Amazon CloudWatch Logs cost across six dimensions: log group retention (Never expire is the #1 waste — moving to 30 days typically cuts storage cost 90%+ since storage is billed at $0.03/GB-month and Never-expire groups accumulate indefinitely), Logs Insights query cost ($0.005/GB scanned — frequent queries should be converted to metric filters which are free), CloudWatch agent buffer tuning (batch_count and batch_size reduce PutLogEvents API charges at $0.40/million ingestion requests), S3 export via Firehose for cold-storage compliance archives ($0.023/GB-month S3 Standard vs Logs $0.50/GB ingestion + $0.03/GB-month storage), subscription filter cost-aware cross-account aggregation, and vended log destinations (VPC Flow Logs and Route53 Resolver Logs sent to S3 directly bypass Logs ingestion fees entirely). Evaluates account-level data protection policies for PII storage reduction, embedded metric format tradeoffs, and log group aggregation patterns. Emits OPTIMIZED when no cost lever yields f...'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted CloudWatch Logs metrics, retention settings, and Cost Explorer findings. Live-account optimization uses aws logs describe-log-groups, aws logs describe-metric-filters, aws logs describe-subscription-filters, aws cloudwatch get-metric-statistics (IncomingBytes, IncomingLogEvents), aws firehose describe-delivery-streams, aws ce get-cost-and-usage (AWS CLI...
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: Optimising CloudWatch Logs cost, triaging retention sweep candidates (Never-expire groups), migrating frequent Logs Insights queries to metric filters, planning a Firehose-to-S3 cold-storage pipeline for compliance archives, tuning CloudWatch agent buffer settings to reduce PutLogEvents request charges, evaluating vended log destination placement (VPC Flow Logs to S3 vs CloudWatch Logs), or running a FinOps audit of observability spend.
  when_not_to_use: CloudWatch alarm configuration or tuning (use cloudwatch-alarm-auditor), Logs Insights query debugging or syntax help (use cloudwatch-logs-insights-troubleshooter), logs-not-ingesting investigations (use cloudwatch-logs-not-ingesting-troubleshooter), S3 storage class optimization for non-log objects (use s3-storage-class-optimizer), or Firehose delivery stream troubleshooting. This skill focuses on cost-driven optimization of CloudWatch Logs, not functional debugging of log pipelines.
  activation_triggers: optimise CloudWatch Logs cost, CloudWatch Logs retention sweep, CloudWatch Logs Never expire, CloudWatch Logs Insights cost, metric filter vs Logs Insights, CloudWatch agent batch size, CloudWatch agent buffer tuning, PutLogEvents cost, Firehose S3 export logs, cold storage compliance archive, VPC Flow Logs to S3, Route53 Resolver Logs cost, vended log destinations, CloudWatch Logs subscription filter cost, embedded metric format cost, CloudWatch data protection policy, PII log reduction, CloudWatch Logs FinOps, reduce observability bill, log group aggregation
  invocation_schema: 'Input: either (a) a log group identifier + live-account context, (b) a Cost Explorer CloudWatch Logs charge breakdown, OR (c) CloudWatch Logs metrics (IncomingBytes, IncomingLogEvents) with retention setting and at least 14 days of observation. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ ESTIMATED_SAVINGS/MIGRATION_STEPS block per log group (or account-level finding), where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE.'
  invocation_example: "# Minimal valid input (offline finding classification):\nLogGroupName: /aws/lambda/order-processor-prod\nRetentionInDays: 0 (Never expire)\nRegion: us-east-1\nStoredBytes: 842 GB\nMetrics (last 30 days):\n  - IncomingBytes avg: 28 GB/day\n  - IncomingLogEvents avg: 12,000,000/day\n  - Logs Insights queries/month: 450 (scanning ~120 GB each)\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CloudWatch Logs, log retention, cost optimization, Logs Insights, metric filter, subscription filter, Firehose, S3 export, cold storage, CloudWatch agent, batch size, PutLogEvents, VPC Flow Logs, Route53 Resolver Logs, vended log destinations, embedded metric format, data protection policy, PII, log aggregation, FinOps
  tags: cloudwatch, logs, management, cost-optimization, finops, retention, firehose, s3-export
---

# CloudWatch Logs Cost Optimizer

## What this skill does

Translates a CloudWatch Logs footprint (log groups, retention settings,
ingestion volume, query patterns, agent configuration) into a concrete
cost-optimization recommendation with a dollar-denominated savings
estimate. The verdict reflects the highest-leverage action across six
dimensions — retention, query patterns, agent buffering, cold-storage
export, subscription filters, and vended destination placement — applied
in priority order. Always pairs the recommendation with exact CLI
commands or infrastructure-as-code snippets.

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Four headline rules and the cost formula | First read |
| Mindset | Why retention is the #1 lever | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying a log group |
| Pre-flight data gate | CloudWatch metrics, Cost Explorer | Before any recommendation |
| Step 0 non-obvious behaviours | Billing model gotchas, EMF, vended logs | Edge cases |
| Step 1 Retention | Never-expire sweep, tiered retention | The headline savings dimension |
| Step 2 Logs Insights vs metric filters | Query-to-filter migration | Frequent-query log groups |
| Step 3 CloudWatch agent buffer tuning | batch_count, batch_size, idle hosts | High-volume agents |
| Step 4 Firehose S3 export for cold storage | Compliance archive pipeline | Long-retention compliance logs |
| Step 5 Subscription filter / cross-account | Aggregation cost, fan-out | Multi-account setups |
| Step 6 Vended log destinations | VPC Flow Logs, Route53 Resolver to S3 | High-volume vended logs |
| Step 7 Data protection policy | PII reduction at the account level | Compliance-driven cost cut |
| Step 8 Impact estimation | The cost formula and worked math | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | CONFIRM gate, retention audit | Before any apply CLI |

## Quick start

- **Retention is the #1 lever.** A log group with `RetentionInDays = 0`
  (Never expire) accumulates storage indefinitely at $0.03/GB-month.
  Moving a 500 GB group from Never to 30 days saves ~$13,500/year in
  storage alone. Sweep Never-expire groups FIRST — they are the largest
  source of unintended CloudWatch Logs spend.
- **Cost formula (memorise this):**
  `monthly_cost = (ingested_GB × $0.50)               # ingestion
                 + (stored_GB × $0.03)               # storage (retention-dependent)
                 + (PutLogEvents_requests / 1M × $0.40)  # API ingestion requests
                 + (insights_GB_scanned × $0.005)    # Logs Insights queries`
- **Logs Insights queries are priced by GB scanned, not by result.**
  A query scanning 500 GB costs $2.50 regardless of whether it returns
  one row or one million. Frequent scheduled queries should become
  metric filters (free) or CloudWatch Metric Queries on dashboards.
- **Vended logs can bypass CloudWatch Logs entirely.** VPC Flow Logs,
  Route53 Resolver Logs, and WAF logs can publish directly to S3 via
  Firehose, avoiding the $0.50/GB ingestion fee. For high-volume vended
  logs, S3 delivery is almost always cheaper.

## Mindset

Mindset framing and the four cost principles (ingestion dominant, retention multiplier, S3 cold storage, hidden query cost) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand to understand why retention is the #1 lever.

## Quick reference — verdict thresholds

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| `RetentionInDays = 0` (Never expire) AND `StoredBytes` > 50 GB | **FURTHER_OPTIMIZATION_AVAILABLE** (retention) | Step 1 — set retention to the compliance minimum (typically 30-90 days) |
| `RetentionInDays` > 365 AND log group is not a compliance-mandated archive | **FURTHER_OPTIMIZATION_AVAILABLE** (retention / cold storage) | Step 1 or Step 4 — reduce retention or export to S3 via Firehose |
| Logs Insights queries > 100/month on a single log group AND query patterns are time-series aggregations | **FURTHER_OPTIMIZATION_AVAILABLE** (query migration) | Step 2 — convert frequent queries to metric filters |
| CloudWatch agent `batch_count` = 1000 (default) AND `PutLogEvents` requests > 1M/month per host | **FURTHER_OPTIMIZATION_AVAILABLE** (agent buffer) | Step 3 — increase batch_count to 10000, tune batch_size |
| Log group retention > 180 days for compliance AND no S3 export configured | **FURTHER_OPTIMIZATION_AVAILABLE** (cold storage) | Step 4 — deliver to S3 via Firehose, reduce Logs retention to 30 days |
| VPC Flow Logs destined to CloudWatch Logs at > 50 GB/day ingestion | **FURTHER_OPTIMIZATION_AVAILABLE** (vended destination) | Step 6 — redirect to S3 via Firehose |
| Account-level data protection policy not configured AND PII-dense application logs | **FURTHER_OPTIMIZATION_AVAILABLE** (data protection) | Step 7 — enable account-level data protection to mask PII |
| All dimensions verified AND retention set to compliance minimum AND Insights queries converted AND cold storage in S3 | **OPTIMIZED** | None — continue monitoring |
| `IncomingBytes` metrics absent or window < 14 days | **NEED_MORE_INFO** | Pull 14-30 day CloudWatch data, re-evaluate |
| All dimensions verified AND a change was applied and confirmed this session | **OPTIMIZED** | Emit post-state verification |

## Pre-flight: data gate (run before any optimization decision)

Data-gate prose, the required data-source list (describe-log-groups, IncomingBytes/IncomingLogEvents, metric/subscription filters, CloudTrail StartQuery, Cost Explorer), the metrics-vs-Cost-Explorer ground-truth rule moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md); the data-quality short-circuit table moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand before pulling metrics for an optimization decision.

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

Step 0 non-obvious behaviours (Never-expire semantics, retroactive retention, per-GB-scanned Insights, free metric filters, EMF tradeoff, PutLogEvents batching, Firehose crossover, vended-log destinations, subscription fan-out, data-protection masking) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand — each gotcha routes the recommendation away from the obvious choice.

### Step 1: Log group retention (the #1 lever)

Retention-sweep rationale moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md); the never-expire jq sweep and put-retention-policy CLI moved to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when executing the retention sweep; the tier matrix and decision gate stay inline below.

**Retention tier decision matrix:**

| Log type | Recommended retention | Rationale |
|---|---|---|
| Application logs (debug/info) | 7-30 days | Operational debugging window; beyond 30 days use S3 |
| Application logs (error/warn) | 30-90 days | Incident investigation window |
| Audit / security logs | 90-365 days (then S3) | Compliance short-term; S3 for long-term |
| Lambda function logs | 7-30 days | Most debugging happens within 7 days of deployment |
| VPC Flow Logs | 7-30 days in Logs; archive to S3 | Security investigations are post-hoc queries |
| API Gateway access logs | 7-30 days | Operational debugging; use Athena on S3 for long-term |
| Container logs (ECS/EKS via Firelens) | 7-14 days | Use a dedicated log aggregator for longer retention |

**Decision gate after retention audit:**

| Current retention | StoredBytes | Verdict | Action |
|---|---|---|---|
| Never expire (0) | > 50 GB | **FURTHER_OPTIMIZATION_AVAILABLE** | Set to compliance minimum (30-90 days) |
| Never expire (0) | < 5 GB | **FURTHER_OPTIMIZATION_AVAILABLE** (low priority) | Set to 30 days; small absolute saving |
| 90+ days AND not compliance-mandated | > 100 GB | **FURTHER_OPTIMIZATION_AVAILABLE** | Reduce to 30 days OR export to S3 (Step 4) |
| 7-30 days | Any | Retention OK | Proceed to other dimensions |
| 365+ days AND compliance-mandated | Any | Proceed to Step 4 (cold storage) | S3 export is the lever |

### Step 2: Logs Insights queries vs metric filters

Step 2 rationale moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md); the Logs Insights cost-estimation math moved to [references/worked-examples.md](references/worked-examples.md); the put-metric-filter CLI moved to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when converting frequent queries to metric filters; the migration-candidate matrix stays inline below.

**When to migrate a query to a metric filter:**

| Query pattern | Metric filter candidate? | Action |
|---|---|---|
| `filter @message like /ERROR/ \| stats count() by bin(1min)` | YES — count of ERROR messages per minute | Create metric filter with pattern `ERROR` |
| `stats avg(duration) by bin(5min)` where duration is a JSON field | YES — EMF or metric filter on JSON value | Use metric filter with JSON extraction |
| `sort @timestamp desc \| limit 20` (latest 20 errors) | NO — ad-hoc exploration | Keep as Insights query; it scans minimal data with tight time window |
| `filter @message like /timeout/ \| stats count()` run hourly | YES — scheduled aggregation | Metric filter counting timeout occurrences |
| Complex multi-line query with joins/regex | NO — exceeds filter syntax | Keep as Insights; consider precomputing via EMF |

### Step 3: CloudWatch agent buffer tuning

Step 3 rationale and the data-loss caveat moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md); the agent configuration JSON moved to [references/diagnostic-commands.md](references/diagnostic-commands.md); the PutLogEvents request-saving math moved to [references/worked-examples.md](references/worked-examples.md).
Load on demand when tuning agent buffers; the parameter table stays inline below.

| Parameter | Default | Recommended (high-volume) | Effect |
|---|---|---|---|
| `batch_count` | 1000 | 10000 | 10x fewer PutLogEvents requests |
| `batch_size` | 1,048,576 (1 MB) | 1,048,576 (max) | Already at max; do not reduce |
| `batch_wait_time` | 5 (seconds, not in older configs) | 30-60 | Longer wait allows larger batches |

### Step 4: Firehose S3 export for cold storage (compliance archives)

Step 4 rationale and architecture moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md); the 500 GB 2-year Logs-vs-Firehose-S3 cost comparison moved to [references/worked-examples.md](references/worked-examples.md); the create-delivery-stream CLI moved to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when planning a compliance-archive pipeline; the cold-storage decision gate stays inline below.

**Decision gate for cold storage migration:**

| Retention requirement | Current destination | Recommendation |
|---|---|---|
| 7-30 days | CloudWatch Logs | Keep in CW Logs (operational queries need speed) |
| 31-90 days | CloudWatch Logs | Keep in CW Logs if queried weekly; otherwise dual-write to S3 |
| 91-365 days | CloudWatch Logs | **Migrate to S3 via Firehose; reduce CW Logs retention to 30 days** |
| 365+ days (compliance) | CloudWatch Logs | **Migrate to S3 + Glacier lifecycle; CW Logs retention 0-7 days** |

### Step 5: Subscription filter and cross-account aggregation

Step 5 rationale and the double-ingestion anti-pattern note moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for cross-account aggregation; the cost-aware pattern table stays inline below.

**Cost-aware aggregation patterns:**

| Pattern | Cost | When to use |
|---|---|---|
| CW Logs → subscription filter → Firehose → S3 (central bucket) | Firehose + S3 only | Cheapest cross-account archive |
| CW Logs → subscription filter → Lambda → another CW Logs group | Double ingestion ($1.00/GB) | Avoid for high-volume logs; use Firehose instead |
| CW Logs → subscription filter → Kinesis Data Streams | Kinesis shard cost + ingestion | Real-time processing pipeline |
| VPC Flow Logs → directly to S3 (no CW Logs) | S3 only ($0.023/GB-month) | Best for pure archival |

### Step 6: Vended log destinations (VPC Flow Logs, Route53 Resolver)

Step 6 rationale and the >10 GB/day S3 guidance moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when placing vended logs; the destination decision table stays inline below.

**VPC Flow Logs destination decision:**

| Requirement | Destination | Cost |
|---|---|---|
| Real-time querying via Logs Insights | CloudWatch Logs | $0.50/GB ingest + $0.03/GB-month storage |
| Post-hoc querying via Athena | S3 (via Firehose or direct) | $0.023/GB-month + Athena scan cost |
| Compliance archive only | S3 → Glacier | $0.012/GB-month (GIR) or $0.00099 (Deep Archive) |

### Step 7: Account-level data protection policy (PII reduction)

Step 7 rationale, the cost nuance (masking saves storage, not ingestion), and when-to-enable guidance moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md); the put-account-policy CLI moved to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when enabling PII masking.

### Step 8: Impact estimation

The full impact-estimation formula block (current/projected monthly cost, monthly saving) moved verbatim to [references/worked-examples.md](references/worked-examples.md); the memorised cost formula remains in Quick start.
Load on demand when computing ESTIMATED_SAVINGS.

### Step 9: Final verdict

- Any dimension recommends a change → **FURTHER_OPTIMIZATION_AVAILABLE**.
- All dimensions pass AND retention at compliance minimum AND no
  query waste AND cold storage in S3 where applicable → **OPTIMIZED**.
- Change applied and verified this session → **OPTIMIZED** (post-state).
- Data insufficient (IncomingBytes absent, window < 14 days) →
  **NEED_MORE_INFO**.

Never emit `FURTHER_OPTIMIZATION_AVAILABLE` without first discharging
every `NEED_MORE_INFO`/`BLOCKED` gate.

## Output format

The minimal output template fence moved verbatim to [references/worked-examples.md](references/worked-examples.md); the authoritative STRICT output contract with the perfect example remains inline below.
Load on demand for the short-form template.

Full worked examples (retention sweep, query migration, Firehose cold
storage, agent buffer tuning, already-optimized, NEED_MORE_INFO) are in
`references/worked-examples.md`.

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
misclassification or an arithmetic contradiction that breaks downstream
FinOps automation. Self-check EVERY emitted block against these rules
before returning the response.

### Required output structure

Every response MUST be a single block using these literal labels, in this
order. Do NOT substitute markdown headings, camelCase, or bold variants.

```text
TARGET: <log-group-name or account-level>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <retention> days, <ingested GB>/month, <Insights queries>/month, <agent batch_count>
  Proposed: <retention> days, <ingested GB>/month, <Insights queries>/month, <agent batch_count>
  Dimensions changed: <retention | queries | agent | cold-storage | subscription | destination | data-protection>
  Dimensions checked: <list ALL seven, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>    ← MUST show subtotals (ingest, storage, requests, insights)
  Projected monthly: $<amount>
  Monthly saving: $<amount>     ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>      ← MUST equal Monthly × 12
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: <confirmation prompt text>
```

### Decision tree: cost-optimization priority

```text
Cost Optimization — START
  │
  Q1: RetentionInDays = 0 (Never expire) OR field absent?
  ├── YES → STEP 1 (retention sweep) — 90%+ storage savings; highest leverage
  └── NO  → Q2
  │
  Q2: Logs Insights queries > 100/month on this log group?
  ├── YES → STEP 2 (convert to metric filters) — $0.005/GB scan → free
  └── NO  → Q3
  │
  Q3: Retention > 90 days for compliance AND no S3 export?
  ├── YES → STEP 4 (Firehose → S3 / Glacier) — 94% cheaper long-term
  └── NO  → Q4
  │
  Q4: CloudWatch agent batch_count at default (1000)?
  ├── YES → STEP 3 (increase to 10000) — 10x fewer PutLogEvents requests
  └── NO  → Q5
  │
  Q5: Subscription filters fanning out to another CW Logs group?
  ├── YES → STEP 5 (redirect to Firehose) — eliminates double ingestion ($1.00/GB)
  └── NO  → Q6
  │
  Q6: Vended logs (VPC Flow / Route53) to CW Logs at > 10 GB/day?
  ├── YES → STEP 6 (redirect to S3) — eliminates $0.50/GB ingestion
  └── NO  → All dimensions checked → emit OPTIMIZED
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` with `Monthly
   saving: $0.00`.** If every dimension nets zero cost delta, the verdict
   MUST be `OPTIMIZED`. A cost-neutral compliance improvement is surfaced
   in REASON, NOT as a dollar saving.

2. **NEVER show savings math that does not balance.**
   `Current monthly − Projected monthly` MUST equal `Monthly saving`,
   rounded to 2 decimal places.

3. **NEVER emit scratch lines** ("WAIT — recompute", "Hmm, let me redo",
   "corrected:") in the output. Finalize the math before emitting.

4. **NEVER recommend a retention change without citing the current
   `RetentionInDays` and `StoredBytes`.** The REASON MUST name the data
   source (describe-log-groups, Cost Explorer).

5. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all seven dimensions, each marked
   ✓ (no finding) or → (finding).

6. **NEVER present a Firehose S3 export recommendation without including
   the Firehose + S3 cost in the Projected monthly.** Omitting these
   inflates the apparent saving.

7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE with verified math

Every field below is internally consistent. Copy this shape exactly.
The scenario: a 500 GB/month application log group with Never-expire
retention has accumulated 6,000 GB over 12 months. Retention to 30
days caps storage at 500 GB steady-state (91.7% storage cost cut).
Two orphaned subscription filters waste $250/month in double ingestion.
A Firehose S3 export provides a compliance archive.

```text
TARGET: /app/payment-service-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Application log group with Never-expire retention has accumulated
  6,000 GB over 12 months at $0.03/GB-month ($180.00/month storage and
  growing). Two orphaned subscription filters deliver to a decommissioned
  Lambda account, adding $250.00/month in double-ingestion charges.
  Retention to 30 days caps storage at 500 GB steady-state ($15.00/month,
  91.7% storage reduction). A Firehose S3 export provides a compliance
  archive at $26.00/month (Firehose + S3 Standard).
RECOMMENDATION:
  Current: Never expire, 500 GB/month ingested, 6,000 GB stored, 0 Insights queries/month,
           agent batch_count 10000, 2 subscription filters (orphaned)
  Proposed: 30 days, 500 GB/month ingested, 500 GB stored (steady), 0 Insights queries/month,
            agent batch_count 10000, 0 subscription filters (cleaned up),
            Firehose S3 export for compliance archive
  Dimensions changed: retention (Step 1) + subscription (Step 5) + cold-storage (Step 4)
  Dimensions checked: retention → (Never to 30d)  queries ✓ (none to convert)
    agent ✓ (batch_count already 10000)  cold-storage → (add Firehose S3 export)
    subscription → (2 orphaned filters removed)  destination ✓ (app logs, not vended)
    data-protection ✓ (no PII fields detected)
  Confidence: HIGH — describe-log-groups confirms RetentionInDays absent and
    storedBytes=6,000 GB; describe-subscription-filters confirms 2 filters pointing
    to arn:aws:lambda:us-east-1:999988887777:function:log-shipper (decommissioned).
ESTIMATED_SAVINGS:
  Current monthly: $680.00
    ingestion: 500 GB x $0.50 = $250.00
    storage: 6,000 GB x $0.03 = $180.00
    subscription double-ingestion: 500 GB x $0.50 = $250.00 (orphaned Lambda dest)
    insights: 0 queries = $0.00
  Projected monthly: $291.00
    ingestion: 500 GB x $0.50 = $250.00 (unchanged — retention does not reduce ingestion)
    storage: 500 GB x $0.03 = $15.00 (steady-state at 30-day retention)
    Firehose delivery: 500 GB x $0.029 = $14.50 (compliance archive to S3)
    S3 Standard storage: 500 GB x $0.023 = $11.50 (first 90 days; lifecycle to GIR after)
    subscription: $0.00 (orphaned filters removed)
    insights: $0.00
  Monthly saving: $389.00 ($680.00 − $291.00)
  Annual saving: $4,668.00
  Storage-only savings: $180.00 → $15.00 = 91.7% reduction
MIGRATION_STEPS:
  1. Create Firehose delivery stream to S3 for compliance archive:
     aws firehose create-delivery-stream --delivery-stream-name payment-log-archive \
       --s3-destination-configuration \
       RoleARN=arn:aws:iam::444455556666:role/firehose-s3-role,\
       BucketARN=arn:aws:s3:::payment-log-archive-bucket,\
       Prefix=logs/,BufferingSize=5,BufferingInterval=300
  2. Verify Firehose stream is ACTIVE before proceeding:
     aws firehose describe-delivery-stream --delivery-stream-name payment-log-archive
  3. Remove orphaned subscription filters (decommissioned Lambda destination):
     aws logs delete-subscription-filter --log-group-name /app/payment-service-prod \
       --filter-name log-shipper-lambda
     aws logs delete-subscription-filter --log-group-name /app/payment-service-prod \
       --filter-name log-shipper-lambda-v2
  4. Set retention to 30 days (deletes logs older than 30d within hours):
     aws logs put-retention-policy --log-group-name /app/payment-service-prod \
       --retention-in-days 30
  5. Verify retention applied + subscription filters removed:
     aws logs describe-log-groups --log-group-name-prefix /app/payment-service-prod
     aws logs describe-subscription-filters --log-group-name /app/payment-service-prod
CONFIRM: About to put-retention-policy on /app/payment-service-prod
  (Never → 30 days). This will delete 5,500 GB of logs older than 30 days
  within hours. Firehose S3 export configured for compliance archive.
  Saving $389.00/month (57.2%). Storage alone: 91.7% reduction.
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
| `OPTIMIZED` | All dimensions pass (retention at compliance minimum, no query waste, cold storage in S3 where applicable). Also emitted when a change was applied and verified this session. |
| `NEED_MORE_INFO` | Data gate failed: metrics absent, window < 14 days, or Cost Explorer data unavailable with no CloudWatch fallback. |
| `BLOCKED` | Hard precondition prevents evaluation: log group in a different account without cross-account role, IAM denies logs:DescribeLogGroups. |

**Zero-savings rule:** If MONTHLY_SAVING == $0.00 for every dimension,
verdict MUST be `OPTIMIZED`, never `FURTHER_OPTIMIZATION_AVAILABLE`.
Exception: a compliance improvement (e.g., data protection policy) with
no cost change is surfaced in REASON, not as dollar savings.

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend a retention change without verifying compliance
   requirements.** Reducing retention below a regulatory minimum (e.g.,
   SOX 7-year, HIPAA 6-year) can create legal liability. Always confirm
   the log group is not subject to a retention mandate before recommending
   a reduction.

2. **NEVER convert a Logs Insights query to a metric filter without
   verifying the query pattern is expressible in metric filter syntax.**
   Metric filters support a limited pattern language. Complex queries
   with multiple aggregations, regex, or joins cannot be converted —
   forcing them produces incorrect metrics.

3. **NEVER reduce CloudWatch Logs retention without first confirming a
   cold-storage copy exists OR the data is safe to delete.** Retention
   reduction is irreversible — deleted log events cannot be recovered.
   For compliance logs, always configure Firehose → S3 BEFORE reducing
   CW Logs retention.

4. **NEVER increase agent `batch_count` without warning the operator
   about the data-loss exposure on agent failure.** Larger batches mean
   more events in-flight at any moment. For mission-critical logs,
   balance cost savings against acceptable data-loss window.

5. **NEVER recommend redirecting VPC Flow Logs to S3 without confirming
   the team's query workflow can move to Athena.** Teams relying on Logs
   Insights for real-time VPC Flow Log queries will lose that capability
   when logs move to S3-only delivery. Surface the workflow change.

Extended anti-patterns in `references/cloudwatch-logs-pricing-and-retention.md`.

## Pre-flight safety checks (run before any remediation CLI)

Pre-flight safety checks (CONFIRM gate, retention-deletes-data warning, metric-filter immediacy, Firehose activation wait, subscription-filter downstream consumers, masking scope, agent restart, VPC Flow non-retroactivity, 10-group batch limit) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before executing any remediation CLI.

## Recent AWS features (2024-2026)

Recent AWS features (2024-2026) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when choosing between data-protection policies, Firehose delivery, S3 Tables, or the Graviton agent.

## References

- `references/cloudwatch-logs-pricing-and-retention.md` — pricing tables,
  retention tier matrix, Firehose cost math, metric filter syntax
  reference, vended log destination comparison, regional pricing
  multipliers, cost calculation worked examples.
- `references/worked-examples.md` — full worked examples (retention
  sweep, Insights-to-metric-filter migration, Firehose cold-storage
  pipeline, agent buffer tuning, already-optimized, NEED_MORE_INFO,
  end-to-end walkthrough).

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Mindset principles, Step 0 non-obvious behaviours, step rationale/nuance prose, data-quality short-circuits, and Recent AWS features (2024-2026) moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — data-gate data sources, step CLI listings (retention sweep, metric filter, agent config, Firehose, data protection), and pre-flight safety checks moved from SKILL.md
- [references/worked-examples.md](references/worked-examples.md) — now also holds step cost math (Insights estimation, buffer savings, cold-storage comparison, impact formula) and the minimal output template moved from SKILL.md
- [references/cloudwatch-logs-pricing-and-retention.md](references/cloudwatch-logs-pricing-and-retention.md) — pricing tables, retention tiers, regional multipliers (pre-existing)

## Domain

AWS CloudOps / CloudWatch Logs Cost Optimization & FinOps.

## AWS documentation

- **Amazon CloudWatch Logs User Guide** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html
- **CloudWatch Logs pricing** — https://aws.amazon.com/cloudwatch/pricing/
- **CloudWatch Logs retention** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html#SettingLogRetention
- **CloudWatch Logs Insights** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html
- **CloudWatch Logs metric filters** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html
- **CloudWatch Logs subscription filters** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Subscriptions.html
- **CloudWatch agent configuration** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-Configuration-File-Details.html
- **Kinesis Data Firehose** — https://docs.aws.amazon.com/firehose/latest/dev/what-is-this-service.html
- **VPC Flow Logs** — https://docs.aws.amazon.com/vpc/latest/flow-logs/flow-logs-cwl.html
- **CloudWatch Logs data protection** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/data-protection.html
- **AWS CLI Logs reference** — https://docs.aws.amazon.com/cli/latest/reference/logs/
- **Well-Architected Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
