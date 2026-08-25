---
name: dynamodb-throttling-troubleshooter
description: Diagnoses DynamoDB ProvisionedThroughputExceededException and throttle events via a symptom-to-cause decision tree covering read throttling, write throttling, GSI hot-key throttling, burst capacity exhaustion, and adaptive capacity lag. Walks CloudWatch consumed vs provisioned capacity units, per-GSI metrics, partition key distribution, scan vs query patterns, and BatchGetItem/BatchWriteItem limits. Emits a deterministic verdict (ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE) with the specific throttle type and evidence from ConsumedReadCapacityUnits, ConsumedWriteCapacityUnits, ThrottledRequests, and ReturnConsumedCapacity. Use when DynamoDB returns throttle errors, CloudWatch shows ThrottledRequests > 0, or an application sees intermittent ProvisionedThroughputExceededException.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline diagnosis works from pasted CloudWatch metrics, error strings, and table/GSI metadata. Live-account diagnosis uses aws dynamodb describe-table, aws cloudwatch get-metric-statistics, aws dynamodb scan (with --select), and ReturnConsumedCapacity on API responses (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Databases
  task_type: troubleshoot
  skill_class: capability
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  lifecycle_status: active
  when_to_use: Diagnosing a DynamoDB ProvisionedThroughputExceededException, elevated ThrottledRequests in CloudWatch, intermittent throttle errors under spiky traffic, GSI-related table-wide throttling, or post-scale-up throttling from adaptive capacity lag; validating whether the root cause is hot partition, GSI hot key, insufficient provisioned capacity, burst exhaustion, scan misuse, or batch operation limits.
  when_not_to_use: DynamoDB table configuration posture audits (use dynamodb-table-auditor), IAM policy authoring for fine-grained access control (use iam-least-privilege-advisor), KMS key access for encrypted tables (use kms-key-policy-auditor), or DynamoDB Streams/Kinesis consumer lag diagnosis. This skill diagnoses throttling root cause; it does not audit table configuration posture.
  activation_triggers: DynamoDB ProvisionedThroughputExceededException, DynamoDB throttling, DynamoDB ThrottledRequests, DynamoDB hot partition, DynamoDB GSI throttling, DynamoDB burst capacity exhausted, DynamoDB request rate too high, DynamoDB write throttled, DynamoDB read throttled, DynamoDB intermittent throttling, DynamoDB adaptive capacity, troubleshoot DynamoDB throttling
  invocation_schema: 'Input: either (a) a symptom description (the throttle error string, the table name, observed CloudWatch metric pattern), optionally paired with describe-table output, OR (b) a table name plus caller context (access pattern, partition key distribution, recent traffic change) for live-account diagnosis. Output: a deterministic TABLE / VERDICT / ROOT_CAUSE / THROTTLE_TYPE / EVIDENCE / REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and THROTTLE_TYPE ∈ {HOT_PARTITION, GSI_HOT_KEY, READ_CAPACITY_LOW, WRITE_CAPACITY_LOW, BURST_EXHAUSTED, ADAPTIVE_LAG, SCAN_MISUSE, BATCH_LIMIT, ON_DEMAND_BREACH, UNKNOWN}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: DynamoDB, throttling, ProvisionedThroughputExceededException, ThrottledRequests, ConsumedReadCapacityUnits, ConsumedWriteCapacityUnits, hot partition, GSI hot key, burst capacity, adaptive capacity, partition key, scan, query, on-demand, provisioned capacity, RCU, WCU, BatchGetItem, BatchWriteItem, troubleshooting
  tags: dynamodb, databases, troubleshoot, throttling, capacity, hot-partition, gsi
---

# DynamoDB Throttling Troubleshooter

## Activation

Activate this skill when the user reports a DynamoDB throttling incident.
Trigger phrases: "DynamoDB ProvisionedThroughputExceededException",
"DynamoDB throttling", "DynamoDB ThrottledRequests", "DynamoDB hot
partition", "DynamoDB GSI throttling", "DynamoDB burst capacity
exhausted", "DynamoDB request rate too high", "DynamoDB write throttled",
"DynamoDB read throttled", "DynamoDB intermittent throttling",
"DynamoDB adaptive capacity", "troubleshoot DynamoDB throttling".

## Mindset

**One-line takeaway:** DynamoDB throttling has six distinct root causes
with different fixes, and the throttle error string alone is never enough
to distinguish them. The diagnostic walk combines CloudWatch metrics
(consumed vs provisioned), table/GSI metadata, partition key distribution,
and the access pattern (scan vs query vs batch) to pinpoint the cause.

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Quick reference — symptom to throttle type

| Observed signal | Throttle type | First probe |
|---|---|---|
| `ThrottledRequests` spikes correlate with one partition key value | HOT_PARTITION | CloudWatch per-partition (via contributor insights) + access pattern |
| `ThrottledRequests` on writes, base table capacity ample | GSI_HOT_KEY | Per-GSI `ThrottledRequests` metric; GSI key cardinality |
| Sustained `ConsumedWriteCapacityUnits` ≥ `ProvisionedWriteCapacityUnits` | WRITE_CAPACITY_LOW | CloudWatch consumed vs provisioned (1-min period) |
| Sustained `ConsumedReadCapacityUnits` ≥ `ProvisionedReadCapacityUnits` | READ_CAPACITY_LOW | CloudWatch consumed vs provisioned; check for scan |
| `ThrottledRequests` after ~5 min of spiky traffic, average below provisioned | BURST_EXHAUSTED | CloudWatch consumed vs provisioned at 1-min period; traffic variance |
| Throttling persists after a capacity scale-up | ADAPTIVE_LAG | Check partition-key distribution; adaptive capacity redirect lag |
| `ThrottledRequests` correlates with scan operations | SCAN_MISUSE | CloudTrail for `Scan` calls; `ConsumedReadCapacityUnits` spikes |
| `BatchGetItem` / `BatchWriteItem` exceeding 16 MB / 100 items | BATCH_LIMIT | CloudTrail for batch calls; ReturnConsumedCapacity |

See the ordered steps below for the full diagnostic walk.

## Process — Diagnostic decision tree (apply in order)

### Step 0: Capture the throttle signal

Before any deep walk, gather these three pieces. Each step below branches
on which is present.

| Signal | Source | Why required |
|---|---|---|
| **Table name + region** | User-provided or `aws dynamodb list-tables` | All CloudWatch and describe-table calls need this |
| **Throttle error string + CloudWatch pattern** | Application log + `aws cloudwatch get-metric-statistics` for `ThrottledRequests` | Drives the symptom category |
| **Table capacity mode + per-GSI capacity** | `aws dynamodb describe-table` | Distinguishes provisioned-mode throttle types from on-demand |

If the user has not provided the table name or region, output:

```text
TABLE: <table name or unknown>
VERDICT: NEED_MORE_INFO
REASON: Cannot diagnose without the table name and region. Identify the
  throttled table with the application's DynamoDB client config or
  CloudTrail for dynamodb:* API calls around the throttle window.
MISSING:
  - Table name + region
  - The throttle error string (ProvisionedThroughputExceededException,
    RequestLimitExceeded, etc.)
  - The CloudWatch ThrottledRequests pattern (spike vs sustained)
```

If the user reports "DynamoDB is throttling" but does not know which table
or which operation, ask for the application's DynamoDB client configuration
and the approximate time window. Then run:

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

### Step 1: Identify the symptom category

Map the observed state to one of six categories. Each category has a
different diagnostic walk in Steps 2-7.

| Category | Signature | Diagnostic step |
|---|---|---|
| **A. READ_CAPACITY_LOW** | Sustained `ConsumedReadCapacityUnits` ≥ `ProvisionedReadCapacityUnits`; `ThrottledRequests` on reads | Step 2 |
| **B. WRITE_CAPACITY_LOW** | Sustained `ConsumedWriteCapacityUnits` ≥ `ProvisionedWriteCapacityUnits`; `ThrottledRequests` on writes | Step 3 |
| **C. GSI_HOT_KEY** | Write throttling on the base table but base table consumed capacity is below provisioned; per-GSI `ThrottledRequests` > 0 | Step 4 |
| **D. BURST_EXHAUSTED** | Intermittent throttling after ~5 min of spiky traffic; average consumed capacity below provisioned | Step 5 |
| **E. ADAPTIVE_LAG / HOT_PARTITION** | Throttling persists after scale-up; uneven partition key distribution; one partition key value dominates traffic | Step 6 |
| **F. SCAN_MISUSE / BATCH_LIMIT** | `ThrottledRequests` correlates with `Scan` calls or `BatchGetItem` / `BatchWriteItem` exceeding limits | Step 7 |

If the symptom matches more than one category, prioritise: GSI_HOT_KEY
precedes HOT_PARTITION precedes SCAN_MISUSE precedes
READ/WRITE_CAPACITY_LOW precedes BURST_EXHAUSTED. A GSI hot key that
throttles the base table is the cause; the base-table capacity is the
consequence.

### Step 2: READ_CAPACITY_LOW diagnostic

Read throttling: `ConsumedReadCapacityUnits` sustained at or above
`ProvisionedReadCapacityUnits`. The first question is whether the read
volume is expected (genuine traffic) or unexpected (a scan consuming the
entire budget).

Moved verbatim to [references/capacity-math.md](references/capacity-math.md) - load on demand (see References below).

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

| Sub-symptom | Root cause | Probe |
|---|---|---|
| `ConsumedReadCapacityUnits` sustained > provisioned, no scan | Genuine traffic exceeds provisioned | Check application access pattern; raise provisioned or switch to on-demand |
| `ConsumedReadCapacityUnits` spikes to provisioned, then drops | Scan or BatchGetItem consuming budget | CloudTrail for `Scan` / `BatchGetItem` events; switch scan to query |
| `ConsumedReadCapacityUnits` doubled vs expected | Strongly consistent reads where eventually consistent would do, OR transactional reads | Check application read consistency flags |
| `ConsumedReadCapacityUnits` high but `GetItem` count low | Large items (> 4 KB) consuming multiple RCUs per read | `ReturnConsumedCapacity: TOTAL` on GetItem responses |

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 3: WRITE_CAPACITY_LOW diagnostic

Write throttling: `ConsumedWriteCapacityUnits` sustained at or above
`ProvisionedWriteCapacityUnits`. The first question is whether GSI
replication is inflating the WCU cost.

Moved verbatim to [references/capacity-math.md](references/capacity-math.md) - load on demand (see References below).

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

| Sub-symptom | Root cause | Probe |
|---|---|---|
| `ConsumedWriteCapacityUnits` sustained > provisioned, no GSI | Genuine write traffic exceeds provisioned | Raise provisioned or switch to on-demand |
| `ConsumedWriteCapacityUnits` = base write × (1 + GSI count) | GSI replication cost | Verify each GSI is needed; delete unused GSIs |
| `ThrottledRequests` on writes but `ConsumedWriteCapacityUnits` < provisioned | GSI hot key throttling (see Step 4) | Per-GSI metrics |
| WCU doubled vs expected | Transactional writes (`TransactWriteItems`) | Check application write path |

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 4: GSI_HOT_KEY diagnostic

A GSI has its own partition key. If that key is unevenly distributed (low
cardinality or one value dominating), the GSI's partitions become hot. In
provisioned mode, a hot GSI throttles — and that throttle propagates to
the base table write (because DynamoDB must update the GSI atomically with
the base item).

**This is the most-missed DynamoDB throttle cause.** Operators see
`ThrottledRequests` on the base table, raise base table capacity, and the
throttle persists — because the cause is the GSI, not the base table.

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

| Sub-symptom | Root cause | Probe |
|---|---|---|
| Per-GSI `ThrottledRequests` > 0, base table `ThrottledRequests` = 0 (reads) | GSI read throttle — GSI provisioned too low for query load | Raise GSI provisioned capacity (in provisioned mode); on-demand auto-scales |
| Base table write `ThrottledRequests` > 0, per-GSI `ThrottledRequests` > 0 on one GSI | GSI write throttle propagating to base table | Redesign the GSI partition key for higher cardinality |
| GSI partition key has < 100 distinct values | GSI hot key — low cardinality concentrates writes on few partitions | Add a suffix to the GSI key; or use a composite key |
| GSI partition key has high cardinality but one value dominates (e.g., "status=ACTIVE") | GSI hot key — skewed distribution | Redesign the access pattern; consider a different GSI |

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 5: BURST_EXHAUSTED diagnostic

DynamoDB retains up to 5 minutes (300 seconds) of unused burst capacity.
When traffic is spiky, the burst absorbs the spikes — until it runs out.
The signature is "works fine for 5 minutes, then throttles" with average
consumed capacity below provisioned.

**Diagnostic walk:**

1. **Confirm the burst pattern:** CloudWatch `ConsumedReadCapacityUnits`
   or `ConsumedWriteCapacityUnits` at 1-minute period shows spikes well
   above provisioned, but the 5-minute average is below provisioned.
2. **Check `ThrottledRequests` timing:** throttles cluster AFTER the burst
   is exhausted, not at the start of the spike. If throttles happen at the
   start, the cause is sustained capacity (Step 2/3), not burst.
3. **Verify the burst budget is real:** DynamoDB only grants burst for
   partitions that have unused capacity. A hot partition (Step 6) exhausts
   its burst faster because only one partition's unused capacity is
   available — not the whole table's. Distinguish burst exhaustion on a
   hot partition (fix: redesign key) from burst exhaustion on an even
   distribution (fix: raise sustained capacity).

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 6: ADAPTIVE_LAG / HOT_PARTITION diagnostic

DynamoDB partitions data by partition key. When one partition key value
receives disproportionate traffic, that partition becomes hot. DynamoDB's
adaptive capacity redirects traffic to other partitions — but there is a
lag (seconds to minutes). During the lag, throttling persists even after a
capacity scale-up, because the scale-up applies to the table's aggregate
capacity, not the hot partition's share.

**This is the "throttling after scale-up" pattern.** The operator raises
capacity, throttling continues, and they conclude "DynamoDB is broken." The
actual cause is the hot partition — the scale-up increased aggregate
capacity but the hot partition's allocation did not increase fast enough.

**Diagnostic walk:**

1. **Enable DynamoDB Contributor Insights** (if not already): this reveals
   the top partition key values by traffic volume.
2. **Check partition key cardinality:** a partition key with fewer than
   ~1000 distinct values is at risk of hot partitions. A key with one
   value dominating > 10% of traffic is a confirmed hot partition.
3. **Check the access pattern:** are all writes going to one key (e.g.,
   `status=ACTIVE`, `userId=admin`, `date=today`)? Common hot-key
   anti-patterns:
   - Status / category fields with few values as the partition key.
   - A "today" date as the partition key (all writes hit today's partition).
   - A user ID where one user (admin, bot, batch job) generates most traffic.
4. **Verify adaptive capacity is enabled** (it is on by default for all
   tables). The lag is inherent; the fix is key redesign, not disabling
   adaptive capacity.

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

| Sub-symptom | Root cause | Probe |
|---|---|---|
| Top partition key value > 10% of traffic | HOT_PARTITION — skewed key | Contributor insights; key distribution scan |
| Throttling persists after capacity scale-up | HOT_PARTITION — adaptive capacity lag | Verify scale-up applied; check partition distribution |
| Partition key is a date / status / category | HOT_PARTITION — low cardinality by design | Redesign the key |
| Partition key is high-cardinality but one value dominates | HOT_PARTITION — power-law distribution | Add a suffix to spread the hot key |

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 7: SCAN_MISUSE / BATCH_LIMIT diagnostic

Two operational patterns consume capacity disproportionately without
showing up as a sustained-capacity breach:

**Scan misuse:** a `Scan` operation reads the entire table (or segment).
For a 100 GB table, that is ~12.8 million RCUs (eventually consistent) —
enough to throttle a 100,000-RCU table for 128 seconds. Scans are the #1
cause of unexplained read throttling on tables with low average RCU
consumption.

**Batch limit:** `BatchGetItem` and `BatchWriteItem` have hard limits:
100 items per batch and 16 MB per batch. Exceeding these returns a
`ProvisionedThroughputExceededException` even when the table has spare
capacity. The error is not about table capacity — it is about the batch
size.

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

| Sub-symptom | Root cause | Probe |
|---|---|---|
| `ThrottledRequests` correlates with `Scan` in CloudTrail | SCAN_MISUSE — full-table scan consuming all RCUs | Replace Scan with Query; or use Parallel Scan for analytics |
| `BatchGetItem` returns `ProvisionedThroughputExceededException` with unprocessed keys | BATCH_LIMIT — batch exceeds 100 items or 16 MB | Reduce batch size; implement exponential backoff on `UnprocessedKeys` |
| `BatchWriteItem` throttle with `UnprocessedItems` | BATCH_LIMIT — same as above | Reduce batch size; backoff on `UnprocessedItems` |
| Scan with `FilterExpression` consuming all RCUs before filtering | SCAN_MISUSE — filter is applied AFTER read | Move the filter into the key schema (Query with KeyConditionExpression) |

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 8: Map to root-cause catalog

After the walk identifies the category, cross-reference with this catalog.

| # | Root cause | Category | Fix pattern |
|---|---|---|---|
| 1 | Hot partition key (skewed distribution) | HOT_PARTITION | Add random suffix; composite key; or on-demand |
| 2 | GSI hot key throttling propagating to base table | GSI_HOT_KEY | Redesign GSI key; raise GSI capacity; on-demand |
| 3 | Sustained read traffic above provisioned | READ_CAPACITY_LOW | Raise RCU; on-demand; reduce read consistency |
| 4 | Sustained write traffic above provisioned | WRITE_CAPACITY_LOW | Raise WCU; on-demand; remove unused GSIs |
| 5 | Burst capacity exhaustion on spiky traffic | BURST_EXHAUSTED | Raise sustained capacity to 99th percentile; on-demand; queue |
| 6 | Scan consuming all read capacity | SCAN_MISUSE | Replace Scan with Query; Parallel Scan; export to S3 |
| 7 | BatchGetItem / BatchWriteItem exceeding 100 items / 16 MB | BATCH_LIMIT | Reduce batch size; backoff on UnprocessedKeys |
| 8 | Transactional reads/writes doubling capacity cost | READ/WRITE_CAPACITY_LOW | Switch to standard consistency where possible |

### Step 9: Verify the fix

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 10: Decide — ROOT_CAUSE_FOUND vs NEED_MORE_INFO vs ESCALATE

- **ROOT_CAUSE_FOUND.** The walk identified a specific throttle type and a
  specific configuration element (capacity setting, partition key, GSI
  key, scan pattern). Output REMEDIATION with the exact change.
- **NEED_MORE_INFO.** The walk reached a step where the operator cannot
  supply evidence (e.g., Contributor Insights is not enabled, or the
  partition key distribution requires a full-table scan to measure).
  Output the list of missing inputs.
- **ESCALATE.** The walk identifies a cause outside the operator's scope:
  an AWS-side DynamoDB event, a table owned by another team, or a key
  redesign that requires application architecture changes. Output the
  escalation target and the specific request to make.

## Output format

```text
TABLE: <table name> in <region>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <throttle type name> — <specific root cause>
THROTTLE_TYPE: <HOT_PARTITION | GSI_HOT_KEY | READ_CAPACITY_LOW |
                WRITE_CAPACITY_LOW | BURST_EXHAUSTED | ADAPTIVE_LAG |
                SCAN_MISUSE | BATCH_LIMIT | ON_DEMAND_BREACH | UNKNOWN>
EVIDENCE:
  - <CloudWatch signal>: <metric and value>
  - <describe-table signal>: <field and value>
  - <access pattern signal>: <observation>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION:
  1. <specific config change with CLI command>
  2. <verification command>
  3. <post-apply monitoring>
```

### Worked example — GSI hot key throttling base table writes

```text
TABLE: orders-prod in us-east-1
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: GSI_HOT_KEY — the GSI "status-index" has partition key
  "status" with only 4 distinct values (PENDING, ACTIVE, SHIPPED,
  DELIVERED). 60% of writes have status=ACTIVE, concentrating on one
  GSI partition. The GSI throttles, which propagates to the base table
  write path.
THROTTLE_TYPE: GSI_HOT_KEY
EVIDENCE:
  - CloudWatch ThrottledRequests (base table, PutItem): sustained > 0
    for the last 30 minutes
  - CloudWatch ThrottledRequests (GSI status-index): sustained > 0,
    correlated with base table throttles
  - CloudWatch ConsumedWriteCapacityUnits (base table): 8,000 WCU/min,
    below the 10,000 WCU/min provisioned — base table capacity is ample
  - describe-table: GSI status-index KeySchema [{AttributeName: status,
    KeyType: HASH}]
  - Contributor Insights: top key "status=ACTIVE" accounts for 60% of
    GSI traffic
ROOT_CAUSE_CATALOG: #2 (GSI hot key)
REMEDIATION:
  1. Immediate: switch the table to on-demand to stop the throttling:
     aws dynamodb update-table --table-name orders-prod \
       --billing-mode PAY_PER_REQUEST
  2. Permanent: redesign the GSI partition key to a composite of
     status + orderId hash suffix:
     - Create a new GSI "status-shard-index" with partition key
       "statusShard" (= status + "#" + (orderId % 10))
     - Update the application to populate statusShard on writes
     - Query the new GSI with all 10 shards and merge (fan-out read)
     - Delete the old "status-index" GSI
  3. Monitor CloudWatch ThrottledRequests for 15 minutes after the
     on-demand switch; expect 0 throttles.
```

### Worked example — burst capacity exhaustion

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

## Diagnostic command reference

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

## Anti-Patterns — NEVER

- NEVER assume `ProvisionedThroughputExceededException` means "raise
  capacity." Six different root causes produce this error. Raising
  capacity fixes only two (sustained read/write breach). Hot partition,
  GSI hot key, burst exhaustion, and scan misuse require different fixes.

- NEVER diagnose write throttling without checking per-GSI metrics. A GSI
  hot key throttles the base table write path in provisioned mode.
  Operators who debug "the table is throttled" without checking per-GSI
  metrics miss the cause and raise base table capacity to no effect.

- NEVER recommend raising capacity for a hot partition without verifying
  the partition key distribution. Adaptive capacity redirects within
  seconds to minutes, but a severely skewed key cannot be fixed by
  aggregate capacity — the hot partition's share does not scale linearly.

- NEVER recommend Scan as an access pattern for a production table. Scan
  reads every item; for any table over 1 GB, Scan is a throttle vector.
  Use Query for key-based access; use Parallel Scan or S3 export for
  analytics.

- NEVER set provisioned capacity to the average traffic rate for spiky
  workloads. The burst budget absorbs spikes for up to 5 minutes; beyond
  that, throttling resumes. Set provisioned to the 99th percentile, or
  switch to on-demand.

- NEVER ignore `UnprocessedKeys` in `BatchGetItem` or `UnprocessedItems`
  in `BatchWriteItem` responses. These fields indicate throttled items
  that must be retried. Dropping them silently causes data loss.

- NEVER switch a production table to on-demand without checking the cost
  implications. On-demand bills per request (~3x the provisioned rate at
  sustained load). For steady-state high-throughput tables, provisioned
  mode is cheaper. Use on-demand for spiky or unpredictable workloads.

- NEVER leave transactional reads/writes (`TransactWriteItems`,
  `TransactGetItems`) in place if standard consistency suffices.
  Transactional operations cost 2x the standard capacity. Audit the
  application's transaction usage periodically.

- NEVER assume on-demand mode eliminates all throttling. On-demand has a
  per-partition burst limit (2x the previous peak, ramped over 30
  minutes). A sudden spike > 2x the previous peak on a single partition
  can still throttle. The fix is key distribution, not capacity.

- NEVER redesign a partition key without planning the read path. Adding a
  random suffix to spread writes means reads must fan out across all
  suffixes and merge. If reads cannot tolerate fan-out, the suffix
  approach is wrong — use a composite key or a different access pattern.

- NEVER delete a GSI without verifying no application depends on it. GSI
  deletion is immediate and irreversible. Capture the GSI's query pattern
  in the application code before deletion.

## Remediation guidance

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## References

See `references/throttle-decision-tree.md` for the full symptom-to-cause
walk with worked examples per category, and `references/capacity-math.md`
for the RCU/WCU consumption formulas and cost multipliers.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Mindset deep-dive facts, per-step common fix patterns, Step 9 fix verification, remediation guidance, and 2024-2026 feature changes moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 0 account-wide throttle scan, Steps 2-7 per-category diagnostic commands, and the consolidated diagnostic command reference moved from SKILL.md
- [references/worked-examples.md](references/worked-examples.md) — burst capacity exhaustion worked example moved from SKILL.md
- [references/capacity-math.md](references/capacity-math.md) — RCU and WCU consumption math tables plus the GSI WCU cost multiplier moved from SKILL.md (extends the existing capacity math reference)

## Domain

AWS CloudOps / DynamoDB Capacity, Partitioning, and Throughput Reliability.

## AWS documentation

- **Amazon DynamoDB Developer Guide** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Welcome.html
- **DynamoDB throughput capacity** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadWriteCapacityMode.html
- **DynamoDB error handling** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Programming.Errors.html
- **DynamoDB best practices for tables** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html
- **DynamoDB Contributor Insights** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/contributorinsights.html
- **DynamoDB CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/dynamodb/
