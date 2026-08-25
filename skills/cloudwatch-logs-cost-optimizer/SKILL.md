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

CloudWatch Logs cost optimization is a volume-and-retention exercise,
not a performance tuning problem. The goal is to ingest only the bytes
that have operational or compliance value, retain them only as long as
required, and move long-term archives to the cheapest compatible tier
(S3 lifecycle-managed storage instead of CloudWatch Logs storage).

Four principles guide every recommendation:

- **Ingestion is the dominant cost term.** At $0.50/GB ingested, every
  GB avoided is $0.50 saved permanently (plus the downstream storage
  multiplier over the retention window). Filter at the source (agent
  level, log level) rather than at the destination.
- **Retention multiplies ingestion cost.** A GB ingested and retained
  for 90 days costs $0.50 (ingest) + $0.09 (3 months × $0.03) = $0.59.
  Retained for 3 years it costs $0.50 + $1.08 = $1.58 — over 3x the
  ingestion cost. Tight retention is the second-highest lever.
- **Cold storage belongs in S3, not CloudWatch Logs.** S3 Standard is
  $0.023/GB-month vs CloudWatch Logs storage at $0.03/GB-month. With
  S3 lifecycle policies (Glacier Instant Retrieval at $0.012/GB-month,
  Deep Archive at $0.00099/GB-month), long-term log archival in S3 is
  30-100x cheaper than CloudWatch Logs retention beyond 90 days.
- **Query patterns are a hidden cost.** Logs Insights at $0.005/GB
  scanned compounds rapidly: a daily dashboard query scanning 200 GB
  costs $36.50/month. Metric filters — which compute the same values
  at ingestion time for free — eliminate this entirely.

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

Optimization decisions are only as good as the underlying data. Pull
these metrics before any recommendation. Full CLI sequences are in
`references/cloudwatch-logs-pricing-and-retention.md`.

**Required data sources** (summarized — see reference for full CLI):
1. Log group configuration + retention: `aws logs describe-log-groups`
2. Ingestion volume (14-30 day window): `aws cloudwatch get-metric-statistics --namespace AWS/Logs --metric-name IncomingBytes`
3. PutLogEvents request count: `aws cloudwatch get-metric-statistics --namespace AWS/Logs --metric-name IncomingLogEvents`
4. Metric filters: `aws logs describe-metric-filters --log-group-name <name>`
5. Subscription filters: `aws logs describe-subscription-filters --log-group-name <name>`
6. Logs Insights query volume (CloudTrail): `aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=StartQuery`
7. Cost Explorer breakdown: `aws ce get-cost-and-usage --service AmazonCloudWatch`

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `IncomingBytes` metric absent (log group never received data) | **NEED_MORE_INFO**. Verify agent/SDK wiring; skip until ingestion exists. |
| `IncomingBytes` Sum = 0 over 14 days | Emit **OPTIMIZED** with note "dormant log group." |
| Observation window < 14 days | **NEED_MORE_INFO**. Minimum 14 days; 30 days preferred. |
| `StoredBytes` absent or stale | Fall back to `IncomingBytes × retention_days` estimate; mark retention finding MEDIUM confidence. |
| Cost Explorer `AmazonCloudWatch` usage type breakdown absent | Proceed with metric-based estimate; mark dollar figure MEDIUM confidence. |
| CloudTrail `StartQuery` events absent for Logs Insights analysis | Cannot assess query cost; skip Step 2, surface as data gap. |

When CloudWatch metrics and Cost Explorer disagree, Cost Explorer is the
ground truth for actual charges — metrics inform the optimization lever,
Cost Explorer confirms the dollar impact.

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

These billing-model and operational gotchas route a recommendation away
from the obvious choice:

- **`RetentionInDays = 0` means Never expire, not 0 days.** This is the
  single most common misunderstanding. A value of 0 (or the field
  absent) means logs are retained forever. Always check for this in
  `describe-log-groups` output.
- **Retention changes are NOT retroactive for already-deleted events but
  ARE retroactive for existing stored logs.** Setting retention from
  Never to 30 days will delete logs older than 30 days within hours.
  This is desired for cost savings but can surprise operators expecting
  a "going forward only" change.
- **Logs Insights charges per GB SCANNED, not per GB returned.** A query
  with `filter` after `stats` still scans the full log group for the
  time window. Push filters early in the query pipeline.
- **Metric filters are free but compute at ingestion time.** A metric
  filter extracts values as logs arrive — no scan cost. Tradeoff: limited
  syntax (CWL metric filter pattern language). Complex aggregations may
  still require Insights.
- **Embedded Metric Format (EMF) is free for metric extraction but the
  log event itself still incurs ingestion + storage cost.** EMF does not
  reduce Logs spend — it adds structured metrics without PutMetricData.
- **PutLogEvents charges per request, not per event.** The CloudWatch
  agent and SDKs batch events. Default agent `batch_count` = 1000 and
  `batch_size` = 1,048,576 bytes. Increasing `batch_count` to 10000
  reduces PutLogEvents requests by 10x, saving $0.40 per million
  requests eliminated.
- **Firehose delivery to S3 incurs its own charges** ($0.029/GB plus
  S3 storage) but is far cheaper than CloudWatch Logs retention beyond
  ~60 days. The crossover: CloudWatch Logs storage ($0.03/GB-month) +
  ongoing ingestion ($0.50/GB) vs Firehose ($0.029/GB one-time delivery)
  + S3 Standard ($0.023/GB-month). For retention > 90 days, S3 wins.
- **VPC Flow Logs to CloudWatch Logs incurs ingestion + storage.**
  Direct-to-S3 delivery (via Firehose or the native `DeliverLogsPermissionArn`
  to S3) avoids the $0.50/GB ingestion fee entirely. For high-volume
  VPC Flow Logs, S3 is almost always the right destination.
- **Subscription filters fan out at ingestion cost.** Each subscription
  filter delivers a COPY of the log events to its destination (Lambda,
  Kinesis, Firehose). The destination's ingestion is billed separately.
  Cross-account aggregation via subscription filters doubles the
  effective ingestion cost if the destination is another CloudWatch
  Logs group.
- **Account-level data protection policies mask PII at ingestion.** This
  reduces stored bytes (masked fields are shorter) and reduces risk,
  but does NOT reduce ingestion cost (the full event is received before
  masking). The saving is on storage and downstream query processing.

### Step 1: Log group retention (the #1 lever)

Retention is the primary cost lever because CloudWatch Logs storage
accumulates at $0.03/GB-month with no automatic cap. Never-expire
groups are the dominant source of unintended spend.

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

**The retention sweep CLI:**
```bash
# List all log groups with Never expire (RetentionInDays absent or null)
aws logs describe-log-groups --output json | \
  jq '.logGroups[] | select(.retentionInDays == null or .retentionInDays == 0) |
      {logGroupName, storedBytes}'

# Set retention to 30 days
aws logs put-retention-policy \
  --log-group-name /aws/lambda/order-processor-prod \
  --retention-in-days 30
```

**Decision gate after retention audit:**

| Current retention | StoredBytes | Verdict | Action |
|---|---|---|---|
| Never expire (0) | > 50 GB | **FURTHER_OPTIMIZATION_AVAILABLE** | Set to compliance minimum (30-90 days) |
| Never expire (0) | < 5 GB | **FURTHER_OPTIMIZATION_AVAILABLE** (low priority) | Set to 30 days; small absolute saving |
| 90+ days AND not compliance-mandated | > 100 GB | **FURTHER_OPTIMIZATION_AVAILABLE** | Reduce to 30 days OR export to S3 (Step 4) |
| 7-30 days | Any | Retention OK | Proceed to other dimensions |
| 365+ days AND compliance-mandated | Any | Proceed to Step 4 (cold storage) | S3 export is the lever |

### Step 2: Logs Insights queries vs metric filters

Logs Insights charges $0.005 per GB scanned. Frequent queries on large
log groups are a hidden cost center. Metric filters extract the same
time-series values at ingestion time for free.

**When to migrate a query to a metric filter:**

| Query pattern | Metric filter candidate? | Action |
|---|---|---|
| `filter @message like /ERROR/ \| stats count() by bin(1min)` | YES — count of ERROR messages per minute | Create metric filter with pattern `ERROR` |
| `stats avg(duration) by bin(5min)` where duration is a JSON field | YES — EMF or metric filter on JSON value | Use metric filter with JSON extraction |
| `sort @timestamp desc \| limit 20` (latest 20 errors) | NO — ad-hoc exploration | Keep as Insights query; it scans minimal data with tight time window |
| `filter @message like /timeout/ \| stats count()` run hourly | YES — scheduled aggregation | Metric filter counting timeout occurrences |
| Complex multi-line query with joins/regex | NO — exceeds filter syntax | Keep as Insights; consider precomputing via EMF |

**Logs Insights cost estimation:**
```
insights_monthly_cost = queries_per_month × avg_GB_scanned_per_query × $0.005

Example: 450 queries/month × 120 GB/query × $0.005 = $270.00/month
         Converting to 5 metric filters: $0.00/month (metric filters are free)
         Net saving: $270.00/month
```

**Creating a metric filter:**
```bash
aws logs put-metric-filter \
  --log-group-name /aws/lambda/order-processor-prod \
  --filter-name ErrorCount \
  --filter-pattern '"ERROR"' \
  --metric-transformations \
    metricName=ErrorCount,metricNamespace=AppMetrics,metricValue=1,defaultValue=0
```

### Step 3: CloudWatch agent buffer tuning

The CloudWatch agent batches log events before calling PutLogEvents.
PutLogEvents charges $0.40 per million requests. Default agent settings
(`batch_count` = 1000, `batch_size` = 1,048,576 bytes) generate excess
requests on high-volume hosts.

**Agent configuration (JSON snippet):**
```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/app/application.log",
            "log_group_name": "/app/application",
            "log_stream_name": "{instance_id}",
            "retention_in_days": 30
          }
        ]
      }
    },
    "log_stream_name": "{instance_id}",
    "batch_count": 10000,
    "batch_size": 1048576,
    "batch_wait_time": 60
  }
}
```

| Parameter | Default | Recommended (high-volume) | Effect |
|---|---|---|---|
| `batch_count` | 1000 | 10000 | 10x fewer PutLogEvents requests |
| `batch_size` | 1,048,576 (1 MB) | 1,048,576 (max) | Already at max; do not reduce |
| `batch_wait_time` | 5 (seconds, not in older configs) | 30-60 | Longer wait allows larger batches |

**PutLogEvents request saving from buffer tuning:**
```
old_requests = log_events_per_hour / old_batch_count
new_requests = log_events_per_hour / new_batch_count
monthly_saving = (old_requests - new_requests) × 730 × $0.40/1,000,000

Example: 12M events/hour, batch_count 1000 → 10000:
  old_requests: 12,000/hour; new_requests: 1,200/hour
  Monthly saving: (12,000 - 1,200) × 730 × $0.40/1M = $3.16/host/month
  For a fleet of 100 hosts: $316/month
```

Caveat: larger batches increase the risk of losing buffered events if
the agent crashes. For mission-critical logs, balance batch_count against
acceptable data-loss exposure. The tradeoff: 10x cost reduction vs up to
60 seconds of buffered data at risk on agent failure.

### Step 4: Firehose S3 export for cold storage (compliance archives)

For log groups requiring long retention (180+ days) for compliance
(SOC2, HIPAA, PCI-DSS, financial regulations), CloudWatch Logs storage
is the wrong tier. Firehose delivers to S3, where lifecycle policies
provide 30-100x cheaper long-term storage.

**Architecture: Log source → Firehose → S3 (with lifecycle to Glacier)**

**Cost comparison (500 GB/month ingested, 2-year retention):**
```
CloudWatch Logs only:
  Ingestion:   500 GB × $0.50 = $250.00/month
  Storage:     500 × 24 months × $0.03 = $360.00/month (grows over time)
  Total at 24 months: ~$610/month → $14,640 over 2 years

Firehose → S3 (Glacier Instant Retrieval after 90 days):
  Firehose:    500 GB × $0.029 = $14.50/month
  S3 Standard:  500 GB × $0.023 = $11.50/month (first 90 days)
  S3 GIR:       500 GB × $0.012 = $6.00/month (after 90 days)
  Athena (queries on demand): ~$5.00/month
  Total steady-state: ~$37/month → $888 over 2 years
  Saving: $13,752 over 2 years (94% reduction)
```

**Firehose delivery stream for log archival:**
```bash
aws firehose create-delivery-stream \
  --delivery-stream-name log-archive-stream \
  --s3-destination-configuration \
    RoleARN=arn:aws:iam::<acct>:role/firehose-s3-role,\
    BucketARN=arn:aws:s3:::log-archive-bucket,\
    Prefix=logs/,!BufferingSize=5,!BufferingInterval=300
```

**Decision gate for cold storage migration:**

| Retention requirement | Current destination | Recommendation |
|---|---|---|
| 7-30 days | CloudWatch Logs | Keep in CW Logs (operational queries need speed) |
| 31-90 days | CloudWatch Logs | Keep in CW Logs if queried weekly; otherwise dual-write to S3 |
| 91-365 days | CloudWatch Logs | **Migrate to S3 via Firehose; reduce CW Logs retention to 30 days** |
| 365+ days (compliance) | CloudWatch Logs | **Migrate to S3 + Glacier lifecycle; CW Logs retention 0-7 days** |

### Step 5: Subscription filter and cross-account aggregation

Subscription filters deliver log events to Lambda, Kinesis Data Streams,
or Firehose for cross-account or cross-region aggregation. Each
subscription filter destination incurs its own ingestion/processing cost.

**Cost-aware aggregation patterns:**

| Pattern | Cost | When to use |
|---|---|---|
| CW Logs → subscription filter → Firehose → S3 (central bucket) | Firehose + S3 only | Cheapest cross-account archive |
| CW Logs → subscription filter → Lambda → another CW Logs group | Double ingestion ($1.00/GB) | Avoid for high-volume logs; use Firehose instead |
| CW Logs → subscription filter → Kinesis Data Streams | Kinesis shard cost + ingestion | Real-time processing pipeline |
| VPC Flow Logs → directly to S3 (no CW Logs) | S3 only ($0.023/GB-month) | Best for pure archival |

**Subscription filter anti-pattern — double ingestion:** If a subscription
filter delivers to a Lambda that writes to ANOTHER CloudWatch Logs group,
the events are ingested TWICE ($1.00/GB total). Use Firehose as the
destination for cross-account aggregation, not another CW Logs group.

### Step 6: Vended log destinations (VPC Flow Logs, Route53 Resolver)

Vended log sources (VPC Flow Logs, Route53 Resolver query logs, WAF
logs) can publish directly to S3, bypassing CloudWatch Logs entirely.
This eliminates the $0.50/GB ingestion fee.

**VPC Flow Logs destination decision:**

| Requirement | Destination | Cost |
|---|---|---|
| Real-time querying via Logs Insights | CloudWatch Logs | $0.50/GB ingest + $0.03/GB-month storage |
| Post-hoc querying via Athena | S3 (via Firehose or direct) | $0.023/GB-month + Athena scan cost |
| Compliance archive only | S3 → Glacier | $0.012/GB-month (GIR) or $0.00099 (Deep Archive) |

For VPC Flow Logs above ~10 GB/day, S3 is almost always cheaper than
CloudWatch Logs. Route53 Resolver query logs are high-volume and rarely
queried in real time — default to S3 delivery, use Athena when needed.

### Step 7: Account-level data protection policy (PII reduction)

Account-level data protection policies mask sensitive data (PII, credit
card numbers, API keys) in CloudWatch Logs at ingestion time. This
reduces stored bytes (masked fields are shorter) and reduces risk.

**Cost nuance:** Data protection policies do NOT reduce ingestion cost
— the full event is received before masking. The saving is on storage
(masked fields use fewer bytes) and on reducing the blast radius of
accidental PII logging.

**When to enable data protection:** Application logs with known PII fields
(user emails, phone numbers), services handling payment data (PCI scope
reduction), or audit logs that may capture sensitive headers.

**CLI to create a data protection policy:**
```bash
aws logs put-account-policy \
  --policy-name pii-protection-policy \
  --policy-type DATA_PROTECTION_POLICY \
  --policy-document '{
    "Name": "pii-protection",
    "Version": "2021-08-01",
    "Identifiers": [
      {"Type": "EmailAddress"},
      {"Type": "Phone"},
      {"Type": "CreditCard"}
    ],
    "DeletionProtection": false
  }'
```

### Step 8: Impact estimation

Compute the monthly savings for each recommendation:

```
current_monthly_cost =
  (monthly_ingested_GB × $0.50)
  + (monthly_stored_GB × $0.03)
  + (monthly_putlogevents_requests / 1M × $0.40)
  + (monthly_insights_GB_scanned × $0.005)

projected_monthly_cost =
  (projected_ingested_GB × $0.50)
  + (projected_stored_GB × $0.03)
  + (projected_putlogevents_requests / 1M × $0.40)
  + (projected_insights_GB_scanned × $0.005)
  + (firehose_GB × $0.029 if S3 export added)
  + (s3_stored_GB × $0.023 if S3 export added)

monthly_saving = current_monthly_cost - projected_monthly_cost
```

Always state assumptions: monthly ingestion volume, current vs projected
retention, Logs Insights query volume, pricing region, agent fleet size.

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

```text
TARGET: <log-group-name or account-level>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <retention> days, <ingested GB>/month, <Insights queries>/month, <agent batch_count>
  Proposed: <retention> days, <ingested GB>/month, <Insights queries>/month, <agent batch_count>
  Dimensions changed: <retention | queries | agent | cold-storage | subscription | destination | data-protection>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
  Assumptions: <list (ingestion volume, pricing region, etc.)>
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <log-group-name> in <region>.
  Proceed? (yes/no)"
```

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

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Retention changes delete data.** Setting retention from Never to 30
  days will delete logs older than 30 days within hours. Confirm the
  operator has verified no compliance or investigation need for older
  logs.
- **Metric filter creation is immediate.** Filters start processing new
  log events within seconds. Historical events are NOT backfilled.
- **Firehose delivery stream takes 5-10 minutes to become active.**
  Verify the stream is `ACTIVE` before relying on it for log delivery.
- **Subscription filter changes can break downstream consumers.**
  Removing a subscription filter stops delivery to Lambda/Kinesis. Verify
  no downstream service depends on the filter before modifying.
- **Data protection policy changes apply to NEW log events only.** Existing
  stored events are not retroactively masked.
- **Agent buffer changes require agent restart.** Update the agent config
  file, then `systemctl restart amazon-cloudwatch-agent`. Existing log
  streams are not interrupted.
- **VPC Flow Log destination changes are not retroactive.** New logs go
  to the new destination; existing logs remain in the old destination
  until their retention expires.
- **Bulk-operation limit:** Process at most 10 log groups per batch.
  Sort by `StoredBytes` (largest first), verify each batch before
  proceeding. Abort if any log group shows a spike in errors or missing
  data post-change.

## Recent AWS features (2024-2026)

- **Account-level data protection policy (2024 GA):** Masks PII at
  ingestion across all log groups in the account.
- **CloudWatch Logs Insights query optimization (2024-2025):** Query
  engine improvements reduce scan volume for well-structured queries.
- **VPC Flow Logs to S3 via Firehose (2024):** Native delivery to S3
  without a Lambda intermediary, eliminating processing cost.
- **CloudWatch Logs subscription filter to Firehose (enhanced 2024):**
  Direct subscription to Firehose without a Lambda intermediary.
- **S3 Tables for log analytics (2025):** Iceberg-backed tables in S3
  for structured log data. Cheaper than Athena-on-raw-S3 for recurring
  analytical queries.
- **CloudWatch Logs batch ingestion throughput improvements (2025):**
  Higher PutLogEvents throughput per stream; reduces throttling.
- **Graviton-based CloudWatch agent (2024):** Lower CPU usage on
  Graviton instances for the same log throughput.

## References

- `references/cloudwatch-logs-pricing-and-retention.md` — pricing tables,
  retention tier matrix, Firehose cost math, metric filter syntax
  reference, vended log destination comparison, regional pricing
  multipliers, cost calculation worked examples.
- `references/worked-examples.md` — full worked examples (retention
  sweep, Insights-to-metric-filter migration, Firehose cold-storage
  pipeline, agent buffer tuning, already-optimized, NEED_MORE_INFO,
  end-to-end walkthrough).

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
