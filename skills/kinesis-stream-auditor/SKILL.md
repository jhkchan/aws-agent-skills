---
name: kinesis-stream-auditor
description: >-
  Audits Amazon Kinesis Data Streams for encryption-at-rest gaps (EncryptionType
  NONE), extended-retention cost exposure, shard-count quota-exhaustion risk,
  enhanced-monitoring blind spots (missing per-shard IteratorAge and
  WriteProvisionedThroughputExceeded), consumer checkpointing posture, and
  on-demand vs provisioned mode fit. Emits a deterministic verdict
  (NO_ENCRYPTION | COST_RISK | CONFIG_GAP | OK) per stream with enumerated
  findings and CLI remediation. Use when reviewing Kinesis stream
  configurations, checking encryption posture, validating monitoring coverage,
  auditing retention cost, or assessing consumer health before production
  deployment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline stream-config classification. Live
  account audits use aws kinesis describe-stream-summary, describe-stream,
  list-stream-consumers, and list-shards (AWS CLI v2, SSO or key-based
  credentials).
keywords:
  - Kinesis
  - Kinesis Data Streams
  - stream encryption
  - SSE-KMS
  - EncryptionType
  - enhanced monitoring
  - shard-level metrics
  - retention period
  - extended retention
  - shard count
  - quota exhaustion
  - enhanced fan-out
  - consumer checkpointing
  - on-demand mode
  - provisioned mode
  - UpdateShardCount
  - IteratorAgeMilliseconds
  - WriteProvisionedThroughputExceeded
  - stream cost audit
  - StartStreamEncryption
tags: [kinesis, analytics, encryption, cost, monitoring, consumer, stream-audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Analytics
  verdict_shape: "NO_ENCRYPTION | COST_RISK | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing a Kinesis Data Streams configuration before production deployment,
    checking encryption-at-rest posture, auditing extended-retention cost,
    validating enhanced-monitoring coverage, assessing consumer checkpointing,
    or evaluating on-demand vs provisioned mode fit.
  activation_triggers:
    - "audit this kinesis stream"
    - "is my kinesis stream encrypted"
    - "check kinesis retention cost"
    - "kinesis enhanced monitoring"
    - "kinesis shard quota"
    - "kinesis consumer health"
    - "on-demand vs provisioned kinesis"
    - "kinesis stream cost"
  invocation_schema: >-
    Input: either (a) a Kinesis stream configuration summary (StreamStatus,
    StreamMode, OpenShardCount, RetentionPeriodHours, EncryptionType, KeyId,
    EnhancedMonitoring, ConsumerCount), optionally paired with utilization
    metadata, OR (b) a stream name/ARN for live-account audit. Output:
    deterministic STREAM/VERDICT/REASON/FINDINGS/REMEDIATION block per stream,
    where VERDICT belongs to {NO_ENCRYPTION, COST_RISK, CONFIG_GAP, OK, ERROR}.
---

# Kinesis Stream Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across all
dimensions, and Kinesis has three non-obvious cost-coupling traps that catch
even experienced engineers — retention cost is **separate** from shard cost,
on-demand has a **per-stream-hour floor** regardless of volume, and classic
consumers **share** 2 MB/s read throughput per shard.

Kinesis Data Streams is the ingress artery for real-time pipelines. Unlike S3
or DynamoDB, a misconfigured stream does not just cost money — it silently
drops data when records expire from the retention window before a lagging
consumer reads them, and it silently throttles producers when a single hot
shard exceeds 1 MB/s.

- **EncryptionType: NONE** is plaintext-at-rest — any snapshot, backup, or
  forensic copy of the underlying storage inherits the exposure. This is a
  hard NO_ENCRYPTION regardless of other configuration quality.
- **RetentionPeriodHours > 168** incurs extended-retention storage charges
  that are billed **per shard per hour** beyond the included 24-hour window,
  independent of the per-shard-hour provisioned fee. Most operators budget
  only the shard cost and are surprised by the retention line item.
- **On-demand mode** charges a per-stream-hour fee (~$0.04/hr in us-east-1)
  **regardless of data volume**. A stream ingesting under 200 MB/day costs
  more in on-demand mode than a 1-shard provisioned stream.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| `EncryptionType: NONE` | **NO_ENCRYPTION** | Step 1 |
| `RetentionPeriodHours: 8760` (365-day max) | **COST_RISK** | Step 2 |
| `RetentionPeriodHours > 168` (7 days) on provisioned | **COST_RISK** | Step 2 |
| `StreamMode: ON_DEMAND` + daily ingest < 200 MB | **COST_RISK** | Step 2 |
| `StreamMode: PROVISIONED` + `OpenShardCount > 400` (quota: 500) | **COST_RISK** | Step 2 |
| `EnhancedMonitoring` missing `IteratorAgeMilliseconds` | **CONFIG_GAP** | Step 3 |
| `EnhancedMonitoring` missing `WriteProvisionedThroughputExceeded` | **CONFIG_GAP** | Step 3 |
| `ConsumerCount: 0` (no consumers, data accumulating) | **CONFIG_GAP** | Step 3 |
| `StreamMode: PROVISIONED` + `OpenShardCount: 1` + high throughput | **CONFIG_GAP** | Step 3 |
| KMS-encrypted, reasonable retention, full monitoring, consumers healthy | **OK** | Step 4 |

Priority order: NO_ENCRYPTION > COST_RISK > CONFIG_GAP > OK. See the ordered
steps for edge cases. Deep Kinesis internals (resharding, enhanced fan-out
throughput math, iterator-age data-loss path) are in the
[Deep reference](#deep-reference-kinesis-data-streams-internals) at the end.

## Pre-flight: stream metadata gate (run before classification)

Before evaluating dimensions, classify the stream itself. Several attributes
short-circuit the audit.

**Multi-stream / account-wide sweep note (pagination):** when auditing every
stream in an account, `aws kinesis list-streams` returns at most 100 per page
(use `--next-token`). For each stream, also call `list-stream-consumers` (caps
at 100 per page) and `list-shards` (caps at 1,000 per page, use
`--next-token`). Always drain `NextToken` to completion — the long tail of
streams is where stale, unencrypted, or over-retained streams hide.

**Live-account pre-flight checks (skip if doing offline config audit):**
1. Verify the caller's identity can run `kinesis:UpdateStreamMode` /
   `StartStreamEncryption` if remediation is intended — most read-only auditor
   roles CANNOT, and remediation commands will fail with `AccessDenied`.
2. Verify CloudWatch has the `AWS/Kinesis` namespace ingesting — without it,
   `GetRecords.IteratorAgeMilliseconds` (the stream-level consumer-lag metric)
   has no data and the audit cannot assess consumer health.
3. Snapshot `aws kinesis list-stream-consumers --stream-arn <arn>` BEFORE any
   mode or encryption change — consumers are not migrated automatically when
   switching from KMS to NONE; they continue to decrypt with the old key until
   they re-read from `TRIM_HORIZON`.

| Attribute | Value | Effect on audit |
|---|---|---|
| `StreamStatus` | `ACTIVE` | Normal operation. Proceed with full audit. |
| `StreamStatus` | `CREATING` | Stream not yet available. Note as operational: `PutRecord`/`GetRecords` fail. Classify metadata but mark transitional. |
| `StreamStatus` | `UPDATING` | Resharding or encryption change in progress. `UpdateShardCount` is blocked until ACTIVE. Note but do not block classification. |
| `StreamStatus` | `DELETING` | Stream being deleted — irrecoverable. Output ERROR: stream is being deleted. |
| `StreamMode` | `PROVISIONED` | Shard count is customer-managed. Evaluate shard cost, quota, and capacity. |
| `StreamMode` | `ON_DEMAND` | Shard count is auto-managed. Skip shard-count quota check. Evaluate per-stream-hour cost vs data volume. |

**If the stream configuration is malformed** (missing required fields,
unparseable), output:

```text
STREAM: <stream-name>
VERDICT: ERROR
REASON: Stream configuration is incomplete or malformed — cannot classify.
REMEDIATION: Retrieve the canonical summary with aws kinesis describe-stream-summary --stream-name <name> and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious Kinesis behaviors that change classification

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

### Step 1: Encryption evaluation (highest priority — security-critical)

Evaluate `EncryptionType`:

- **EncryptionType: NONE** → **NO_ENCRYPTION**. Data at rest is plaintext.
  Any EBS snapshot of the underlying infrastructure, any backup, and any
  forensic copy inherits the plaintext exposure. This is the highest-priority
  verdict — no other finding overrides it. Record the finding and jump to
  aggregation; the verdict is NO_ENCRYPTION regardless of cost or config
  findings.

- **EncryptionType: KMS + KeyId = `alias/aws/kinesis`** (AWS-managed key) →
  Encrypted. This dimension is OK. Emit a compliance NOTE: "AWS-managed key
  is shared across all Kinesis streams in the account and its key policy is
  not customer-editable. For compliance frameworks requiring customer-governed
  key policies (PCI-DSS, HIPAA), replace with a customer-managed CMK."
  Proceed to Step 2.

- **EncryptionType: KMS + customer-managed CMK** (KeyId is an ARN with a
  12-digit account and `key/` prefix) → Encrypted with customer-managed key.
  This dimension is OK. Proceed to Step 2.

### Step 2: Cost risk evaluation

Evaluate retention, shard count, and stream mode for cost exposure:

| Condition | Finding | Why |
|---|---|---|
| `RetentionPeriodHours == 8760` (365-day max) | **COST_RISK** | Maximum retention is almost certainly a misconfiguration. 365 days of data on a multi-shard stream generates enormous extended-retention charges. Verify this is intentional. |
| `RetentionPeriodHours > 168` (> 7 days) on provisioned | **COST_RISK** | Extended retention beyond 7 days incurs per-GB charges separate from the shard-hour fee. Evaluate whether consumers truly need a week-plus replay window. |
| `StreamMode: ON_DEMAND` + estimated daily ingest < 200 MB | **COST_RISK** | On-demand per-stream-hour fee (~$29/month) dominates at low volume. A 1-shard provisioned stream (~$11/month) is cheaper. Recommend switching to PROVISIONED. |
| `StreamMode: PROVISIONED` + `OpenShardCount > 400` (default quota 500) | **COST_RISK** | Approaching the account-region shard quota. Only ~100 shards remain for all other streams. Evaluate whether the shard count is justified or whether partition-key distribution is uneven (hot shards). |
| `StreamMode: PROVISIONED` + `OpenShardCount: 1` + throughput near 1 MB/s | **COST_RISK** | Single-shard bottleneck. Write throttling is imminent or already occurring. One shard caps at 1 MB/s / 1,000 records/s — no headroom for bursts. |

**Extended-retention cost formula (us-east-1 pricing, approximate):**

The extended-retention charge applies to data stored beyond the included
24-hour window. The approximate rate is **$0.020 per GB-month** (varies by
region; ap-southeast-1 is ~$0.025, eu-west-1 is ~$0.022). The formula:

```text
monthly_extended_retention_cost =
  shard_count × avg_write_rate (MB/s) × (retention_hours - 24)
  × 3600 s/hr × 30 days / (1024 × 1024) × $0.020/GB-month
```

Worked example: 10 shards at 1 MB/s/shard, 720-hour (30-day) retention:
10 × 1 MB/s × (720 - 24)h × 3600 s/h ÷ 1024 ÷ 1024 × $0.020 ≈ **$4,800/month**
in extended-retention charges alone — dwarfing the ~$110/month shard-hour fee.
This is why retention > 168h is COST_RISK: the storage fee scales linearly with
both shard count AND retention duration, compounding beyond the operator's
mental model of "I'm just paying for shards."

**On-demand vs provisioned crossover formula:**

On-demand cost (approximate, us-east-1):
- Per-stream-hour: ~$0.04/hr (~$29/month flat floor)
- Per-GB ingested: ~$0.04/GB
- Per-GB retrieved: ~$0.04/GB

Provisioned cost (per shard):
- Per-shard-hour: ~$0.015/hr (~$11/month per shard)

Crossover point (ingest only, ignore retrieval):
`on_demand_cost = provisioned_cost`
`$29 + $0.04 × daily_GB × 30 = $11 × shard_count`

For 1-shard provisioned: `$29 + $1.2 × daily_GB = $11` → daily_GB < -15
→ on-demand is ALWAYS more expensive than 1 shard at any ingest volume
below ~15 GB/day. The 200 MB/day threshold is conservative and accounts
for burst unpredictability.

**If any COST_RISK finding is present** and encryption is OK (Step 1 passed),
the verdict is **COST_RISK**. Record all findings and proceed to Step 3 for
additional CONFIG_GAP findings (they appear in FINDINGS but do not override
the COST_RISK verdict).

### Step 3: Config gap evaluation

Evaluate enhanced monitoring and consumer posture:

| Condition | Finding | Why |
|---|---|---|
| `EnhancedMonitoring` ShardLevelMetrics does NOT include `IteratorAgeMilliseconds` | **CONFIG_GAP** | Without per-shard iterator age, you cannot identify which shard's consumer is lagging. Stream-level `GetRecords.IteratorAgeMilliseconds` shows the aggregate but not the hot shard. |
| `EnhancedMonitoring` ShardLevelMetrics does NOT include `WriteProvisionedThroughputExceeded` | **CONFIG_GAP** | Without per-shard write-throttle metrics, you cannot identify the hot shard causing `ProvisionedThroughputExceededException`. |
| `ConsumerCount: 0` + no Kinesis Firehose attached | **CONFIG_GAP** | No registered consumers and no Firehose delivery stream reading from it. Data is accumulating in the stream with nothing reading it. Records will expire from the retention window and be silently lost. |
| `ConsumerCount: 0` + Kinesis Firehose attached | **OK** (this dimension) | Firehose uses an internal consumer that does NOT appear in `ConsumerCount` (it is a delivery-stream integration, not a registered stream consumer). Verify the Firehose is active: `aws firehose describe-delivery-stream --delivery-stream-name <name>` and check `DeliveryStreamStatus: ACTIVE`. |
| `StreamMode: PROVISIONED` + `ConsumerCount > 2` + all consumers using `GetRecords` (no enhanced fan-out) | **CONFIG_GAP** | Multiple classic consumers competing for 2 MB/s shared read throughput per shard. Each consumer gets a fraction. Enhanced fan-out consumers get 2 MB/s each. Detect: call `aws kinesis list-stream-consumers --stream-arn <arn>` and check for `ConsumerStatus: ACTIVE` entries — these are enhanced fan-out consumers. If the list is empty or shorter than the expected consumer count, the remaining consumers use classic `GetRecords`. |

**Consumer detection methodology:** `ConsumerCount` from
`describe-stream-summary` counts ONLY registered enhanced fan-out consumers.
Classic consumers (those using `GetRecords` directly) are NOT counted. To
determine the true consumer landscape:
1. `aws kinesis list-stream-consumers --stream-arn <arn>` — lists enhanced
   fan-out consumers (compare count to `ConsumerCount`).
2. Check for Kinesis Firehose delivery streams with the stream as source:
   `aws firehose list-delivery-streams` then
   `aws firehose describe-delivery-stream` for each — Firehose uses
   `GetRecords` internally and does NOT register as a stream consumer.
3. Check for Lambda event-source mappings:
   `aws lambda list-event-source-mappings --event-source-arn <arn>` — Lambda
   can use either `GetRecords` (polling) or `SubscribeToShard` (enhanced
   fan-out) depending on the consumer registration.

**If any CONFIG_GAP finding is present** and Steps 1-2 passed (no NO_ENCRYPTION
or COST_RISK), the verdict is **CONFIG_GAP**.

### Step 4: Clean posture

If no findings from Steps 1-3:

- EncryptionType: KMS (customer-managed CMK or AWS-managed)
- RetentionPeriodHours: reasonable (24-168 hours)
- EnhancedMonitoring includes IteratorAgeMilliseconds and
  WriteProvisionedThroughputExceeded
- ConsumerCount >= 1

→ **VERDICT: OK**.

### Step 5: Aggregation — worst verdict wins

```text
verdict = max_severity(encryption_verdict, cost_verdict, config_verdict)
```

Priority: NO_ENCRYPTION > COST_RISK > CONFIG_GAP > OK.

All findings from all dimensions are listed in the FINDINGS section regardless
of which one drives the final verdict.

## Output format (per stream)

```text
STREAM: <stream-name>
VERDICT: NO_ENCRYPTION | COST_RISK | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
FINDINGS:
  - [NO_ENCRYPTION] <finding description (Step N)>
  - [COST_RISK] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — unencrypted stream with extended retention

```text
STREAM: no-encryption-extended-retention
VERDICT: NO_ENCRYPTION
REASON: EncryptionType is NONE — data at rest is plaintext (Step 1).
RetentionPeriodHours is 720 (30 days) on an 8-shard provisioned stream,
incurring significant extended-retention charges (Step 2).
FINDINGS:
  - [NO_ENCRYPTION] EncryptionType: NONE — data at rest is not encrypted (Step 1)
  - [COST_RISK] RetentionPeriodHours: 720 exceeds 168h threshold — extended-retention storage charges apply per GB beyond 24h (Step 2)
  - [CONFIG_GAP] EnhancedMonitoring missing IteratorAgeMilliseconds — cannot identify per-shard consumer lag (Step 3)
REMEDIATION:
  1. Enable KMS encryption: aws kinesis start-stream-encryption --stream-name no-encryption-extended-retention --encryption-type KMS --key-id alias/aws/kinesis
  2. Reduce retention: aws kinesis decrease-stream-retention-period --stream-name no-encryption-extended-retention --retention-period-hours 24
  3. Enable key metrics: aws kinesis enable-enhanced-monitoring --stream-name no-encryption-extended-retention --shard-level-metrics IteratorAgeMilliseconds WriteProvisionedThroughputExceeded
```

## Edge-case handling

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

## Anti-Patterns — NEVER

- NEVER classify `EncryptionType: NONE` as anything other than NO_ENCRYPTION.
  Plaintext data at rest is the highest-priority finding regardless of how
  well-tuned the retention, shard count, or monitoring are. A perfectly
  monitored, cost-optimized stream with no encryption is still a compliance
  violation and a data-exposure risk.

- NEVER flag an on-demand stream's `OpenShardCount` against the 500-shard
  provisioned quota. On-demand shards are managed by AWS and have a separate
  quota (50 on-demand streams per region). Flagging on-demand shards as
  "approaching quota" is a false positive.

- NEVER flag `RetentionPeriodHours: 24` as a cost risk. 24 hours is the
  included retention window — no extended-retention charges apply. Only
  retention beyond 168 hours (7 days) is a COST_RISK, and only beyond 24
  hours is there ANY additional charge.

- NEVER recommend switching from provisioned to on-demand for a steady-state
  high-throughput workload without explaining the cost crossover. On-demand
  charges per-GB-ingested on top of the per-stream-hour fee. For a stream
  consistently above ~1 GB/day, provisioned is cheaper. On-demand is for
  bursty, unpredictable workloads.

- NEVER assume `ConsumerCount: 0` is always a problem. A stream may be
  intentionally buffering for a future consumer, or feeding a Kinesis Firehose
  (which uses internal consumers not counted in `ConsumerCount`). If a
  Firehose is attached, note it and do not flag.

- NEVER recommend `UpdateShardCount` to scale below 1 shard. One shard is the
  absolute floor — Kinesis does not support sub-shard streams. A stream with
  `OpenShardCount: 1` cannot be made smaller.

- NEVER treat the AWS-managed key (`alias/aws/kinesis`) as an encryption gap.
  Encryption IS present — the data is encrypted at rest. The key policy is not
  customer-editable, which is a compliance nuance, not a security hole. Flag
  as a NOTE, not as NO_ENCRYPTION.

- NEVER overlook the classic-consumer shared-throughput trap. Three consumers
  using `GetRecords` on the same shard share 2 MB/s total. If one consumer
  reads aggressively, the others starve. Enhanced fan-out gives each consumer
  2 MB/s independently. Flag `ConsumerCount > 2` with no enhanced fan-out as
  CONFIG_GAP.

- NEVER assume `StartStreamEncryption` is instant. The stream enters UPDATING
  state and existing records are NOT retroactively re-encrypted — only new
  records are encrypted with the specified key. Old records remain readable
  in their original (plaintext or old-key) form until they expire from the
  retention window.

- NEVER flag a stream in UPDATING state as misconfigured. UPDATING is a
  transitional state during resharding or encryption change. Re-audit after
  the stream returns to ACTIVE before drawing conclusions.

- NEVER recommend enabling ALL shard-level metrics on a high-shard-count
  stream without warning about CloudWatch costs. Each shard-level metric is a
  separate CloudWatch custom metric. A 200-shard stream with 8 metrics = 1,600
  custom metrics/month (~$80+ in CloudWatch). Recommend only
  IteratorAgeMilliseconds and WriteProvisionedThroughputExceeded as essential.

- NEVER assume `GetRecords.IteratorAgeMilliseconds` at the stream level is
  sufficient for diagnosis. Stream-level iterator age is an aggregate — it
  hides the hot shard. Enhanced monitoring with per-shard IteratorAge is the
  only way to identify which shard's consumer is lagging.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`StartStreamEncryption`, `StopStreamEncryption`, `UpdateShardCount`,
  `IncreaseStreamRetentionPeriod`, `DecreaseStreamRetentionPeriod`,
  `UpdateStreamMode`), the auditor MUST emit:
  `CONFIRM: About to <action> on stream <name> in account <account>. This
  affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- **StartStreamEncryption key-id validation.** When emitting a
  `StartStreamEncryption` command, verify the KeyId exists and the KMS key is
  ENABLED: `aws kms describe-key --key-id <id>`. A key in `Disabled` or
  `PendingDeletion` state will cause `StartStreamEncryption` to fail with
  `KMSDisabledException`.

- **Retention decrease is irreversible for expired data.** When emitting
  `DecreaseStreamRetentionPeriod`, note that records older than the new
  retention period are immediately deleted and unrecoverable. Confirm no
  consumer needs the older data before decreasing.

- **UpdateStreamMode is one-way for on-demand to provisioned.** Switching
  from ON_DEMAND to PROVISIONED sets the shard count based on the current
  on-demand capacity. Verify the resulting shard count is within budget
  before switching. Switching back to ON_DEMAND is possible but takes effect
  immediately.

- **Enhanced fan-out consumer registration cost.** Each enhanced fan-out
  consumer incurs per-consumer-AU-hour charges (~$0.028/consumer-AU-hour in
  us-east-1). Confirm the consumer is needed before recommending
  `RegisterStreamConsumer`.

- **Capture pre-change state for rollback.** Before any modification, capture:
  `aws kinesis describe-stream-summary --stream-name <name> --output json >
  /tmp/<name>-backup-$(date +%s).json`. There is no undo for retention
  decreases or encryption-key changes.

## Remediation guidance

### For NO_ENCRYPTION — EncryptionType: NONE

1. **Enable KMS encryption** immediately. Use a customer-managed CMK for
   compliance-sensitive workloads:
   ```bash
   aws kinesis start-stream-encryption \
     --stream-name <name> \
     --encryption-type KMS \
     --key-id arn:aws:kms:us-east-1:111111111111:key/<cmk-id>
   ```
   Or with the AWS-managed key (minimum viable):
   ```bash
   aws kinesis start-stream-encryption \
     --stream-name <name> \
     --encryption-type KMS \
     --key-id alias/aws/kinesis
   ```
2. **Note:** existing plaintext records are NOT retroactively encrypted. Only
   new records are encrypted. Old records expire from the retention window
   naturally. If immediate encryption of all data is required, create a new
   encrypted stream and migrate producers.
3. **Verify:** `aws kinesis describe-stream-summary --stream-name <name>` and
   confirm `EncryptionType: KMS`.

### For COST_RISK — Extended retention (> 168 hours)

1. **Reduce retention** to the minimum consumers need for replay:
   ```bash
   aws kinesis decrease-stream-retention-period \
     --stream-name <name> \
     --retention-period-hours 24
   ```
2. **Verify** no consumer requires the extended replay window before
   decreasing. Records older than the new retention period are deleted
   immediately and irreversibly.
3. **Calculate savings:** extended retention charges are proportional to
   (retention_hours - 24) x shard_count x average_data_rate. Reducing from
   720h to 24h on a 10-shard stream at 1 MB/s/shard saves ~25 TB of
   extended-retention storage per month.

### For COST_RISK — On-demand at low volume (< 200 MB/day)

1. **Switch to provisioned mode:**
   ```bash
   aws kinesis update-stream-mode \
     --stream-arn arn:aws:kinesis:us-east-1:111111111111:stream/<name> \
     --stream-mode PROVISIONED
   ```
2. **Set shard count** to match peak throughput:
   ```bash
   aws kinesis update-shard-count \
     --stream-name <name> \
     --target-shard-count 1 \
     --scaling-type UNIFORM_SCALING
   ```
3. **Savings:** on-demand per-stream-hour (~$29/month) + per-GB charges
   vs provisioned 1-shard (~$11/month). For < 200 MB/day, provisioned is
   cheaper.

### For COST_RISK — Provisioned approaching shard quota (> 400 shards)

1. **Evaluate partition-key distribution.** Uneven distribution causes hot
   shards, which forces over-provisioning. Fix the partition key strategy
   before reducing shards.
2. **Reduce shard count** if throughput allows:
   ```bash
   aws kinesis update-shard-count \
     --stream-name <name> \
     --target-shard-count 200 \
     --scaling-type UNIFORM_SCALING
   ```
3. **Request a quota increase** if the shard count is justified:
   ```bash
   aws service-quotas request-service-quota-increase \
     --service-code kinesis \
     --quota-code L-7B8615C9 \
     --desired-value 1000
   ```

### For CONFIG_GAP — Missing enhanced-monitoring metrics

1. **Enable essential shard-level metrics:**
   ```bash
   aws kinesis enable-enhanced-monitoring \
     --stream-name <name> \
     --shard-level-metrics IteratorAgeMilliseconds WriteProvisionedThroughputExceeded
   ```
2. **Set a CloudWatch alarm** on iterator age approaching retention:
   ```bash
   aws cloudwatch put-metric-alarm \
     --alarm-name kinesis-<name>-iterator-age \
     --namespace AWS/Kinesis \
     --metric-name GetRecords.IteratorAgeMilliseconds \
     --dimensions Name=StreamName,Value=<name> \
     --threshold <RetentionPeriodHours * 3600000 * 0.8> \
     --comparison-operator GreaterThanThreshold \
     --evaluation-periods 1 \
     --period 300
   ```

### For CONFIG_GAP — No consumers (ConsumerCount: 0)

1. **Register a consumer** or verify a Kinesis Firehose is attached:
   ```bash
   aws kinesis register-stream-consumer \
     --stream-arn arn:aws:kinesis:us-east-1:111111111111:stream/<name> \
     --consumer-name my-consumer
   ```
2. If no consumer is needed yet, set a CloudWatch alarm on
   `GetRecords.IteratorAgeMilliseconds` to alert when data is at risk of
   expiring unread.

### For OK

1. No remediation required.
2. Recommend a CloudWatch alarm on `GetRecords.IteratorAgeMilliseconds`
   approaching the retention threshold (defense-in-depth).
3. For provisioned streams, recommend periodic shard-utilization review to
   catch partition-key hot spots before they cause throttling.

## Deep reference: Kinesis Data Streams internals

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

## Domain

AWS CloudOps / Kinesis Data Streams Security, Cost, and Operational Auditing.
