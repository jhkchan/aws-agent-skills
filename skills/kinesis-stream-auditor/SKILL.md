---
name: kinesis-stream-auditor
description: Audits Amazon Kinesis Data Streams for encryption-at-rest gaps (EncryptionType NONE), extended-retention cost exposure, shard-count quota-exhaustion risk, enhanced-monitoring blind spots (missing per-shard IteratorAge and WriteProvisionedThroughputExceeded), consumer checkpointing posture, and on-demand vs provisioned mode fit. Emits a deterministic verdict (NO_ENCRYPTION | COST_RISK | CONFIG_GAP | OK) per stream with enumerated findings and CLI remediation. Use when reviewing Kinesis stream configurations, checking encryption posture, validating monitoring coverage, auditing retention cost, or assessing consumer health before production deployment.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline stream-config classification. Live account audits use aws kinesis describe-stream-summary, describe-stream, list-stream-consumers, and list-shards (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  verdict_shape: NO_ENCRYPTION | COST_RISK | CONFIG_GAP | OK
  when_to_use: Reviewing a Kinesis Data Streams configuration before production deployment, checking encryption-at-rest posture, auditing extended-retention cost, validating enhanced-monitoring coverage, assessing consumer checkpointing, or evaluating on-demand vs provisioned mode fit.
  activation_triggers: audit this kinesis stream, is my kinesis stream encrypted, check kinesis retention cost, kinesis enhanced monitoring, kinesis shard quota, kinesis consumer health, on-demand vs provisioned kinesis, kinesis stream cost
  invocation_schema: 'Input: either (a) a Kinesis stream configuration summary (StreamStatus, StreamMode, OpenShardCount, RetentionPeriodHours, EncryptionType, KeyId, EnhancedMonitoring, ConsumerCount), optionally paired with utilization metadata, OR (b) a stream name/ARN for live-account audit. Output: deterministic STREAM/VERDICT/REASON/FINDINGS/REMEDIATION block per stream, where VERDICT belongs to {NO_ENCRYPTION, COST_RISK, CONFIG_GAP, OK, ERROR}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Kinesis, Kinesis Data Streams, stream encryption, SSE-KMS, EncryptionType, enhanced monitoring, shard-level metrics, retention period, extended retention, shard count, quota exhaustion, enhanced fan-out, consumer checkpointing, on-demand mode, provisioned mode, UpdateShardCount, IteratorAgeMilliseconds, WriteProvisionedThroughputExceeded, stream cost audit, StartStreamEncryption
  tags: kinesis, analytics, encryption, cost, monitoring, consumer, stream-audit
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

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Pre-flight: stream metadata gate (run before classification)".
> Load when: classifying a stream — StreamStatus/StreamMode gate table, account-wide sweep pagination, malformed-config ERROR block.

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious Kinesis behaviors that change classification

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Step 0: Expert knowledge — non-obvious Kinesis behaviors that change classification".
> Load when: a behavior seems non-obvious — retention cost coupling, on-demand per-stream-hour floor, shared classic-consumer throughput, shard quota scope.

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

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Edge-case handling".
> Load when: an edge case appears — UPDATING streams, on-demand shard counts, sub-24h retention, all-metrics monitoring cost.

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

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Pre-flight safety checks (run before any remediation CLI)".
> Load when: before any remediation CLI — confirmation gate, KMS key validation, irreversible retention decrease, rollback snapshot.

## Remediation guidance

> **Moved verbatim** → [references/error-handling.md](references/error-handling.md) § "Remediation guidance".
> Load when: the verdict is known — per-verdict fix procedures with exact CLI for NO_ENCRYPTION, COST_RISK, and CONFIG_GAP findings.

## Deep reference: Kinesis Data Streams internals

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Deep reference: Kinesis Data Streams internals".
> Load when: you need the internals — shard capacity math, resharding mechanics, fan-out vs classic throughput, iterator-age data-loss path.

## Recent AWS features (2024-2026)

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Recent AWS features (2024-2026)".
> Load when: checking 2024-2026 feature availability — on-demand capacity updates, fan-out consumer limits, KCL checkpointing.

## References (load on demand)

- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight stream metadata gate (status/mode table, sweep pagination, malformed-config ERROR block) and pre-flight safety checks before remediation CLIs
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 non-obvious Kinesis behaviors, edge-case handling, Kinesis internals deep reference (shard math, resharding, fan-out, iterator-age loss path), recent AWS features 2024-2026
- [references/error-handling.md](references/error-handling.md) — remediation guidance per verdict (NO_ENCRYPTION, COST_RISK, CONFIG_GAP, OK)

## Domain

AWS CloudOps / Kinesis Data Streams Security, Cost, and Operational Auditing.

## AWS documentation

- **Amazon Kinesis Data Streams Developer Guide** — https://docs.aws.amazon.com/streams/latest/dev/introduction.html
- **Kinesis Security** — https://docs.aws.amazon.com/streams/latest/dev/security.html
- **Kinesis API Reference** — https://docs.aws.amazon.com/kinesis/latest/APIReference/
- **Kinesis CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/kinesis/
