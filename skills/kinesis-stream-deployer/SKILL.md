---
name: kinesis-stream-deployer
description: 'Provisions Amazon Kinesis Data Streams with production defaults: stream creation (shard count, stream mode provisioned vs on-demand), enhanced fan-out (consumer registration, SubscribeToShard), server-side encryption (KMS CMK, key policy, aws/kinesis alias), resource-level IAM policies (PutRecord, GetRecords, SubscribeToShard), and CloudWatch monitoring (IteratorAgeMilliseconds, WriteProvisionedThroughputExceeded). Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Kinesis data stream, switching stream mode to on-demand, registering enhanced fan-out consumers, enabling SSE-KMS encryption, sizing shard count for throughput, or wiring CloudWatch alarms for iterator age and throttling. Triggers: create kinesis stream, kinesis on-demand capacity, kinesis enhanced fan-out, kinesis SSE-KMS, kinesis shard count, kinesis IAM policy, kinesis CloudWatch iterator age, SubscribeToShard consumer, kinesis throughput provisioning.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with kinesis, iam, kms, and cloudwatch access. Works with Terraform aws_kinesis_stream / aws_kinesis_stream_consumer resources and CloudFormation AWS::Kinesis::Stream / AWS::Kinesis::StreamConsumer templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, kinesis, kinesis-data-streams, cloudops, deploy, analytics, provisioning, stream-mode, on-demand, enhanced-fanout, sse-kms, iam, cloudwatch
  dependencies: aws-orchestrator
  keywords: aws, kinesis, kinesis data streams, cloudops, deploy, provisioning, stream mode, on-demand, provisioned, shard count, enhanced fan-out, subscribe to shard, sse-kms, server-side encryption, kms, iam policy, resource-level iam, cloudwatch, iterator age, throughput exceeded, put record, get records, stream consumer
  when_to_use: Invoke when the user wants to create an Amazon Kinesis Data Stream, choose between provisioned (shard-based) and on-demand capacity mode, register enhanced fan-out consumers for dedicated read throughput, enable server-side encryption with KMS, define resource-level IAM policies for producer/consumer applications, or set up CloudWatch monitoring for iterator age and write throttling. Do NOT invoke for Kinesis Data Firehose delivery streams (use firehose skills), Kinesis Video Streams, or auditing existing stream configurations (use kinesis-stream-auditor).
---

# Kinesis Stream Deployer

An AWS CloudOps agent skill that provisions Amazon Kinesis Data Streams
with correct defaults. The skill walks the operator through stream mode
selection, shard sizing, enhanced fan-out consumers, encryption, IAM,
and monitoring, captures throughput and consumer decisions, explains why
each default matters, and emits a READY_TO_DEPLOY checklist with copy-
pasteable verification commands.

## Activation keywords

create Kinesis stream, Kinesis on-demand capacity, Kinesis enhanced
fan-out, Kinesis SSE-KMS, Kinesis shard count, Kinesis IAM policy,
Kinesis CloudWatch iterator age, SubscribeToShard consumer, Kinesis
throughput provisioning, Kinesis stream mode.

## STRICT output contract

When this skill is invoked with a Kinesis-stream-provisioning request
(stream creation, capacity mode, consumer registration, encryption, IAM,
monitoring, or a partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section using
the literal all-caps labels `KINESIS_STREAM:`, `VERDICT:`, `CHECKLIST:`,
and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Stream mode: provisioned vs on-demand | Capacity model |
| Step 2 — Shard count sizing (provisioned mode) | Throughput planning |
| Step 3 — Stream creation (CLI, SDK, IaC) | Provisioning step |
| Step 4 — Enhanced fan-out consumers | Dedicated read throughput |
| Step 5 — Server-side encryption (KMS) | Encryption |
| Step 6 — Resource-level IAM policies | Producer / consumer permissions |
| Step 7 — CloudWatch monitoring | Iterator age, throttling, alarms |
| Step 8 — Stream ARN resource policies | Cross-account access control |
| Step 9 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/stream-mode-and-scaling.md | Capacity mode + auto-scaling detail |
| references/iam-and-encryption.md | IAM policies + SSE-KMS detail |

## Mindset

**One-line takeaway:** Kinesis Data Streams is a managed real-time data
ingestion service. The capacity model (provisioned shards vs on-demand)
is the foundational decision — it determines cost, scaling behavior, and
throughput limits. Enhanced fan-out gives dedicated 2 MiB/sec read
throughput per consumer without contending with other readers.

Deep-dives moved verbatim to `references/advanced-patterns.md`:
misconceptions, dependency graph, cost crossover, fan-out model, IteratorAge.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account with Kinesis access | Can't provision without it | `aws sts get-caller-identity` |
| Region selected | Kinesis streams are regional | `aws configure get region` |
| Stream name identified | Unique per account-region; 1-128 chars | Confirm naming convention |
| Stream mode decision | Determines cost model, scaling, shard relevance | Assess traffic pattern |
| Shard count (if provisioned) | Write throughput: 1 MiB/sec or 1,000 records/sec per shard | Estimate peak write throughput |
| KMS key (if SSE-KMS) | CMK requires key policy permitting Kinesis service | `aws kms describe-key` |
| IAM principal for producer | Needs `kinesis:PutRecord` / `PutRecords` on stream ARN | Confirm producer role |
| IAM principal for consumer | Needs `GetRecords`+`GetShardIterator` or `SubscribeToShard` | Confirm consumer role |
| Consumer count estimate | Determines enhanced fan-out need (max 20 per stream) | List downstream consumers |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Stream mode: provisioned vs on-demand

The first decision is the capacity model: provisioned (shard-based) or
on-demand (automatic scaling).

**Decision tree:**

```text
Is the write throughput predictable and steady?
├── YES, and > ~2-3 MiB/sec sustained
│   → PROVISIONED mode (cheaper at scale; size shard count to throughput)
│
├── NO — bursty, unpredictable, or unknown
│   → ON_DEMAND mode (auto-scales; no shard management)
│
└── UNKNOWN — new workload, no traffic data
    → Start ON_DEMAND, switch to PROVISIONED after 2-4 weeks of data
```

| Feature | Provisioned | On-demand |
|---|---|---|
| Capacity management | Manual (update-shard-count) | Automatic |
| Write throughput | 1 MiB/sec or 1,000 records/sec per shard | Auto-scales |
| Read throughput | 2 MiB/sec per shard (shared or enhanced) | Same per-shard; stream auto-scales |
| Cost model | Per shard-hour | Per stream-hour + per GB ingested |
| Cost at low volume | Higher (pay for idle shards) | Lower (pay per GB) |
| Cost at high volume | Lower (flat per-shard) | Higher (per-GB scales linearly) |
| Scaling downtime | Brief (shard split/merge) | None (automatic) |

## Step 2 — Shard count sizing (provisioned mode)

SKIPPED for on-demand mode. Shard count determines write and read
throughput.

| Dimension | Limit per shard |
|---|---|
| Write data throughput | 1 MiB/sec |
| Write record count | 1,000 records/sec |
| Read (shared GetRecords) | 2 MiB/sec total |
| Read (enhanced fan-out) | 2 MiB/sec per consumer |
| Max record size | 1 MiB |

**Sizing formula:**

```text
shard_count = max(
  ceil(write_mib_per_sec / 1),
  ceil(write_records_per_sec / 1000)
)
```

Always round UP. Consider the record count limit (small frequent records
hit 1,000 records/sec before 1 MiB/sec). Add 20-30% headroom for spikes.
Use `update-shard-count` to scale (provisioned only).

## Step 3 — Stream creation

**Provisioned stream:**

```bash
aws kinesis create-stream \
  --stream-name my-data-stream \
  --shard-count 5 \
  --stream-mode-details StreamMode=PROVISIONED \
  --region us-east-1
```

**On-demand stream:**

```bash
aws kinesis create-stream \
  --stream-name my-data-stream \
  --stream-mode-details StreamMode=ON_DEMAND \
  --region us-east-1
```

`--shard-count` is IGNORED when `StreamMode=ON_DEMAND`. Do not specify it.

**Wait for ACTIVE:**

```bash
aws kinesis wait stream-exists --stream-name my-data-stream --region us-east-1
aws kinesis describe-stream-summary \
  --stream-name my-data-stream \
  --query 'StreamDescriptionSummary.StreamStatus' --output text --region us-east-1
# Expected: ACTIVE
```

**Set retention period (default 24 hours):**

```bash
aws kinesis increase-stream-retention-period \
  --stream-name my-data-stream --retention-period-hours 168 --region us-east-1
```

**Common mistake:** using the stream before it is ACTIVE. Takes 1-2
minutes. Use `wait stream-exists`.

## Step 4 — Enhanced fan-out consumers

Enhanced fan-out gives each registered consumer a dedicated 2 MiB/sec
read throughput via SubscribeToShard (HTTP/2 push).

```bash
aws kinesis register-stream-consumer \
  --stream-arn arn:aws:kinesis:us-east-1:123456789012:stream/my-data-stream \
  --consumer-name my-enhanced-consumer --region us-east-1
```

**Limits:** max 20 consumers per stream (soft limit). Consumer name
unique per stream. Consumer must use SubscribeToShard API (not
GetRecords).

**Deregister (cleanup):**

```bash
aws kinesis deregister-stream-consumer \
  --consumer-arn arn:aws:kinesis:us-east-1:123456789012:stream/my-data-stream/consumer/my-enhanced-consumer:1620000000 \
  --region us-east-1
```

**Common mistake:** registering a consumer but the application uses
standard GetRecords. Enhanced fan-out requires SubscribeToShard (via KCL
enhanced fan-out config or direct HTTP/2 API).

## Step 5 — Server-side encryption (KMS)

SSE-KMS encrypts data at rest using a CMK or AWS-managed key
(`alias/aws/kinesis`). Full KMS key creation and key policy details in
`references/iam-and-encryption.md`.

**Enable SSE-KMS (AWS-managed key):**

```bash
aws kinesis start-stream-encryption \
  --stream-name my-data-stream --encryption-type KMS \
  --key-id alias/aws/kinesis --region us-east-1
```

**Enable SSE-KMS (customer-managed key — recommended):**

```bash
aws kinesis start-stream-encryption \
  --stream-name my-data-stream --encryption-type KMS \
  --key-id alias/kinesis/my-data-stream --region us-east-1
```

**Key policy requirement:** the CMK policy MUST allow
`kinesis.amazonaws.com` to call `kms:GenerateDataKey` and `kms:Decrypt`.
Without this, PutRecord/GetRecords fail with KMS access errors. See
`references/iam-and-encryption.md` for the full key policy statement.

Producers and consumers also need `kms:GenerateDataKey` and
`kms:Decrypt` in their IAM policies when using a CMK.

## Step 6 — Resource-level IAM policies

Kinesis supports resource-level IAM: producer and consumer policies
reference the stream ARN. Full policy JSON templates are in
`references/iam-and-encryption.md`.

**Producer requires:** `kinesis:PutRecord`, `kinesis:PutRecords`,
`kinesis:DescribeStream`, `kinesis:DescribeStreamSummary` on the stream
ARN.

**Standard consumer requires:** `kinesis:GetRecords`,
`kinesis:GetShardIterator`, `kinesis:DescribeStream`,
`kinesis:DescribeStreamSummary`, `kinesis:ListShards` on the stream ARN.

**Enhanced fan-out consumer requires:** `kinesis:SubscribeToShard`,
`kinesis:DescribeStream`, `kinesis:DescribeStreamSummary`,
`kinesis:ListShards` on BOTH the stream ARN AND the consumer ARN
(`stream/<name>/consumer/*`).

**With SSE-KMS (CMK):** add `kms:GenerateDataKey` and `kms:Decrypt` on
the KMS key ARN to both producer and consumer policies.

**Common mistakes:**
- Granting `kinesis:*` on `*` (over-broad) instead of specific actions
  on the stream ARN.
- Forgetting `kinesis:DescribeStream` — without it, the consumer/KCL
  cannot discover shards and fails silently.
- Enhanced fan-out consumer missing the consumer ARN in Resource.

## Step 7 — CloudWatch monitoring

The two most critical alarms are IteratorAgeMilliseconds (consumer lag)
and WriteProvisionedThroughputExceeded (write throttling).

Full `put-metric-alarm` command listings moved verbatim to
`references/diagnostic-commands.md` (load on demand).

| Metric | What it tells you | Healthy threshold |
|---|---|---|
| `GetRecords.IteratorAgeMilliseconds` | Consumer lag | < 300,000 ms (5 min) |
| `WriteProvisionedThroughputExceeded` | Write throttling (provisioned) | 0 |
| `PutRecord.Success` / `PutRecords.Success` | Write success rate | > 99% |
| `GetRecords.Success` | Read success rate | > 99% |

**Common mistake:** setting IteratorAge threshold without considering
the retention period. If retention is 1 hour, a 1-hour IteratorAge means
data loss is imminent.

## Step 8 — Stream ARN resource policies

Resource-policy detail and `put-resource-policy` example moved verbatim to
`references/advanced-patterns.md` (load on demand).

## Step 9 — Recent features

Recent-feature details moved verbatim to `references/advanced-patterns.md`
(load on demand).

## NEVER do these things

1. **NEVER specify shard count for on-demand streams and expect it to
   matter.** `--shard-count` is IGNORED when `StreamMode=ON_DEMAND`. The
   stream auto-scales; shard count is irrelevant.

2. **NEVER grant `kinesis:*` on `*` in IAM policies.** Use resource-
   level permissions with the specific stream ARN and specific actions.
   Over-broad policies violate least-privilege.

3. **NEVER skip the IteratorAgeMilliseconds CloudWatch alarm.** Without
   it, a consumer falling behind goes undetected until data is lost.
   This is the #1 cause of silent data loss in Kinesis pipelines.

4. **NEVER use a CMK for SSE-KMS without a key policy permitting the
   Kinesis service principal.** PutRecord and GetRecords fail with KMS
   access denied. The key policy MUST allow `kinesis.amazonaws.com` to
   call `kms:GenerateDataKey` and `kms:Decrypt`.

5. **NEVER assume enhanced fan-out is free.** Enhanced fan-out charges a
   data-retrieval fee per consumer-shard-hour. For a 10-shard stream
   with 5 enhanced consumers, that is 50 consumer-shard-hours per hour.
   Use standard GetRecords for cost-sensitive, latency-tolerant
   consumers.

6. **NEVER forget `kinesis:DescribeStream` in consumer IAM policies.**
   Without it, the consumer (or KCL) cannot discover shard information
   and fails to start.

7. **NEVER set retention period lower than the consumer's max downtime.**
   If a consumer can be down for 4 hours, retention MUST be at least 4
   hours. Otherwise data is permanently lost during an outage.

8. **NEVER switch stream modes frequently.** Mode switching is throttled
   to once per 15 minutes and the cost model changes fundamentally.

9. **NEVER use `update-shard-count` to scale by more than 2x in a single
   operation.** Large changes cause brief throughput disruption. Scale
   incrementally.

10. **NEVER assume WriteProvisionedThroughputExceeded is benign.** Any
    non-zero value means records are being throttled. Scale up or switch
    to on-demand mode.

## Output format

```text
KINESIS_STREAM: <stream-name> (<stream-arn>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Stream name: <stream-name>
  [✓|✗] Stream mode: PROVISIONED | ON_DEMAND
  [✓|✗] Shard count: <n> (provisioned only — ignored if on-demand)
  [✓|✗] Retention period: <hours> hours (default 24)
  [✓|✗] Enhanced fan-out: <consumer-name> (consumer ARN) | Standard GetRecords
  [✓|✗] SSE-KMS: enabled (key <key-id> / alias/aws/kinesis) | Disabled
  [✓|✗] KMS key policy: permits kinesis.amazonaws.com | N/A
  [✓|✗] Producer IAM: <role/user> → kinesis:PutRecord, PutRecords on <stream-arn>
  [✓|✗] Consumer IAM: <role/user> → kinesis:GetRecords, GetShardIterator (or SubscribeToShard) on <stream-arn>
  [✓|✗] CloudWatch alarm: IteratorAgeMilliseconds > <threshold> → <sns-topic>
  [✓|✗] CloudWatch alarm: WriteProvisionedThroughputExceeded > 0 → <sns-topic>
  [✓|✗] Resource policy: <cross-account principal> | Same account
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws kinesis describe-stream-summary --stream-name <stream-name> --region <region>
  aws kinesis list-stream-consumers --stream-arn <stream-arn> --region <region>
  aws kinesis describe-stream --stream-name <stream-name> --query 'StreamDescription.{Encryption:EncryptionType,KeyId:KeyId}' --region <region>
  aws cloudwatch describe-alarms --alarm-name-prefix "Kinesis-<stream-name>" --region <region>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: READY_TO_DEPLOY` with a `[✗]` checklist item.**
   If any prerequisite is missing, the verdict MUST be
   `PREREQUISITES_MISSING`. Do not mix verdicts.

2. **NEVER omit the stream mode from the checklist.** The mode
   (`PROVISIONED` or `ON_DEMAND`) determines whether shard count is
   relevant and which CloudWatch alarms apply.

3. **NEVER list a shard count for an on-demand stream without marking
   it `N/A`.** `--shard-count` is IGNORED when `StreamMode=ON_DEMAND`.
   Showing a number misleads the operator into thinking it matters.

4. **NEVER show enhanced fan-out consumers without the consumer ARN.**
   The consumer ARN is required for IAM policy Resource clauses and
   for `deregister-stream-consumer` cleanup. Omitting it breaks
   downstream automation.

5. **NEVER omit the SSE-KMS line from the checklist.** Even if
   encryption is disabled, the line MUST appear as `[✓] SSE-KMS:
   Disabled` so the operator explicitly confirms the decision.

6. **NEVER omit the IteratorAgeMilliseconds alarm from a READY_TO_DEPLOY
   checklist.** Without it, consumer lag goes undetected until data
   loss. This alarm is mandatory for every deployed stream.

7. **NEVER omit VERIFICATION_COMMANDS from the output block.** The
   verification commands are what the operator runs after deployment
   to confirm the stream is ACTIVE, consumers are registered, and
   encryption is enabled.

### Decision tree

```text
Is the write throughput predictable and steady?
├── YES, > ~2-3 MiB/sec sustained
│   → PROVISIONED mode
│     ├── Size shards: ceil(write_mib/sec) with 20-30% headroom
│     ├── Add WriteProvisionedThroughputExceeded alarm
│     └── Proceed to consumer / encryption / IAM steps
├── NO — bursty, unpredictable, or unknown
│   → ON_DEMAND mode
│     ├── Shard count: N/A (auto-scales)
│     ├── Skip WriteProvisionedThroughputExceeded alarm
│     └── Proceed to consumer / encryption / IAM steps
└── UNKNOWN — new workload
    → Start ON_DEMAND, evaluate after 2-4 weeks

How many consumers read from this stream?
├── 1 consumer → standard GetRecords (no enhanced fan-out)
├── 2-3 consumers, latency-tolerant → standard GetRecords (shared)
├── 2-3 consumers, low-latency → enhanced fan-out (dedicated push)
└── 4+ consumers → enhanced fan-out (avoids read contention)

Is SSE-KMS required?
├── YES (compliance / security policy)
│   ├── Use CMK (recommended) or alias/aws/kinesis
│   ├── Key policy MUST permit kinesis.amazonaws.com
│   └── Producer + consumer IAM MUST include kms:GenerateDataKey, kms:Decrypt
└── NO
    └── Confirm explicitly in checklist: [✓] SSE-KMS: Disabled
```

### Worked example — on-demand stream with 2 enhanced fan-out consumers and SSE-KMS

```text
KINESIS_STREAM: telemetry-ingest (arn:aws:kinesis:us-east-1:123456789012:stream/telemetry-ingest)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Stream name: telemetry-ingest
  [✓] Stream mode: ON_DEMAND
  [✓] Shard count: N/A (on-demand auto-scales)
  [✓] Retention period: 168 hours (7 days)
  [✓] Enhanced fan-out consumer 1: realtime-processor
      (arn:aws:kinesis:us-east-1:123456789012:stream/telemetry-ingest/consumer/realtime-processor:1620000000)
  [✓] Enhanced fan-out consumer 2: anomaly-detector
      (arn:aws:kinesis:us-east-1:123456789012:stream/telemetry-ingest/consumer/anomaly-detector:1630000000)
  [✓] SSE-KMS: enabled (key arn:aws:kms:us-east-1:123456789012:key/abcd1234-5678-90ef-1234-567890abcdef,
      alias/kinesis/telemetry-ingest)
  [✓] KMS key policy: permits kinesis.amazonaws.com (kms:GenerateDataKey, kms:Decrypt)
  [✓] Producer IAM: EC2-producer-role → kinesis:PutRecord, PutRecords on
      arn:aws:kinesis:us-east-1:123456789012:stream/telemetry-ingest
      + kms:GenerateDataKey on KMS key ARN
  [✓] Consumer IAM (consumer 1): Lambda-processor-role → kinesis:SubscribeToShard
      on stream ARN + consumer/realtime-processor ARN + kms:Decrypt on KMS key ARN
  [✓] Consumer IAM (consumer 2): Lambda-detector-role → kinesis:SubscribeToShard
      on stream ARN + consumer/anomaly-detector ARN + kms:Decrypt on KMS key ARN
  [✓] CloudWatch alarm: IteratorAgeMilliseconds > 300000 for 3 periods →
      arn:aws:sns:us-east-1:123456789012:alerts-topic
  [✓] CloudWatch alarm: N/A (on-demand — no WriteProvisionedThroughputExceeded)
  [✓] Resource policy: Same account (no cross-account resource policy needed)
  [✓] Tags: Environment=production, Service=telemetry, Team=data-platform
VERIFICATION_COMMANDS:
  aws kinesis describe-stream-summary --stream-name telemetry-ingest --region us-east-1
  aws kinesis list-stream-consumers --stream-arn arn:aws:kinesis:us-east-1:123456789012:stream/telemetry-ingest --region us-east-1
  aws kinesis describe-stream --stream-name telemetry-ingest --query 'StreamDescription.{Encryption:EncryptionType,KeyId:KeyId}' --region us-east-1
  aws cloudwatch describe-alarms --alarm-name-prefix "Kinesis-telemetry-ingest" --region us-east-1
  aws kms describe-key --key-id alias/kinesis/telemetry-ingest --region us-east-1
  aws iam simulate-principal-policy --policy-source-arn arn:aws:iam::123456789012:role/Lambda-processor-role --action-names kinesis:SubscribeToShard kms:Decrypt --output json
```

## Error handling

Per-error deep dives moved verbatim to `references/error-handling.md`
(load on demand).

## References (load on demand)

- [`references/advanced-patterns.md`](references/advanced-patterns.md) — dependency graph, provisioned/on-demand cost crossover, enhanced fan-out vs GetRecords, IteratorAge thresholds, stream resource policies, recent AWS features.
- [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — CloudWatch alarm setup commands (IteratorAgeMilliseconds, WriteProvisionedThroughputExceeded).
- [`references/error-handling.md`](references/error-handling.md) — error deep dives: stuck CREATING, write throttling, consumer access denied, fan-out not receiving data, SSE-KMS enable failure.
- [`references/stream-mode-and-scaling.md`](references/stream-mode-and-scaling.md) — capacity mode + auto-scaling detail.
- [`references/iam-and-encryption.md`](references/iam-and-encryption.md) — IAM policies + SSE-KMS detail.

## Domain

AWS CloudOps / Amazon Kinesis Data Streams Provisioning & Real-Time
Data Ingestion.

## AWS documentation

- **Kinesis Data Streams Developer Guide** — https://docs.aws.amazon.com/streams/latest/dev/
- **Creating a stream** — https://docs.aws.amazon.com/streams/latest/dev/amazon-kinesis-streams-add-update-streams.html
- **On-demand capacity mode** — https://docs.aws.amazon.com/streams/latest/dev/capacity-mode-swap.html
- **Enhanced fan-out** — https://docs.aws.amazon.com/streams/latest/dev/enhanced-consumers.html
- **SSE-KMS** — https://docs.aws.amazon.com/streams/latest/dev/server-side-encryption.html
- **IAM for Kinesis** — https://docs.aws.amazon.com/streams/latest/dev/controlling-access.html
- **CloudWatch metrics** — https://docs.aws.amazon.com/streams/latest/dev/monitoring-with-cloudwatch.html
- **Stream resource policies** — https://docs.aws.amazon.com/streams/latest/dev/resource-policies.html
- **Shard limits** — https://docs.aws.amazon.com/streams/latest/dev/service-sizes-and-limits.html
