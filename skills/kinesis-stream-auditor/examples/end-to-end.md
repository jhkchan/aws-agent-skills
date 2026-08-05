# End-to-end usage scenario: kinesis-stream-auditor

A walkthrough showing the skill auditing a Kinesis Data Streams
configuration that has NO_ENCRYPTION (EncryptionType: NONE) compounded by
extended retention and missing monitoring — demonstrating the worst-verdict
aggregation, the retention-cost-coupling concept, and the ordered
remediation workflow.

## Input (user prompt)

> Review this Kinesis stream before we attach it to the production
> analytics pipeline. It ingests clickstream events at ~2 MB/s from
> our web application.

```yaml
StreamName: prod-clickstream-ingest
StreamStatus: ACTIVE
StreamMode: PROVISIONED
OpenShardCount: 4
RetentionPeriodHours: 720
EncryptionType: NONE
EnhancedMonitoring:
  - ShardLevelMetrics: [IncomingBytes, OutgoingBytes]
ConsumerCount: 2
```

## Skill output

```text
STREAM: prod-clickstream-ingest
VERDICT: NO_ENCRYPTION
REASON: EncryptionType is NONE — data at rest is plaintext (Step 1).
RetentionPeriodHours is 720 (30 days) on a 4-shard provisioned stream,
incurring extended-retention storage charges beyond the included 24-hour
window (Step 2). EnhancedMonitoring is missing IteratorAgeMilliseconds
and WriteProvisionedThroughputExceeded — cannot identify per-shard
consumer lag or write throttling (Step 3).
FINDINGS:
  - [NO_ENCRYPTION] EncryptionType: NONE — data at rest is not encrypted (Step 1)
  - [COST_RISK] RetentionPeriodHours: 720 exceeds 168h threshold — extended-retention charges apply per GB beyond 24h (Step 2)
  - [CONFIG_GAP] EnhancedMonitoring missing IteratorAgeMilliseconds — cannot identify per-shard consumer lag (Step 3)
  - [CONFIG_GAP] EnhancedMonitoring missing WriteProvisionedThroughputExceeded — cannot identify per-shard write throttling (Step 3)
  - [OK] ConsumerCount: 2 — consumers are attached
REMEDIATION:
  1. Enable KMS encryption: aws kinesis start-stream-encryption --stream-name prod-clickstream-ingest --encryption-type KMS --key-id alias/aws/kinesis
  2. Reduce retention: aws kinesis decrease-stream-retention-period --stream-name prod-clickstream-ingest --retention-period-hours 24
  3. Enable key metrics: aws kinesis enable-enhanced-monitoring --stream-name prod-clickstream-ingest --shard-level-metrics IteratorAgeMilliseconds WriteProvisionedThroughputExceeded
```

## Why the verdict is NO_ENCRYPTION

The skill's aggregation rule is: **worst verdict wins** with priority
NO_ENCRYPTION > COST_RISK > CONFIG_GAP > OK. Even though the retention
cost (720 hours on 4 shards) and the monitoring gap (missing
IteratorAgeMilliseconds and WriteProvisionedThroughputExceeded) are
actionable findings, plaintext data at rest is the highest-priority
exposure. The COST_RISK and CONFIG_GAP findings appear in the FINDINGS
list for visibility but do not override the verdict.

## Key D1 knowledge deltas applied

- **Retention cost is separate from shard cost.** The 720-hour retention
  generates per-GB charges beyond the included 24-hour window, independent
  of the per-shard-hour provisioned fee. The operator likely budgeted only
  the shard cost (~$44/month for 4 shards) and is unaware of the
  extended-retention line item.
- **Enhanced monitoring blind spot.** Without `IteratorAgeMilliseconds`
  per shard, the operator cannot identify which shard's consumer is
  lagging. Stream-level aggregate metrics hide the hot shard. At 2 MB/s
  ingest across 4 shards (500 KB/s/shard average), uneven partition-key
  distribution could put one shard near the 1 MB/s write limit with no
  visibility.
- **Encryption does not retroactively apply.** `StartStreamEncryption`
  encrypts only NEW records. Existing plaintext records remain readable
  in plaintext until they expire from the retention window.
