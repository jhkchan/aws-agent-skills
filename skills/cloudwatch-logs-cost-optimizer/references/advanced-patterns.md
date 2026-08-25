# Advanced Patterns (load on demand) — CloudWatch Logs Cost Optimizer

Mindset principles, Step 0 non-obvious billing behaviours, step rationale and nuance prose, the data-quality short-circuit table, and recent AWS feature notes moved verbatim from SKILL.md. Loaded on demand.

---

## Mindset (moved from SKILL.md)

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
---

## Step 0: Non-obvious behaviours that change the recommendation (moved from SKILL.md)

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
---

## Pre-flight data-quality short-circuits (moved from SKILL.md)

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `IncomingBytes` metric absent (log group never received data) | **NEED_MORE_INFO**. Verify agent/SDK wiring; skip until ingestion exists. |
| `IncomingBytes` Sum = 0 over 14 days | Emit **OPTIMIZED** with note "dormant log group." |
| Observation window < 14 days | **NEED_MORE_INFO**. Minimum 14 days; 30 days preferred. |
| `StoredBytes` absent or stale | Fall back to `IncomingBytes × retention_days` estimate; mark retention finding MEDIUM confidence. |
| Cost Explorer `AmazonCloudWatch` usage type breakdown absent | Proceed with metric-based estimate; mark dollar figure MEDIUM confidence. |
| CloudTrail `StartQuery` events absent for Logs Insights analysis | Cannot assess query cost; skip Step 2, surface as data gap. |
---

## Step rationale and nuance prose (moved from SKILL.md)

**Step 1 — retention rationale:**

Retention is the primary cost lever because CloudWatch Logs storage
accumulates at $0.03/GB-month with no automatic cap. Never-expire
groups are the dominant source of unintended spend.

**Step 2 — query-vs-filter rationale:**

Logs Insights charges $0.005 per GB scanned. Frequent queries on large
log groups are a hidden cost center. Metric filters extract the same
time-series values at ingestion time for free.

**Step 3 — buffer-tuning rationale:**

The CloudWatch agent batches log events before calling PutLogEvents.
PutLogEvents charges $0.40 per million requests. Default agent settings
(`batch_count` = 1000, `batch_size` = 1,048,576 bytes) generate excess
requests on high-volume hosts.

**Step 3 — data-loss caveat:**

Caveat: larger batches increase the risk of losing buffered events if
the agent crashes. For mission-critical logs, balance batch_count against
acceptable data-loss exposure. The tradeoff: 10x cost reduction vs up to
60 seconds of buffered data at risk on agent failure.

**Step 4 — cold-storage rationale and architecture:**

For log groups requiring long retention (180+ days) for compliance
(SOC2, HIPAA, PCI-DSS, financial regulations), CloudWatch Logs storage
is the wrong tier. Firehose delivers to S3, where lifecycle policies
provide 30-100x cheaper long-term storage.

**Architecture: Log source → Firehose → S3 (with lifecycle to Glacier)**

**Step 5 — aggregation rationale:**

Subscription filters deliver log events to Lambda, Kinesis Data Streams,
or Firehose for cross-account or cross-region aggregation. Each
subscription filter destination incurs its own ingestion/processing cost.

**Step 5 — double-ingestion anti-pattern:**

**Subscription filter anti-pattern — double ingestion:** If a subscription
filter delivers to a Lambda that writes to ANOTHER CloudWatch Logs group,
the events are ingested TWICE ($1.00/GB total). Use Firehose as the
destination for cross-account aggregation, not another CW Logs group.

**Step 6 — vended-destination rationale:**

Vended log sources (VPC Flow Logs, Route53 Resolver query logs, WAF
logs) can publish directly to S3, bypassing CloudWatch Logs entirely.
This eliminates the $0.50/GB ingestion fee.

**Step 6 — S3 guidance:**

For VPC Flow Logs above ~10 GB/day, S3 is almost always cheaper than
CloudWatch Logs. Route53 Resolver query logs are high-volume and rarely
queried in real time — default to S3 delivery, use Athena when needed.

**Step 7 — data-protection rationale and cost nuance:**

Account-level data protection policies mask sensitive data (PII, credit
card numbers, API keys) in CloudWatch Logs at ingestion time. This
reduces stored bytes (masked fields are shorter) and reduces risk.

**Cost nuance:** Data protection policies do NOT reduce ingestion cost
— the full event is received before masking. The saving is on storage
(masked fields use fewer bytes) and on reducing the blast radius of
accidental PII logging.

**Step 7 — when to enable:**

**When to enable data protection:** Application logs with known PII fields
(user emails, phone numbers), services handling payment data (PCI scope
reduction), or audit logs that may capture sensitive headers.
---

## Recent AWS features (2024-2026) (moved from SKILL.md)

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
