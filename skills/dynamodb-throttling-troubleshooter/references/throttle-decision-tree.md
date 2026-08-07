# DynamoDB Throttling Decision Tree — Reference

Supplementary reference for the DynamoDB Throttling Troubleshooter skill.
Walks the full symptom-to-cause tree with worked examples per category.

## Throttle categories and where each strikes

```
Application sees ProvisionedThroughputExceededException
  │
  ├── Read throttle (ConsumedReadCapacityUnits ≥ provisioned)
  │     ├── Sustained: genuine traffic  → READ_CAPACITY_LOW
  │     ├── Spiky after 5 min           → BURST_EXHAUSTED
  │     └── Scan / BatchGetItem spike   → SCAN_MISUSE / BATCH_LIMIT
  │
  ├── Write throttle (ConsumedWriteCapacityUnits ≥ provisioned)
  │     ├── Sustained: genuine traffic  → WRITE_CAPACITY_LOW
  │     ├── GSI replica cost inflation  → WRITE_CAPACITY_LOW (GSI-driven)
  │     └── Per-GSI ThrottledRequests   → GSI_HOT_KEY
  │
  ├── Throttling after scale-up (capacity raised, throttle persists)
  │     └── One partition dominates     → HOT_PARTITION / ADAPTIVE_LAG
  │
  └── On-demand throttle (> 2x previous peak on one partition)
        └── Sudden spike + skewed key   → HOT_PARTITION (on-demand variant)
```

The category letters map to the steps in SKILL.md:

- A = READ_CAPACITY_LOW (Step 2)
- B = WRITE_CAPACITY_LOW (Step 3)
- C = GSI_HOT_KEY (Step 4)
- D = BURST_EXHAUSTED (Step 5)
- E = HOT_PARTITION / ADAPTIVE_LAG (Step 6)
- F = SCAN_MISUSE / BATCH_LIMIT (Step 7)

**Rule:** pick the SPECIFIC cause over the AGGREGATE cause. If a GSI is
throttling and propagating to the base table, the cause is GSI_HOT_KEY,
not WRITE_CAPACITY_LOW. If a hot partition is exhausting burst, the cause
is HOT_PARTITION, not BURST_EXHAUSTED.

## Category A: READ_CAPACITY_LOW

### Worked example — genuine sustained read traffic

**Symptom:** `ConsumedReadCapacityUnits` sustained at 50,000; table
provisioned at 40,000 RCU. `ThrottledRequests` sustained > 0.

**Walk:**

1. `describe-table` shows `BillingMode: PROVISIONED`,
   `ReadCapacityUnits: 40000`.
2. CloudWatch `ConsumedReadCapacityUnits` (1-min period): sustained
   ~50,000 for the last hour.
3. CloudTrail: no `Scan` events; access pattern is `GetItem` and `Query`.
4. No GSIs with elevated `ThrottledRequests`.

**Root cause:** READ_CAPACITY_LOW — sustained traffic exceeds provisioned
(catalog #3).

**Fix:** raise `ReadCapacityUnits` or switch to on-demand:

```bash
aws dynamodb update-table --table-name <table> \
  --provisioned-throughput ReadCapacityUnits=60000,WriteCapacityUnits=10000
```

### Worked example — strongly consistent reads doubling cost

**Symptom:** `ConsumedReadCapacityUnits` is 2x the expected GetItem count.
Table provisioned at 10,000 RCU; application makes ~5,000 GetItem/sec.

**Walk:**

1. Expected RCU for 5,000 eventually-consistent GetItem/sec on 4 KB items:
   5,000 × 0.5 = 2,500 RCU/sec.
2. Actual: 5,000 RCU/sec — exactly 2x expected.
3. Application code: all `GetItem` calls use `ConsistentRead: true`.

**Root cause:** READ_CAPACITY_LOW — strongly consistent reads doubling
RCU cost (catalog #8 variant).

**Fix:** switch to eventually consistent reads where the application
tolerates it (halves RCU cost).

## Category B: WRITE_CAPACITY_LOW

### Worked example — GSI replica cost inflation

**Symptom:** Table provisioned at 10,000 WCU. Application writes 2,000
items/sec, each 1 KB. `ConsumedWriteCapacityUnits` is 8,000 — 4x the
expected 2,000.

**Walk:**

1. Expected WCU for 2,000 PutItem/sec on 1 KB items: 2,000 WCU/sec.
2. Actual: 8,000 WCU/sec — 4x expected.
3. `describe-table`: table has 3 GSIs.
4. Each GSI replicates the write: 1 (base) + 3 (GSIs) = 4x WCU per item.

**Root cause:** WRITE_CAPACITY_LOW — GSI replica cost inflation (catalog
#4 variant).

**Fix:** audit each GSI for necessity. Remove unused GSIs to reduce the
multiplier. If all GSIs are needed, raise WCU or switch to on-demand.

### Worked example — transactional writes

**Symptom:** `ConsumedWriteCapacityUnits` is 2x the expected write count.
Table has no GSIs.

**Walk:**

1. Expected WCU for 1,000 writes/sec on 1 KB items: 1,000 WCU/sec.
2. Actual: 2,000 WCU/sec.
3. Application uses `TransactWriteItems` for all writes.
4. Transactional writes cost 2x standard writes.

**Root cause:** WRITE_CAPACITY_LOW — transactional writes doubling WCU
cost (catalog #8).

**Fix:** switch to standard `PutItem` / `UpdateItem` where transactional
semantics are not required.

## Category C: GSI_HOT_KEY

### Worked example — status field GSI throttling base table

**Symptom:** Base table write `ThrottledRequests` sustained > 0. Base
table `ConsumedWriteCapacityUnits` is below provisioned. Raising base
table capacity does not help.

**Walk:**

1. `describe-table`: GSI "status-index" on partition key `status`.
2. Per-GSI `ThrottledRequests` (status-index): sustained > 0.
3. Per-GSI `ConsumedWriteCapacityUnits` (status-index): at GSI provisioned
   limit.
4. Contributor Insights: top GSI key "status=ACTIVE" = 60% of traffic.
5. `status` has only 4 distinct values.

**Root cause:** GSI_HOT_KEY — low-cardinality GSI partition key (catalog
#2).

**Fix:** redesign the GSI key (composite with a shard suffix), or switch
to on-demand for immediate relief.

### Worked example — GSI read throttle (no base table impact)

**Symptom:** `ThrottledRequests` on the GSI only, base table has 0
throttles. Query on the GSI fails intermittently.

**Walk:**

1. Per-GSI `ThrottledRequests` > 0; base table `ThrottledRequests` = 0.
2. GSI `ProvisionedReadCapacityUnits`: 5,000.
3. GSI `ConsumedReadCapacityUnits`: sustained 6,000.
4. The GSI's read capacity is independent of the base table in provisioned
   mode.

**Root cause:** GSI_HOT_KEY (read variant) — GSI read capacity too low.

**Fix:** raise the GSI's `ProvisionedReadCapacityUnits` independently.

## Category D: BURST_EXHAUSTED

### Worked example — batch writes every 2 minutes

**Symptom:** Throttling starts ~5 minutes after the first batch write.
Average WCU is below provisioned. Each batch is 12,000 WCU in 10 seconds;
provisioned is 5,000 WCU.

**Walk:**

1. `ConsumedWriteCapacityUnits` (1-min period): alternating 0 and 12,000
   datapoints.
2. `ThrottledRequests`: starts at minute 5, continues on every batch.
3. `ConsumedWriteCapacityUnits` (5-min avg): 4,000 — below the 5,000
   provisioned (misleading at coarse period).
4. DynamoDB burst budget: 5 minutes of unused capacity. After 2-3 batches,
   the burst is exhausted; subsequent batches throttle.

**Root cause:** BURST_EXHAUSTED — spiky traffic depleting burst budget
(catalog #5).

**Fix:** raise sustained capacity to the 99th percentile of per-second
rate (12,000 WCU), OR switch to on-demand, OR smooth traffic via SQS.

### Worked example — burst on a hot partition

**Symptom:** Same spiky pattern, but only one partition key value is
receiving the spikes. Other partitions are idle.

**Walk:**

1. Same burst pattern as above.
2. BUT Contributor Insights shows one partition key = 90% of traffic.
3. The burst budget is per-partition, not per-table. Only the hot
   partition's burst is exhausted; other partitions have spare burst.

**Root cause:** HOT_PARTITION (not BURST_EXHAUSTED). The fix is key
redistribution, not capacity.

**Fix:** redesign the partition key to spread writes. Raising capacity
helps marginally but does not resolve the skew.

## Category E: HOT_PARTITION / ADAPTIVE_LAG

### Worked example — status=ACTIVE hot partition

**Symptom:** Throttling persists after raising capacity from 10,000 to
50,000 WCU. `ConsumedWriteCapacityUnits` is only 8,000 (below provisioned).

**Walk:**

1. `describe-table`: `WriteCapacityUnits: 50000` (raised recently).
2. `ConsumedWriteCapacityUnits`: 8,000 — well below 50,000.
3. `ThrottledRequests`: sustained > 0 despite the headroom.
4. Contributor Insights: partition key "status=ACTIVE" = 80% of traffic.
5. The hot partition's adaptive capacity allocation lags behind the
   traffic spike.

**Root cause:** HOT_PARTITION — severely skewed partition key (catalog
#1).

**Fix:** redesign the partition key. Add a random suffix or composite
component. Short-term: switch to on-demand (handles per-partition scaling
without adaptive lag).

### Worked example — "today" date partition key

**Symptom:** Throttling every day at peak hours. Table works fine off-peak.

**Walk:**

1. Partition key is `date` (ISO format, e.g., `2026-08-07`).
2. All writes for "today" go to one partition.
3. At peak, that partition exceeds its share of table capacity.
4. Yesterday's partition and last week's partitions are idle.

**Root cause:** HOT_PARTITION — date-based partition key (catalog #1).

**Fix:** use a write-sharding pattern: `2026-08-07#0` through
`2026-08-07#99` (100 shards per day). Reads query all 100 shards for today
and merge.

## Category F: SCAN_MISUSE / BATCH_LIMIT

### Worked example — full-table scan throttling reads

**Symptom:** `ThrottledRequests` on reads spikes periodically. Average
`ConsumedReadCapacityUnits` is low. Table is 50 GB.

**Walk:**

1. CloudTrail: `Scan` events correlate with throttle spikes.
2. Each Scan reads the entire 50 GB table: ~6.4 million RCUs (eventually
   consistent).
3. Table provisioned at 10,000 RCU — the scan consumes the entire budget
   for ~640 seconds.
4. Application runs Scan for a dashboard report every 10 minutes.

**Root cause:** SCAN_MISUSE — full-table scan consuming all RCUs (catalog
#6).

**Fix:** replace Scan with Query (if the access pattern supports it), OR
export the table to S3 and run the dashboard query on S3 via Athena.

### Worked example — BatchGetItem exceeding 100 items

**Symptom:** `BatchGetItem` returns `ProvisionedThroughputExceededException`
with `UnprocessedKeys` populated. Table has spare capacity.

**Walk:**

1. Application sends `BatchGetItem` with 150 items in one request.
2. DynamoDB limit: 100 items per `BatchGetItem` request.
3. The request is rejected before capacity is evaluated.

**Root cause:** BATCH_LIMIT — batch exceeds 100 items (catalog #7).

**Fix:** split the batch into chunks of 50-80 items. Implement backoff on
`UnprocessedKeys`.

## Cross-category decision flowchart

```
START
  │
  ▼
Table in PROVISIONED or ON_DEMAND mode?
  ├── ON_DEMAND ──→ Is throttling on a single partition?
  │                   ├── YES ──→ HOT_PARTITION (on-demand variant)
  │                   └── NO  ──→ ESCALATE (AWS-side event)
  │
  ▼ PROVISIONED
Per-GSI ThrottledRequests > 0?
  ├── YES ──→ GSI_HOT_KEY
  │            ├── Low-cardinality GSI key → redesign GSI key
  │            └── GSI capacity too low → raise GSI capacity
  │
  ▼ NO
Partition key distribution uneven (Contributor Insights)?
  ├── YES ──→ HOT_PARTITION / ADAPTIVE_LAG
  │            └── Redesign partition key; on-demand short-term
  │
  ▼ NO
CloudTrail shows Scan / BatchGetItem correlating with throttles?
  ├── YES ──→ SCAN_MISUSE / BATCH_LIMIT
  │            ├── Scan → replace with Query
  │            └── Batch > 100 items → reduce batch size
  │
  ▼ NO
Consumed capacity sustained > provisioned at 1-min period?
  ├── YES ──→ READ/WRITE_CAPACITY_LOW
  │            ├── Genuine traffic → raise capacity / on-demand
  │            ├── GSI replica cost → remove unused GSIs
  │            └── Transactional → switch to standard
  │
  ▼ NO
Throttling after 5 min of spiky traffic, avg below provisioned?
  ├── YES ──→ BURST_EXHAUSTED
  │            └── Raise sustained to 99th percentile / on-demand
  │
  ▼
NEED_MORE_INFO — gather more context
```

## Common diagnostic shortcuts

- If write throttling persists after raising base table capacity, suspect
  GSI hot key first.
- If throttling correlates with a batch job or dashboard refresh, suspect
  scan misuse.
- If throttling only happens during peak hours on a date-based partition
  key, suspect hot partition.
- If throttling starts ~5 minutes after traffic spikes begin, suspect
  burst exhaustion.
- If on-demand mode throttles, suspect a hot partition exceeding 2x the
  previous peak — the fix is key distribution.
- If `ConsumedWriteCapacityUnits` = base writes × (1 + GSI count), the
  GSI replica cost is the driver.
