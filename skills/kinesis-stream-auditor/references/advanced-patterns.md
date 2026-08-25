# Advanced Patterns — Kinesis Stream Auditor

Step-0 expert-knowledge deep dives, edge-case handling, the Kinesis Data Streams internals deep reference, and recent AWS features moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Step 0: Expert knowledge — non-obvious Kinesis behaviors that change classification (moved from SKILL.md)

These behaviors are easy to misjudge without operational Kinesis experience.
Each changes a verdict if ignored:

- **Retention cost is billed SEPARATELY from shard cost.** The per-shard-hour
  fee (~$0.015/hr in us-east-1 = ~$11/shard/month) covers the shard's compute
  capacity for 24 hours of retention. Each hour beyond 24 incurs an
  ADDITIONAL extended-retention charge per GB of data stored. A 10-shard
  stream at 1 MB/s/shard (10 MB/s = 864 GB/day) with 720-hour (30-day)
  retention stores ~25 TB of extended-retention data — the retention fee can
  EXCEED the shard fee. Always evaluate retention as an independent cost
  dimension.

- **On-demand per-stream-hour floor.** On-demand mode charges
  ~$0.04/stream-hour (~$29/month) plus per-GB-ingested and per-GB-retrieved
  fees, REGARDLESS of data volume. A stream ingesting 50 MB/day costs ~$30/month
  in on-demand mode vs ~$11/month for a 1-shard provisioned stream at the same
  volume. The crossover: below ~200 MB/day of ingest, provisioned is cheaper;
  above ~1 GB/day with bursty patterns, on-demand is cheaper. A steady-state
  high-throughput workload is ALWAYS cheaper on provisioned.

- **Classic consumers SHARE 2 MB/s read throughput per shard.** All consumers
  using `GetRecords` (polling) compete for a single 2 MB/s read budget per
  shard. Three classic consumers on one shard each get ~0.67 MB/s. Enhanced
  fan-out consumers (`RegisterStreamConsumer`) get 2 MB/s EACH, independently.
  The threshold: if `ConsumerCount > 2` and no enhanced fan-out consumers are
  registered, read throughput is the bottleneck — flag as CONFIG_GAP.

- **WriteProvisionedThroughputExceeded is per-SHARD, not per-stream.** Write
  throttling is enforced at the shard level (1 MB/s or 1,000 records/s per
  shard). A 4-shard stream with uneven partition-key distribution can throttle
  on one shard while three are idle. The fix is a better partition key
  strategy, not more shards. Without `WriteProvisionedThroughputExceeded` in
  enhanced monitoring, you cannot identify WHICH shard is throttling.

- **Shard quota is account-region, not per-stream.** The default
  per-account-per-region quota for provisioned shards is 500 (Service Quotas:
  "Shards per Region"). A single stream with 450 shards leaves only 50 for
  ALL other streams. On-demand streams do NOT count against this quota (they
  have a separate 50-stream-per-region on-demand quota). Always evaluate
  shard count against the account-level quota, not in isolation.

- **UpdateShardCount blocks during UPDATING.** Resharding
  (`UpdateShardCount` or `SplitShard`/`MergeShards`) transitions the stream to
  `UPDATING` state. No further resharding calls are accepted until the stream
  returns to `ACTIVE` (seconds to minutes). `UpdateShardCount` can scale up to
  10x per call; multiple calls are needed for large jumps. A stream stuck in
  `UPDATING` for more than a few minutes indicates a stuck reshard — contact
  AWS support.

- **Encryption switch is NOT a one-way door, but it has quirks.** You CAN
  switch from `NONE` to `KMS` (`StartStreamEncryption`) and from `KMS` back
  to `NONE` (`StopStreamEncryption`). However, switching the KMS KEY requires
  `StopStreamEncryption` then `StartStreamEncryption` with the new key — there
  is no direct "update key" API. During the transition, the stream is in
  `UPDATING` state. Existing records are re-encrypted lazily on read, not
  retroactively.

- **AWS-managed key (`alias/aws/kinesis`) is shared and non-customizable.**
  This key is used by ALL Kinesis streams in the account that select
  `EncryptionType: KMS` without specifying a CMK. Its key policy is managed by
  AWS — you CANNOT add conditions, restrict principals, or enable
  customer-managed rotation scheduling. For compliance frameworks requiring
  customer-controlled key policies (PCI-DSS 3.4, HIPAA, FedRAMP), a
  customer-managed CMK is mandatory. Flag the AWS-managed key as a compliance
  note, not a hard finding — encryption IS present, just not customer-governed.

- **IteratorAgeMilliseconds approaching retention = silent data loss.** If
  `GetRecords.IteratorAgeMilliseconds` (stream-level, always available without
  enhanced monitoring) approaches `RetentionPeriodHours * 3,600,000`, the
  consumer is falling behind and records will expire from the retention window
  before being read. This is a silent data-loss path that does NOT trigger any
  CloudWatch alarm by default. An alarm on `GetRecords.IteratorAgeMilliseconds
  > RetentionPeriodHours * 3,600,000 * 0.8` (80% of retention) is the
  standard defence.

- **Closed shards after resharding.** After `SplitShard` or `MergeShards`,
  parent shards are CLOSED (`SequenceNumberRange.EndingSequenceNumber` is set).
  Consumers reading from a closed shard receive no new data and must discover
  child shards via `ListShards`. The KCL (Kinesis Client Library) handles this
  automatically, but a custom consumer that does not call `ListShards` after
  detecting a closed shard will stall silently — appearing healthy while
  processing zero records.

- **Enhanced fan-out consumer limit: 20 per stream.** Each enhanced fan-out
  consumer gets dedicated 2 MB/s per shard. The default quota is 20 consumers
  per stream. Beyond 20, `RegisterStreamConsumer` fails with
  `LimitExceededException`. Do not recommend adding enhanced fan-out consumers
  indiscriminately on streams with many consumers.

- **On-demand cooldown after scale-up.** On-demand mode scales up immediately
  when a write is throttled, but does NOT scale down for 15 minutes after
  the last throttle. During bursty workloads, you pay for peak capacity during
  the cooldown even if traffic drops to near-zero. This makes on-demand
  expensive for spiky-but-low-volume workloads that burst frequently.

## Edge-case handling (moved from SKILL.md)

- **StreamStatus: UPDATING during audit.** If the stream is transitioning
  (resharding or encryption change), classify the metadata as-is — the
  post-transition state will differ. Emit a NOTE: "Stream is in UPDATING state
  (resharding or encryption change in progress). Re-audit after the stream
  returns to ACTIVE."

- **On-demand stream with high OpenShardCount.** On-demand mode manages shard
  count automatically. A high `OpenShardCount` on an on-demand stream reflects
  recent traffic, not a quota risk. Do NOT flag on-demand shard count against
  the 500-shard provisioned quota — on-demand streams have a separate quota.

- **RetentionPeriodHours = 24 (default).** 24 hours is the included retention
  — no extended-retention charges. This is OK for the cost dimension.

- **RetentionPeriodHours < 24.** Rare but valid for cost-sensitive workloads
  where consumers read within minutes. No cost finding. Note: lowering below
  24h requires `DecreaseStreamRetentionPeriod` and is bounded by the current
  minimum (1 hour).

- **EnhancedMonitoring with ALL metrics.** Some operators enable all
  shard-level metrics on large streams. The CloudWatch cost scales with
  shard_count x metric_count. For a 100-shard stream with 8 metrics, that is
  800 custom metrics/month (~$40 in CloudWatch charges). Not a verdict driver
  but note if shard count is high.

- **EncryptionType: KMS but KeyId is empty or null.** This indicates a
  malformed configuration — KMS encryption requires a KeyId. Treat as
  CONFIG_GAP: "EncryptionType is KMS but KeyId is not specified — the stream
  cannot encrypt new records. Verify with describe-stream-summary."

## Deep reference: Kinesis Data Streams internals (moved from SKILL.md)

### Shard capacity and throughput math

Each provisioned shard provides:
- **Write:** 1 MB/sec OR 1,000 records/sec (whichever is hit first)
- **Read (classic):** 2 MB/sec shared across ALL `GetRecords` consumers on
  that shard, with a max of 5 `GetRecords` calls/sec per shard
- **Read (enhanced fan-out):** 2 MB/sec PER consumer, independently

On-demand mode provides capacity in units:
- Each on-demand unit = 10,000 records/sec write, 2 MB/sec write, 2 MB/sec
  read
- Default: 4 units (40,000 records/sec, 8 MB/sec write)
- Scales automatically; minimum after scale-down is 4 units (the floor)

### Resharding mechanics

`UpdateShardCount` (recommended for provisioned scaling):
- Can scale UP or DOWN
- Max scaling: 10x per call (can make multiple calls)
- Minimum target: 1 shard (absolute floor)
- Stream enters `UPDATING` state during the operation
- Existing shards are closed; new shards are created
- Consumers must discover child shards via `ListShards`

`SplitShard` / `MergeShards` (manual resharding):
- `SplitShard`: splits one shard into two (doubles capacity for that hash key
  range)
- `MergeShards`: merges two adjacent shards into one (halves capacity)
- More granular than `UpdateShardCount` but requires hash-key-range knowledge
- Both transition the stream to `UPDATING`

### Enhanced fan-out vs classic consumer throughput

| Aspect | Classic (GetRecords) | Enhanced Fan-Out (SubscribeToShard) |
|---|---|---|
| Throughput per consumer | Shared 2 MB/s/shard | Dedicated 2 MB/s/shard |
| Latency | Poll-interval (configurable, typically 1s) | ~70ms (HTTP/2 push) |
| Max consumers | Unlimited (but throughput is shared) | 20 per stream (quota) |
| Cost | Included in shard-hour fee | Per-consumer-AU-hour (~$0.028/hr) |
| API | `GetRecords` (polling) | `SubscribeToShard` (streaming) |

### Iterator-age data-loss path

Records in Kinesis expire from the stream after `RetentionPeriodHours`. If a
consumer's `IteratorAgeMilliseconds` (time between record write and record
read) approaches the retention period, records are at risk of expiring before
being read. This is silent — no error is thrown, no alarm fires by default.

The standard defence is a CloudWatch alarm on:
`GetRecords.IteratorAgeMilliseconds > RetentionPeriodHours * 3,600,000 * 0.8`

This gives a 20% buffer before data loss begins.

### Encryption internals

- `StartStreamEncryption` transitions the stream to `UPDATING`. New records
  are encrypted with the specified key. Existing records are NOT re-encrypted
  — they remain in their original form until they expire from the retention
  window.
- `StopStreamEncryption` sets `EncryptionType` back to `NONE`. New records are
  plaintext. Existing encrypted records can still be read (the key must remain
  accessible).
- Switching the CMK requires `StopStreamEncryption` then
  `StartStreamEncryption` with the new key — there is no direct update.
- The AWS-managed key (`alias/aws/kinesis`) rotates automatically (annual,
  managed by AWS). Customer-managed CMKs support rotation via
  `aws kms enable-key-rotation`.

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **On-demand capacity mode updates (2024-2025):** On-demand streams now support higher throughput limits and automatic capacity adaptation. Auditors should verify that on-demand streams are not over-provisioned for workloads that have steady, predictable throughput (provisioned mode would be cheaper).
- **Enhanced fan-out consumer improvements (2024):** Enhanced fan-out now supports more consumers per stream (up to 20). Auditors should verify that consumer count is within limits and that consumers have appropriate CloudWatch alarms on `IteratorAgeMilliseconds`.
- **Stream consumer checkpointing via KCL:** Enhanced Kinesis Client Library (KCL) support for checkpointing. No new audit-surface fields, but auditors should verify that consumers have proper checkpoint strategies to avoid data reprocessing.

