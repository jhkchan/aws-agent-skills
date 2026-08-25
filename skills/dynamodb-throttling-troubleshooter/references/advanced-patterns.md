# Advanced Patterns (load on demand) — DynamoDB Throttling Troubleshooter

Step-0 expert behaviors, edge cases, deep-dive guidance, and 2024-2026 feature changes, moved verbatim from SKILL.md.


---

## Mindset — three facts that differentiate DynamoDB throttling diagnosis (moved from SKILL.md)

Three facts make DynamoDB throttling diagnosis different from generic
database capacity debugging:

- **A throttle does not always mean "raise capacity."** DynamoDB throttles
  for six different reasons: hot partition, GSI hot key, sustained
  provisioned-capacity breach, burst exhaustion, adaptive capacity lag,
  and scan/batch misuse. Raising capacity fixes only two of these. Hot
  partition and GSI hot key require a key redesign. Scan misuse requires
  switching to query. Misdiagnosing any of these wastes spend without
  resolving the throttle.

- **GSI throttling propagates to the base table.** A GSI shares the
  table's provisioned capacity pool in provisioned mode. A hot GSI can
  throttle writes to the base table even when the base table's own
  capacity is ample. Operators who debug "the table is throttled" without
  checking per-GSI metrics miss that the cause is the GSI, not the table.

- **Intermittent throttling is almost always burst capacity exhaustion.**
  DynamoDB retains up to 5 minutes of unused burst capacity (up to 300
  seconds). When traffic is spiky, the burst absorbs the spikes — until it
  does not. The symptom is "works fine for 5 minutes, then throttles,"
  which operators misdiagnose as "the capacity is fine, it must be a
  DynamoDB outage." The fix is sustained capacity above the average rate,
  not on-demand.

---

## Step 2: Common fix patterns (READ_CAPACITY_LOW) (moved from SKILL.md)

**Common fix patterns:**

- Sustained read traffic above provisioned: raise `ProvisionedReadCapacityUnits`
  via `update-table`, OR switch to on-demand (`BillingMode: PAY_PER_REQUEST`).
- Scan misuse: replace Scan with Query on the partition key; see Step 7.
- Strongly consistent reads where eventually consistent suffices: switch to
  eventually consistent to halve RCU consumption.
- Large items: consider compressing or splitting items; each 4 KB chunk is
  a separate RCU.

---

## Step 3: Common fix patterns (WRITE_CAPACITY_LOW) (moved from SKILL.md)

**Common fix patterns:**

- Sustained write traffic above provisioned: raise
  `ProvisionedWriteCapacityUnits`, OR switch to on-demand.
- GSI replication cost: audit each GSI for necessity; delete GSIs that are
  no longer queried. Each GSI removed reduces WCU cost by 1x per item.
- Transactional writes where standard writes suffice: switch to standard
  `PutItem` / `UpdateItem` to halve WCU cost.

---

## Step 4: Common fix patterns (GSI_HOT_KEY) (moved from SKILL.md)

**Common fix patterns:**

- GSI provisioned too low (reads): raise the GSI's
  `ProvisionedReadCapacityUnits` independently of the base table.
- GSI hot key (writes): redesign the GSI partition key. Add a random
  suffix or a composite component to spread writes across partitions. If
  the access pattern is "find all items with status=ACTIVE," consider a
  sparse GSI that only includes active items.
- Switch the table to on-demand: on-demand mode removes GSI provisioned
  capacity entirely; the GSI auto-scales with query load. This is the
  fastest fix when the GSI access pattern cannot be redesigned quickly.

---

## Step 5: Common fix patterns (BURST_EXHAUSTED) (moved from SKILL.md)

**Common fix patterns:**

- Raise sustained capacity above the average rate so burst is not needed.
  The rule of thumb: set provisioned capacity to the 99th percentile of
  the traffic rate, not the average. This keeps burst in reserve for true
  spikes.
- Switch to on-demand: on-demand mode absorbs spikes without burst budget
  (it bills per request). This is the simplest fix for spiky workloads
  where the average is well below the peak.
- Smooth the traffic at the application layer: batch writes, use a queue
  (SQS) to decouple producers from DynamoDB, or add client-side rate
  limiting.

---

## Step 6: Common fix patterns (HOT_PARTITION) (moved from SKILL.md)

**Common fix patterns:**

- **Add a random suffix to the partition key.** Append a 2-digit random
  number (`userId#04`) to spread writes across 100 partitions. Read
  queries must then fan out across all suffixes and merge — acceptable for
  write-heavy, read-light workloads.
- **Use a composite partition key.** Combine the hot attribute with a
  higher-cardinality attribute (e.g., `userId#orderId`) so writes
  distribute across partitions.
- **Switch to on-demand mode.** On-demand handles hot partitions without
  throttling (it scales per-partition). This is the fastest fix when the
  key cannot be redesigned immediately.
- **For "today" date keys:** use a write-sharding pattern with N shards
  per day (`2026-08-07#0` through `2026-08-07#99`). Reads query all N
  shards for today.

---

## Step 7: Common fix patterns (SCAN_MISUSE / BATCH_LIMIT) (moved from SKILL.md)

**Common fix patterns:**

- Replace Scan with Query: if the access pattern is "find items for user
  X," Query on the partition key `userId` instead of Scan with a filter.
- For analytics scans: use Parallel Scan with N workers (each scans a
  segment); or export the table to S3 via DynamoDB export and run
  analytics on S3 (Athena / Spark).
- For BatchGetItem: keep batches to 50-80 items (below the 100 limit) to
  leave headroom for retries. Always implement exponential backoff on
  `UnprocessedKeys`.
- For FilterExpression misuse: if the filter removes > 90% of scanned
  items, the access pattern is wrong — redesign the key schema so the
  filter becomes a KeyConditionExpression.

---

## Step 9: Verify the fix (moved from SKILL.md)

Before applying, validate the proposed fix:

- **For capacity changes (provisioned mode):** `update-table` applies
  within minutes. Monitor CloudWatch `ThrottledRequests` for 15 minutes
  after the change.
- **For on-demand switch:** `update-table --billing-mode PAY_PER_REQUEST`
  applies immediately. Verify `ThrottledRequests` drops to 0.
- **For key redesign:** this requires a data migration. Create a new table
  with the redesigned key, copy data via DynamoDB export/import or AWS
  Glue, and cut over the application. Verify the new key distribution with
  Contributor Insights before declaring the fix complete.
- **For GSI redesign:** GSIs can be added (`update-table`) but not
  modified in-place. Create a new GSI with the redesigned key, verify query
  patterns, then delete the old GSI.

---

## Remediation guidance (moved from SKILL.md)

### For HOT_PARTITION

1. Enable Contributor Insights to confirm the top partition key.
2. Short-term: switch to on-demand (immediate throttle relief).
3. Long-term: redesign the partition key:
   - Add a random suffix (write-sharding).
   - Use a composite key combining the hot attribute with a
     high-cardinality attribute.
4. Verify the new key distribution with Contributor Insights after
   migration.

### For GSI_HOT_KEY

1. Check per-GSI `ThrottledRequests` to confirm the GSI is the cause.
2. Short-term: raise the GSI's provisioned capacity (provisioned mode) or
   switch to on-demand.
3. Long-term: redesign the GSI partition key for higher cardinality.
4. Create a new GSI with the redesigned key, migrate queries, delete the
   old GSI.

### For READ_CAPACITY_LOW

1. Confirm sustained `ConsumedReadCapacityUnits` > provisioned at 1-min
   period.
2. Check for scan misuse (Step 7) before raising capacity.
3. Check read consistency: switch strongly-consistent reads to eventually
   consistent where possible (halves RCU cost).
4. Raise `ProvisionedReadCapacityUnits` or switch to on-demand.

### For WRITE_CAPACITY_LOW

1. Confirm sustained `ConsumedWriteCapacityUnits` > provisioned.
2. Audit GSIs: each GSI adds WCU cost. Remove unused GSIs.
3. Check for transactional writes: switch to standard writes where
   possible (halves WCU cost).
4. Raise `ProvisionedWriteCapacityUnits` or switch to on-demand.

### For BURST_EXHAUSTED

1. Confirm the spiky pattern at 1-min period (5-min period hides it).
2. Raise sustained capacity to the 99th percentile of per-second rate.
3. Or switch to on-demand (absorbs spikes without burst budget).
4. Or smooth traffic at the application layer (SQS queue, batch writes).

### For SCAN_MISUSE

1. Confirm Scan in CloudTrail correlates with throttle events.
2. Replace Scan with Query on the partition key.
3. For analytics: use Parallel Scan, or export to S3 via DynamoDB export
   and query with Athena.
4. For FilterExpression misuse: redesign the key schema so the filter
   becomes a KeyConditionExpression.

### For BATCH_LIMIT

1. Reduce batch size to 50-80 items (below the 100 limit).
2. Implement exponential backoff on `UnprocessedKeys` / `UnprocessedItems`.
3. Split large items across batches to stay under the 16 MB limit.

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **On-demand mode burst limit refinement (2024-2025):** On-mode mode now
  ramps per-partition capacity over 30 minutes from the previous peak. A
  sudden spike > 2x the previous peak on a single partition can still
  throttle. Troubleshoot via Contributor Insights, not capacity settings.
- **DynamoDB Contributor Insights enhanced (2024):** More granular
  per-GSI key visibility. Auditors should enable Contributor Insights on
  every table with GSIs for hot-key detection.
- **DynamoDB export to S3 (2024-2025 improvements):** Faster exports and
  incremental export support. Use exports to offload analytics workloads
  from the production table, eliminating Scan-induced throttling.
- **DynamoDB Streams + Kinesis Data Streams fan-out (2024):** Higher
  shard capacity for change-data-capture consumers. For high-throughput
  CDC, use Kinesis Data Streams (not just DynamoDB Streams) to decouple
  consumers and avoid read-throttling the table.
- **Amazon DynamoDB zero-ETL integration with OpenSearch (2025):**
  Enables search analytics without scanning DynamoDB. Eliminates a common
  Scan-induced throttle pattern for search workloads.
- **Adaptive capacity improvements (2024-2025):** Faster partition
  rebalancing for moderately skewed keys. Severely skewed keys still
  require redesign.
