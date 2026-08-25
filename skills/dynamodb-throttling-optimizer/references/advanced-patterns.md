# Advanced Patterns (load on demand) — DynamoDB Throttling Optimizer

Step-0 expert behaviors, edge cases, deep-dive guidance, and 2024-2026 feature changes, moved verbatim from SKILL.md.


---

## Mindset — five principles (moved from SKILL.md)

Throttling optimization is a distribution problem, not a capacity
problem. The goal is the partition-key distribution and write pattern
that minimizes throttling events while preserving the cost envelope --
not simply increasing provisioned throughput to brute-force past the
issue.

Five principles guide every recommendation:

- **Throttling is per-partition, not per-table.** DynamoDB allocates
  throughput proportionally across partitions. A hot partition can
  throttle even when table-level consumed capacity is below provisioned.
  CloudWatch `ThrottledRequests` with a `TableName` dimension shows
  table-level throttling; partition-level diagnosis requires CloudTrail
  or the table's partition key distribution analysis.
- **Burst capacity absorbs intermittent spikes.** DynamoDB accumulates
  up to 300 seconds of unused provisioned throughput as a burst bucket.
  Spikes that fit within the burst window (short duration, within
  accumulated capacity) do NOT throttle. Sustained spikes exhaust burst
  and throttle.
- **Adaptive capacity is reactive, not preventive.** It temporarily
  moves unused capacity from cold partitions to hot ones. This delays
  throttling but does not eliminate it. For sustained hot partitions,
  write sharding is the only durable fix.
- **GSI throttling back-pressures the base table.** If a GSI's partition
  key is hot, the GSI throttles and the base table write also throttles
  (GSI backpressure). GSI partition key design is as important as base
  table partition key design.
- **On-demand mode eliminates provisioned-throughput throttling.** In
  on-demand mode, DynamoDB instantly allocates capacity for any
  sustained throughput up to the previous peak (2x previous peak for
  sudden spikes). On-demand is more expensive but eliminates
  ProvisionedThroughputExceededException for most workloads.

---

## Step 0: Non-obvious behaviours that change the recommendation (moved from SKILL.md)

- **Burst capacity is NOT infinite.** DynamoDB accumulates up to 300
  seconds of unused provisioned throughput. A spike of 5x provisioned
  for 60 seconds uses 240 seconds of burst (4x60=240). Sustained spikes
  beyond 5 minutes exhaust burst and throttle.
- **Adaptive capacity has a delay.** It activates within seconds of a
  hot partition but the redistribution is temporary (minutes). It does
  not fix sustained hot partitions.
- **GSI backpressure throttles the base table.** If a GSI's partition
  key is hot, writes to the base table throttle even if the base table
  partition key is well-distributed. Always check GSI partition key
  distribution.
- **On-demand has a 2x spike limit.** On-demand instantly doubles the
  previous-peak sustained throughput. A sudden 10x spike beyond previous
  peak can still throttle. For extreme spikes, provisioned with
  auto-scaling headroom may be needed.
- **BatchWriteItem consumes WCU per item, not per request.** 16 items
  in one BatchWriteItem consume the same total WCU as 16 PutItem calls.
  The savings are in request count, network overhead, and client-side
  latency -- not in consumed capacity.
- **Conditional writes reduce wasted capacity.** A conditional
  `PutItem` with `attribute_not_exists(pk)` costs 1 WCU regardless of
  whether the condition matches. If it fails (item exists), the write
  is rejected -- saving downstream processing but not WCU.
- **TTL deletions consume WCU.** TTL-expired items are deleted
  asynchronously, consuming background WCU. Large TTL batches can cause
  throttling on provisioned tables. Stagger TTL or use on-demand.
- **Write sharding changes the partition key.** Adding a random suffix
  (e.g., `user_id#01` through `user_id#10`) spreads writes across 10
  partitions. Reads must aggregate across all suffixes. This is a
  read-write trade-off.
- **DynamoDB Streams can help diagnose throttling.** The stream records
  all writes in near-real-time. Analyzing stream records for write
  patterns can reveal hot partition keys.
- **ProvisionedThroughputExceededException is client-side.** The SDK
  retries automatically with exponential backoff by default, but custom
  retry logic (with jitter) is more effective for sustained throttling.

---

## Expert heuristic (moved from SKILL.md)

DynamoDB throttling optimization follows a clear priority: write
sharding for high-cardinality hot keys (adding a random suffix to the
partition key spreads writes across N partitions, eliminating per-
partition throttling even when the logical key is the same), burst
capacity (the 300-second window absorbs intermittent spikes -- if
throttling only occurs during brief bursts, the table is operating at
the edge of its burst budget, not necessarily under-provisioned), and
adaptive capacity (automatically redirects unused throughput from cold
partitions to hot ones within seconds, but this is a reactive safety net
and not a substitute for proper partition-key design -- sustained hot
partitions will eventually exhaust adaptive capacity and throttle
regardless).

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **On-demand capacity mode (revised pricing 2024):** Charges per
  request for both read and write. Instant 2x spike capacity beyond
  previous peak.
- **Adaptive capacity (GA since 2019):** Automatic redistribution within
  seconds. No configuration needed.
- **Burst capacity (revised 2024):** 300-second burst bucket. Clearly
  visible in CloudWatch as `BurstCapacityBalance`.
- **DynamoDB Streams enhanced (2024):** Near-real-time write records for
  hot-partition diagnosis.
- **GSI backfill improvements (2025):** Faster GSI creation with
  throttled backfill rate (avoids base-table throttling during creation).
- **CloudTrail Insights for DynamoDB (2025):** Automatic detection of
  unusual write patterns that indicate hot partitions.
