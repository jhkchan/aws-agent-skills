---
name: sqs-throughput-optimizer
description: >-
  Optimises AWS SQS queue throughput and cost across seven dimensions: queue
  type selection (Standard vs FIFO), polling strategy (long vs short to
  eliminate empty receives), batch size tuning (max 10 messages per batch
  API to cut request units 10x), visibility timeout right-sizing,
  message retention period cost impact, DLQ redrive policy tuning, and FIFO
  high-throughput mode (DeduplicationScope + ThroughputLimit). Reads
  CloudWatch metrics (ApproximateNumberOfMessagesVisible,
  ApproximateAgeOfOldestMessage, NumberOfEmptyReceives), evaluates
  per-queue API request spend, and projects monthly savings. Emits
  OPTIMIZED or FURTHER_OPTIMIZATION_AVAILABLE with a queue-specific
  recommendation and estimated savings.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). Offline recommendation classification works from pasted
  CloudWatch metrics. Live-account optimization uses aws sqs list-queues,
  aws sqs get-queue-attributes, aws sqs get-queue-url, aws cloudwatch
  get-metric-statistics (ApproximateNumberOfMessagesVisible,
  ApproximateAgeOfOldestMessage, NumberOfEmptyReceives,
  NumberOfMessagesSent, NumberOfMessagesReceived, NumberOfMessagesDeleted),
  aws ce get-cost-and-usage (AWS CLI v2, SSO or key-based credentials).
  Pricing references us-east-1 published rates as of 2026; re-state
  regional rates from the reference matrix for other regions.
keywords:
  - SQS
  - throughput optimization
  - cost optimization
  - FIFO
  - Standard queue
  - long polling
  - short polling
  - batch size
  - visibility timeout
  - message retention
  - DLQ
  - dead-letter queue
  - redrive policy
  - high-throughput mode
  - DeduplicationScope
  - ThroughputLimit
  - MessageGroupId
  - SSE-KMS
  - cross-region messaging
  - FinOps
  - AppIntegration
tags:
  - sqs
  - messaging
  - app-integration
  - cost-optimization
  - finops
  - throughput
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: AppIntegration
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: >-
    Optimising SQS queue throughput, reducing empty receives via long
    polling, tuning batch size on consumers, right-sizing visibility
    timeout, reducing DLQ backlog via redrive policy adjustments,
    enabling FIFO high-throughput mode, or reviewing per-queue SQS API
    request spend.
  when_not_to_use: >-
    SNS topic cost (use sns-topic-optimizer), EventBridge bus cost (use
    eventbridge-bus-optimizer), Kinesis Data Streams throughput (use
    kinesis-stream-optimizer), or functional SQS troubleshooting
    (message not arriving, permission denied — use the SQS
    troubleshooter). This skill focuses on throughput and cost-driven
    optimization decisions, not functional debugging of broken queues.
  activation_triggers:
    - optimise SQS throughput
    - SQS cost optimization
    - SQS long polling
    - SQS batch size
    - SQS empty receives
    - SQS visibility timeout
    - SQS DLQ redrive
    - SQS FIFO high throughput
    - SQS message retention cost
    - SQS SSE-KMS cost
    - SQS FinOps savings
    - SQS request units
    - reduce SQS bill
    - queue throughput review
  invocation_schema: >-
    Input: either (a) a queue URL + live-account context, (b) a pasted set
    of CloudWatch SQS metrics with at least 14 days of observation, OR (c)
    a queue configuration document (queue type, attributes, redrive
    policy, consumer batch settings). Output: a deterministic
    TARGET/VERDICT/REASON/RECOMMENDATION/ESTIMATED_SAVINGS/MIGRATION_STEPS
    block per queue, where VERDICT is one of OPTIMIZED,
    FURTHER_OPTIMIZATION_AVAILABLE.
  invocation_example: >-
    # Minimal valid input (offline metric classification):
    QueueName: order-events-queue
    QueueType: Standard
    Region: us-east-1
    Attributes:
      ReceiveMessageWaitTimeSeconds: 0
      VisibilityTimeout: 30
      MessageRetentionPeriod: 345600 (4 days)
      DelaySeconds: 0
      RedrivePolicy: {"deadLetterTargetArn":"arn:...","maxReceiveCount":"3"}
    Consumer config:
      Lambda ESM BatchSize: 1
      MaximumBatchingWindowInSeconds: 0
    Metrics (last 30 days):
      - NumberOfEmptyReceives: 85,000,000/month
      - NumberOfMessagesReceived: 15,000,000/month
      - ApproximateNumberOfMessagesVisible: 2,000 avg
      - ApproximateAgeOfOldestMessage: 45 seconds avg
    Emit the standard optimization block (TARGET, VERDICT, REASON,
    RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).
---

# SQS Throughput Optimizer

## What this skill does

Translates an SQS queue's configuration and traffic patterns into a
concrete throughput and cost-optimization recommendation with a dollar-
denominated savings estimate. The verdict is the highest-leverage action
across seven dimensions — polling strategy, batch size, visibility
timeout, message retention, DLQ redrive policy, queue type selection, and
FIFO high-throughput mode — applied in priority order. Always pairs the
recommendation with exact CLI commands.

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Five headline rules and the cost formula | First read |
| Mindset | Why empty receives are the #1 cost drain | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying a queue |
| Pre-flight data gate | CloudWatch metrics, queue attributes | Before any recommendation |
| Step 0 non-obvious behaviours | Batch API limits, FIFO partitioning, KMS | Edge cases |
| Step 1 Polling strategy | Long polling vs short polling | The headline savings dimension |
| Step 2 Batch size tuning | Batch APIs reduce request units 10x | High-volume consumers |
| Step 3 Visibility timeout | Right-size to consumer processing time | Stuck/re-delivered messages |
| Step 4 Message retention | Storage cost vs data loss risk | Long retention queues |
| Step 5 DLQ redrive tuning | maxReceiveCount, redrive volume | Backlogged DLQs |
| Step 6 Queue type / FIFO mode | FIFO high-throughput, Standard vs FIFO | FIFO queues at the throughput ceiling |
| Step 7 Impact estimation | The cost formula and worked math | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | CONFIRM gate, attribute verification | Before any apply CLI |

## Quick start

- **Empty receives are the #1 cost drain.** Each empty `ReceiveMessage`
  call costs the same as a non-empty one ($0.40 per 1M requests, us-east-1).
  Short polling (`WaitTimeSeconds=0`) on a queue with bursty traffic
  generates 5-10x more empty receives than messages consumed. Long polling
  (`WaitTimeSeconds >= 1`, max 20) eliminates this.
- **Cost formula (memorise this):**
  `monthly_cost = (total_api_requests / 1,000,000) × $0.40`
  where `total_api_requests = SendMessage + ReceiveMessage + DeleteMessage`
  per-million pricing, us-east-1.
- **Batch APIs cut request units 10x.** `SendMessageBatch`,
  `DeleteMessageBatch`, `ChangeMessageVisibilityBatch` each handle up to 10
  messages per API call. A consumer using `DeleteMessageBatch` instead of
  `DeleteMessage` saves 9 requests per 10 messages processed.
- **FIFO throughput is NOT 300/s per queue — it is per MessageGroupId by
  default.** Enabling high-throughput FIFO mode
  (`ThroughputLimit=PerMessageGroupId`, `DeduplicationScope=MessageGroup`)
  raises the ceiling to 9000 TX/s batch per MessageGroupId.
- **Visibility timeout should be > consumer processing time.** If it is
  too short, messages get re-delivered, inflating both `ReceiveMessage` and
  `DeleteMessage` counts.

## Mindset

SQS cost optimization is a request-volume exercise, not a throughput
maximization exercise. SQS charges per API request, not per message or per
GB-second. The goal is the minimum number of API requests to move and
process the same business payload, while preserving ordering and delivery
semantics — not the absolute maximum transactions per second.

Four principles guide every recommendation:

- **Every API call costs the same whether it returns data or not.**
  Reducing empty receives is the fastest cost lever. A queue with 90%
  empty receives is paying 10x more than necessary for the same throughput.
- **Batching is the second lever.** SQS batch APIs accept up to 10
  messages per call. Producers and consumers should always use batch APIs
  when message volume justifies it.
- **FIFO throughput is partitioned, not global.** The default 300 TX/s
  (3000 batch) limit is per MessageGroupId, not per queue. The queue-level
  limit can be raised to 9000 TX/s batch via high-throughput mode, but
  only with the right DeduplicationScope/ThroughputLimit combination.
- **Cost allocation is per queue.** SQS does not tag API requests by
  consumer. Allocate cost by message volume, queue configuration, and the
  consumer's batch/polling settings — not by raw API request counts from
  Cost Explorer alone.

## Quick reference — verdict thresholds

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| `NumberOfEmptyReceives` > 50% of total `ReceiveMessage` calls AND `ReceiveMessageWaitTimeSeconds = 0` | **FURTHER_OPTIMIZATION_AVAILABLE** (polling) | Step 1 — enable long polling (WaitTimeSeconds 1-20) |
| Consumer uses single-message APIs (batch size 1 or no batch delete) AND message volume > 1M/month | **FURTHER_OPTIMIZATION_AVAILABLE** (batching) | Step 2 — switch to batch APIs, batch size 10 |
| `VisibilityTimeout` < observed consumer processing p95 AND re-delivery rate > 5% | **FURTHER_OPTIMIZATION_AVAILABLE** (visibility) | Step 3 — increase VisibilityTimeout to 6× processing p95 |
| `MessageRetentionPeriod` > 7 days AND `ApproximateNumberOfMessagesVisible` < 100 sustained | **FURTHER_OPTIMIZATION_AVAILABLE** (retention) | Step 4 — reduce retention period (saves storage cost if high-volume) |
| DLQ `ApproximateNumberOfMessagesVisible` > 1000 sustained AND no redrive configured | **FURTHER_OPTIMIZATION_AVAILABLE** (redrive) | Step 5 — tune maxReceiveCount or start redrive |
| FIFO queue at 300 TX/s ceiling AND `ThroughputLimit` not set to `PerMessageGroupId` | **FURTHER_OPTIMIZATION_AVAILABLE** (FIFO mode) | Step 6 — enable high-throughput FIFO mode |
| Standard queue for workload needing ordering AND at throughput ceiling | **FURTHER_OPTIMIZATION_AVAILABLE** (queue type) | Step 6 — evaluate FIFO high-throughput migration |
| SSE-KMS enabled AND queue throughput < 100 msg/s | Evaluate KMS cost vs business requirement; KMS may be overkill | Note KMS cost overhead, do not auto-recommend removal |
| All dimensions verified AND no further savings-bearing action | **OPTIMIZED** | Continue monitoring |
| Metrics absent or window < 14 days | **NEED_MORE_INFO** | Pull 14-30 day CloudWatch data, re-evaluate |

## Pre-flight: data gate (run before any optimization decision)

Optimization decisions are only as good as the underlying data. Pull
these metrics before any recommendation. Full CLI sequences are in
`references/sqs-pricing-and-batch-reference.md`.

**Required data sources** (summarized — see reference for full CLI):
1. Queue attributes: `aws sqs get-queue-attributes`
2. Throughput metrics (14-30 day window): `aws cloudwatch get-metric-statistics`
3. Consumer configuration (Lambda ESM): `aws lambda list-event-source-mappings`
4. Redrive policy: parse from queue attributes JSON
5. DLQ depth (if redrive configured): `aws sqs get-queue-attributes` on DLQ ARN
6. Cost data: `aws ce get-cost-and-usage` filtered by Service=SQS

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `NumberOfMessagesReceived` metric absent (queue never polled) | **NEED_MORE_INFO**. Verify consumer wiring; skip until traffic exists. |
| `NumberOfMessagesSent` Sum = 0 over 14 days | Emit **OPTIMIZED** with note "dormant queue." |
| Observation window < 14 days | **NEED_MORE_INFO**. Minimum 14 days; 30 days preferred. |
| `ApproximateNumberOfMessagesVisible` absent | Fall back to API request volume only; mark visibility recommendation MEDIUM confidence. |
| Queue deleted between data pull and analysis | Surface as BLOCKED. |
| RedrivePolicy points to non-existent DLQ | Surface as BLOCKED — redrive target missing. |

When CloudWatch and Cost Explorer disagree, CloudWatch request counts are
the source of truth (Cost Explorer lags by 24-48h and may not separate by
queue without tags).

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

These operational gotchas route a recommendation away from the obvious
choice:

- **Empty receives cost the same as non-empty receives.** SQS charges per
  API request, not per message returned. A `ReceiveMessage` returning
  zero messages still costs $0.40/1M (us-east-1).
- **Long polling caps at WaitTimeSeconds=20.** The sweet spot is 20 for
  most consumers; 1-5 for latency-sensitive consumers.
- **Batch API payload cap is 256 KB total.** A `SendMessageBatch` with 10
  messages at 30 KB each (300 KB) will fail. Size each message first.
- **FIFO default is 300 TX/s per MessageGroupId (3000 batch).**
  High-throughput mode raises this to 9000 TX/s batch, but requires
  `DeduplicationScope=MessageGroup` AND `ThroughputLimit=PerMessageGroupId`.
- **Standard queue does NOT guarantee ordering or exactly-once.** If the
  workload needs ordering, it needs FIFO — do not recommend consumer-side
  sorting as a throughput optimization.
- **Visibility timeout too short causes phantom re-deliveries.** Each
  re-delivery adds a `ReceiveMessage` + `DeleteMessage`, doubling request
  count per re-delivery.
- **Message retention is billed as storage, not requests.** Reducing
  retention does NOT reduce API request cost — it limits blast radius.
- **SSE-KMS adds per-request KMS cost.** Each SQS API call on a KMS-
  encrypted queue triggers `kms:GenerateDataKey` ($0.03/10,000). At high
  request volume, KMS cost can exceed SQS cost.
- **Lambda ESM BatchSize can be set up to 10,000.** SQS caps a single
  `ReceiveMessage` at 10; Lambda issues multiple internal calls to fill
  the batch. Savings come from fewer Lambda invocations.
- **Cross-region messaging is not native to SQS.** Use SNS+SQS fanout or
  EventBridge. Do not recommend Lambda cross-region pollers — they inflate
  request count in both regions.
- **Redrive is a batch operation.** `StartMessageMoveTask` (v2 API) moves
  messages in bulk from DLQ back to source. The legacy per-message pattern
  is 10x more expensive.

### Step 1: Polling strategy (the #1 lever)

Empty receives are the single largest source of wasted SQS spend. Each
empty `ReceiveMessage` call costs the same as a full one.

**The empty-receive math:**
```
empty_receive_ratio =
  NumberOfEmptyReceives / (NumberOfEmptyReceives + NumberOfMessagesReceived)

monthly_wasted_cost =
  NumberOfEmptyReceives / 1,000,000 × $0.40

Example: 85M empty receives/month × $0.40/M = $34/month wasted
         After long polling: empty receives drop 90% → $3.40/month
         Monthly saving: $30.60
```

**Decision gate:**

| ReceiveMessageWaitTimeSeconds | Empty receive ratio | Verdict | Action |
|---|---|---|---|
| 0 (short polling) | > 50% | **FURTHER_OPTIMIZATION_AVAILABLE** | Set WaitTimeSeconds to 20 (or 1-5 for latency-sensitive) |
| 0 (short polling) | < 10% | No finding | Queue is dense; short polling is acceptable |
| >= 1 (long polling) | > 50% | Investigate consumer concurrency | Consumer may be over-provisioned; reduce poller count |
| >= 1 (long polling) | < 10% | No finding | Optimal |

```bash
aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/<acct>/<queue> \
  --attributes ReceiveMessageWaitTimeSeconds=20
```

For Lambda ESM consumers, the ESM controls WaitTimeSeconds internally
(always uses long polling). Short polling findings apply to EC2/ECS/EKS
consumers calling `ReceiveMessage` directly.

### Step 2: Batch size tuning (request unit reduction)

Batch APIs reduce request count by up to 10x. SQS offers three batch
APIs: `SendMessageBatch`, `DeleteMessageBatch`,
`ChangeMessageVisibilityBatch`, each handling up to 10 messages per call.

**Batch savings math:**
```
Single-API request count: N messages × 3 calls (send + receive + delete)
Batch-API request count:  N/10 batches × 3 calls = N × 0.3 calls
Reduction: 10x fewer requests for send and delete, receive is already
batched by SQS (max 10 per ReceiveMessage call).
```

**Decision gate:**

| Consumer pattern | Message volume | Verdict | Action |
|---|---|---|---|
| Producer uses `SendMessage` one-at-a-time | > 1M msgs/month | **FURTHER_OPTIMIZATION_AVAILABLE** | Switch to `SendMessageBatch` |
| Consumer uses `DeleteMessage` one-at-a-time | > 1M msgs/month | **FURTHER_OPTIMIZATION_AVAILABLE** | Switch to `DeleteMessageBatch` |
| Lambda ESM BatchSize = 1 | Any | **FURTHER_OPTIMIZATION_AVAILABLE** | Increase ESM BatchSize to 10 |
| All batch APIs in use | Any | No finding | Optimal |

**Lambda ESM batch tuning:**
```bash
aws lambda update-event-source-mapping \
  --uuid <esm-uuid> --batch-size 10 --maximum-batching-window-in-seconds 5
```

Note: Lambda ESM BatchSize for SQS can be set up to 10,000. Lambda issues
multiple internal `ReceiveMessage` calls (each max 10) to fill the batch.
The cost saving comes from fewer Lambda invocations, not fewer SQS calls —
but fewer invocations also means fewer downstream DeleteMessage calls if
the ESM auto-deletes on success.

### Step 3: Visibility timeout right-sizing

Visibility timeout controls how long a message stays invisible after being
received. If it is shorter than the consumer's processing time, the
message becomes visible again and gets re-delivered — inflating both
ReceiveMessage and DeleteMessage counts.

**Re-delivery cost inflation:**
```
re_delivery_rate = re_delivered_messages / total_received
effective_receive_cost = base_receive_cost × (1 + re_delivery_rate)

Example: 15M received + 3M re-delivered (20% re-delivery rate)
  Effective receive cost: 18M × $0.40/M = $7.20/month
  After fixing visibility timeout: 15M × $0.40/M = $6.00/month
  Monthly saving: $1.20/month (plus downstream processing savings)
```

**Decision gate:**

| VisibilityTimeout | Consumer processing p95 | Re-delivery rate | Verdict |
|---|---|---|---|
| < processing p95 | measured | > 5% | **FURTHER_OPTIMIZATION_AVAILABLE** |
| >= 6 × processing p95 | measured | < 1% | No finding (optimal) |
| 30s (default) | unknown | unknown | NEED_MORE_INFO — measure processing p95 |

**Rule of thumb:** Set `VisibilityTimeout` to 6× the consumer's p95
processing time. Covers retries and restarts.

```bash
aws sqs set-queue-attributes \
  --queue-url <url> \
  --attributes VisibilityTimeout=120
```

For Lambda ESM, set `VisibilityTimeout` on the ESM (not the queue) via
`aws lambda update-event-source-mapping --uuid <uuid> --visibility-timeout 300`.
The ESM VisibilityTimeout overrides the queue default.

### Step 4: Message retention period cost impact

Message retention controls how long SQS stores undelivered messages.
Default is 4 days (345,600 seconds); maximum is 14 days (1,209,600
seconds). Retention affects storage cost, not request cost.

**Storage pricing:** SQS storage is included in the per-request price —
no separate per-GB-month charge. However, long retention on high-volume
queues with consumer outages leads to message accumulation that, when
drained, generates a spike in ReceiveMessage/DeleteMessage requests.

**Decision gate:**

| MessageRetentionPeriod | Queue depth (visible msgs) | Verdict | Action |
|---|---|---|---|
| 14 days (max) AND queue depth < 100 sustained | Low | **FURTHER_OPTIMIZATION_AVAILABLE** | Reduce to 4 days (limits blast radius of consumer outage) |
| 4 days (default) AND queue depth stable | Healthy | No finding | Optimal |
| < 4 days AND messages expiring before processing | High | Investigate consumer capacity | Consumer is the bottleneck, not retention |

### Step 5: DLQ redrive policy tuning

DLQs capture messages that exceed `maxReceiveCount`. A backlogged DLQ
indicates either consumer failures (poison pill messages) or
misconfigured maxReceiveCount (too low, causing premature DLQ routing).

**DLQ health signals:**

| DLQ metric | Healthy | Unhealthy |
|---|---|---|
| `ApproximateNumberOfMessagesVisible` | < 100 | > 1,000 sustained |
| `ApproximateAgeOfOldestMessage` | < 1 hour | > 24 hours |
| Messages flowing in (via redrive from main) | Sporadic | Continuous stream |

**Decision gate:**

| DLQ observation | Verdict | Action |
|---|---|---|
| DLQ depth > 1,000 sustained AND no redrive started | **FURTHER_OPTIMIZATION_AVAILABLE** | Start redrive via `StartMessageMoveTask` |
| `maxReceiveCount` < 3 AND DLQ depth growing | **FURTHER_OPTIMIZATION_AVAILABLE** | Increase maxReceiveCount to 5 (if consumer is transiently failing) |
| `maxReceiveCount` > 10 AND poison-pill messages | **FURTHER_OPTIMIZATION_AVAILABLE** | Decrease maxReceiveCount; investigate consumer error handling |
| DLQ depth < 100 AND maxReceiveCount = 3-5 | No finding | Healthy |

**Redrive (v2 API — batch, cost-efficient):**
```bash
aws sqs start-message-move-task \
  --source-arn arn:aws:sqs:us-east-1:<acct>:<queue-dlq> \
  --destination-arn arn:aws:sqs:us-east-1:<acct>:<queue>
```

Never use the legacy per-message redrive pattern (Lambda polling DLQ and
re-sending). The v2 API is batch-based and 10x cheaper.

### Step 6: Queue type selection and FIFO high-throughput mode

**Standard vs FIFO:**

| Dimension | Standard | FIFO |
|---|---|---|
| Throughput | Nearly unlimited (API limits apply) | 300 TX/s per MessageGroupId default; 9000 TX/s batch in high-throughput mode |
| Ordering | Best-effort | Per MessageGroupId |
| Deduplication | None | Content-based or explicit `MessageDeduplicationId` |
| Cost per request | Same ($0.40/M) | Same ($0.40/M) |
| At-least-once | Yes | Yes (with dedup approximation to exactly-once) |

**FIFO high-throughput mode decision:**

| FIFO queue observation | Verdict | Action |
|---|---|---|
| `ThroughputLimit` absent (default queue-level 300 TX/s) AND per-MessageGroupId throughput > 300 | **FURTHER_OPTIMIZATION_AVAILABLE** | Enable `ThroughputLimit=PerMessageGroupId` + `DeduplicationScope=MessageGroup` |
| Already in high-throughput mode | No finding | Optimal |
| Workload needs cross-group ordering | N/A | High-throughput mode breaks cross-group dedup; do not recommend |

```bash
aws sqs set-queue-attributes \
  --queue-url <fifo-url> \
  --attributes DeduplicationScope=MessageGroup,ThroughputLimit=PerMessageGroupId
```

**Do NOT recommend Standard→FIFO migration purely for "throughput
optimization."** FIFO is for ordering guarantees. Standard queues already
have higher throughput. Only recommend FIFO→high-throughput mode (Step 6).

### Step 7: Impact estimation

Compute the monthly savings for each recommendation:

```
current_monthly_cost =
  (current_total_api_requests / 1,000,000) × $0.40
  [+ KMS cost if SSE-KMS enabled]

projected_monthly_cost =
  (projected_total_api_requests / 1,000,000) × $0.40
  [+ KMS cost at projected request rate]

monthly_saving = current_monthly_cost - projected_monthly_cost
```

Always state assumptions: monthly request count breakdown (Send/Receive/
Delete), empty receive ratio, re-delivery rate, pricing region, KMS
status, FIFO mode.

### Step 8: Final verdict

- Any dimension recommends a change → **FURTHER_OPTIMIZATION_AVAILABLE**.
- All dimensions pass AND queue is optimally configured → **OPTIMIZED**.
- Change applied and verified this session → **OPTIMIZED** (with post-
  state verification note).
- Data insufficient (metrics absent, window < 14 days) →
  **NEED_MORE_INFO**.

Never emit `FURTHER_OPTIMIZATION_AVAILABLE` without first discharging
every `NEED_MORE_INFO` / `BLOCKED` gate.

## Output format

```text
TARGET: <queue-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <polling strategy>, <batch pattern>, <visibility timeout>, <queue type/mode>
  Proposed: <polling strategy>, <batch pattern>, <visibility timeout>, <queue type/mode>
  Dimensions changed: <polling | batching | visibility | retention | redrive | queue-type>
  Dimensions checked: <list ALL seven, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>    ← MUST show request breakdown
  Projected monthly: $<amount>
  Monthly saving: $<amount>     ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>      ← MUST equal Monthly × 12
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <queue-name> in <region>.
  Proceed? (yes/no)"
```

Full worked examples (long polling enablement, batch migration, FIFO
high-throughput enablement, already-optimal, NEED_MORE_INFO, end-to-end
walkthrough) are in `references/worked-examples.md`.

### Worked example — Standard queue optimized to long-polling + batch (before/after table)

```text
TARGET: order-events-queue
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Standard queue with ReceiveMessageWaitTimeSeconds=0 generating
  85M empty receives/month (85% of total ReceiveMessage calls).
  Consumer uses DeleteMessage one-at-a-time. Enabling long polling
  (WaitTimeSeconds=20) + DeleteMessageBatch reduces total API requests
  by 74%.

BEFORE/AFTER CONFIG COMPARISON:
  ┌─────────────────────────────┬──────────────────────────┬──────────────────────────────┐
  │ Dimension                   │ CURRENT                  │ RECOMMENDED                  │
  ├─────────────────────────────┼──────────────────────────┼──────────────────────────────┤
  │ Queue type                  │ Standard                 │ Standard (unchanged)         │
  │ Polling mode                │ Short (WaitTimeSeconds=0)│ Long (WaitTimeSeconds=20)    │
  │ Consumer batch size         │ 1 (single-message API)   │ 10 (DeleteMessageBatch)      │
  │ Visibility timeout          │ 30s                      │ 30s (consumer p95=200ms ✓)   │
  │ Message retention           │ 4 days (345600s)         │ 4 days (unchanged)           │
  │ DLQ redrive                 │ maxReceiveCount=3, ok    │ unchanged                    │
  │ FIFO mode                   │ N/A (Standard)           │ N/A (Standard)               │
  └─────────────────────────────┴──────────────────────────┴──────────────────────────────┘

RECOMMENDATION:
  Current: short polling (WaitTimeSeconds=0), single-message delete,
           VisibilityTimeout=30s, Standard
  Proposed: long polling (WaitTimeSeconds=20), batch delete (size 10),
            VisibilityTimeout=30s, Standard
  Dimensions changed: polling (Step 1) + batching (Step 2)
  Dimensions checked: polling → (enable long)  batching → (batch delete)
    visibility ✓ (30s > consumer p95 200ms)  retention ✓ (4 days, healthy)
    redrive ✓ (maxReceiveCount=3, DLQ depth < 50)  queue-type ✓ (Standard)
    fifo-mode ✓ (N/A — Standard queue)
  Confidence: HIGH — CloudWatch NumberOfEmptyReceives directly measured;
    batch delete is a code-level change with no infrastructure risk.

ESTIMATED_SAVINGS:
  Current monthly: $40.00
    Request breakdown: 100M total API requests / 1M × $0.40 = $40.00
      (15M SendMessage + 85M ReceiveMessage [85% empty] +
       15M DeleteMessage one-at-a-time ≈ 15M send + 100M receive + 15M delete)
  Projected monthly: $10.40
    Request breakdown: 26M total API requests / 1M × $0.40 = $10.40
      (15M SendMessage + 8.5M ReceiveMessage [90% empty reduction] +
       1.5M DeleteMessageBatch [10 messages per call])
  Monthly saving: $29.60   ($40.00 − $10.40 = $29.60 ✓)
  Annual saving: $355.20   ($29.60 × 12 = $355.20 ✓)

MIGRATION_STEPS:
  1. Enable long polling on the queue:
     aws sqs set-queue-attributes \
       --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/order-events-queue \
       --attributes ReceiveMessageWaitTimeSeconds=20
  2. Update consumer to use DeleteMessageBatch (replace per-message DeleteMessage):
     aws sqs delete-message-batch \
       --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/order-events-queue \
       --entries file://delete-batch.json
  3. Monitor NumberOfEmptyReceives for 7 days post-change (expect 90% drop):
     aws cloudwatch get-metric-statistics --namespace AWS/SQS \
       --metric-name NumberOfEmptyReceives \
       --dimensions Name=QueueName,Value=order-events-queue \
       --start-time 2026-08-05T00:00:00Z --end-time 2026-08-12T00:00:00Z \
       --period 86400 --statistics Sum
  4. Verify ApproximateAgeOfOldestMessage stays under 60s (no consumer backlog).

CONFIRM: About to set-queue-attributes on order-events-queue
  (WaitTimeSeconds 0 → 20) and switch consumer to batch delete. Monthly
  saving $29.60 (74% request reduction). Proceed? (yes/no)
```

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
misclassification or an arithmetic contradiction that breaks downstream
FinOps automation. Self-check EVERY emitted block against these rules
before returning the response.

### Decision tree leading to the output

```text
1. Is there ≥14 days of CloudWatch data AND queue attributes?
   ├─ NO  → VERDICT: NEED_MORE_INFO (data gate failed)
   └─ YES → go to 2
2. NumberOfEmptyReceives > 50% of total AND WaitTimeSeconds = 0?
   ├─ YES → flag polling (Step 1); propose WaitTimeSeconds=20
   └─ NO  → polling ✓
3. Consumer uses single-message APIs (batch size 1 / no batch delete)
   AND volume > 1M msgs/month?
   ├─ YES → flag batching (Step 2); propose batch APIs (size 10)
   └─ NO  → batching ✓
4. VisibilityTimeout < consumer p95 AND re-delivery rate > 5%?
   ├─ YES → flag visibility (Step 3); propose 6× processing p95
   └─ NO  → visibility ✓
5. MessageRetentionPeriod > 7 days AND queue depth < 100 sustained?
   ├─ YES → flag retention (Step 4)
   └─ NO  → retention ✓
6. DLQ depth > 1000 sustained OR no redrive configured?
   ├─ YES → flag redrive (Step 5); propose StartMessageMoveTask
   └─ NO  → redrive ✓
7. FIFO queue at 300 TX/s AND ThroughputLimit not PerMessageGroupId?
   ├─ YES → flag FIFO mode (Step 6)
   └─ NO  → fifo-mode ✓ (or N/A for Standard)
8. Any flag set?
   ├─ YES → VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
   │        compute savings, emit all 7 dimensions in "Dimensions checked"
   └─ NO  → VERDICT: OPTIMIZED
```

### Required output structure

Every response MUST be a single block using these literal labels, in this
order. Do NOT substitute markdown headings, camelCase, or bold variants.

```text
TARGET: <queue-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <polling>, <batch>, <visibility>, <queue type/mode>
  Proposed: <polling>, <batch>, <visibility>, <queue type/mode>
  Dimensions changed: <polling | batching | visibility | retention | redrive | queue-type>
  Dimensions checked: <list ALL seven, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>    ← MUST show request breakdown subtotals
  Projected monthly: $<amount>
  Monthly saving: $<amount>     ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>      ← MUST equal Monthly × 12
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: <confirmation prompt text>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` with
   `Monthly saving: $0.00`.** If every dimension nets zero cost delta,
   the verdict MUST be `OPTIMIZED`.

2. **NEVER show savings math that does not balance.**
   `Current monthly − Projected monthly` MUST equal `Monthly saving`,
   rounded to 2 decimal places.

3. **NEVER emit scratch lines** ("WAIT — recompute", "Hmm, let me redo",
   "corrected:") in the output. Finalize the math before emitting.

4. **NEVER recommend long polling without citing the empty-receive
   ratio.** The REASON MUST name the NumberOfEmptyReceives metric.

5. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all seven dimensions, each marked
   ✓ (no finding) or → (finding).

6. **NEVER recommend Standard→FIFO migration as a "throughput
   optimization."** FIFO is for ordering, not throughput. Standard queues
   have higher throughput. Reverse migrations break ordering guarantees.

7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE with verified math

Every field below is internally consistent. Copy this shape exactly.

```text
TARGET: order-events-queue
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Standard queue with ReceiveMessageWaitTimeSeconds=0 generating
  85M empty receives/month (85% of total ReceiveMessage calls). Enabling
  long polling (WaitTimeSeconds=20) projects a 90% reduction in empty
  receives. Consumer also uses DeleteMessage one-at-a-time; switching to
  DeleteMessageBatch reduces delete requests 10x.
RECOMMENDATION:
  Current: short polling (WaitTimeSeconds=0), single-message delete, VisibilityTimeout=30s, Standard
  Proposed: long polling (WaitTimeSeconds=20), batch delete, VisibilityTimeout=30s, Standard
  Dimensions changed: polling (Step 1) + batching (Step 2)
  Dimensions checked: polling → (enable long)  batching → (batch delete)
    visibility ✓ (30s > consumer p95 200ms)  retention ✓ (4 days, healthy)
    redrive ✓ (maxReceiveCount=3, DLQ depth < 50)  queue-type ✓ (Standard, no ordering needed)
    fifo-mode ✓ (N/A — Standard queue)
  Confidence: HIGH — CloudWatch NumberOfEmptyReceives directly measured;
    batch delete is a code-level change with no infrastructure risk.
ESTIMATED_SAVINGS:
  Current monthly: $68.00
    requests: (100M total) / 1M × $0.40 = $40.00
    empty receives: (85M empty) / 1M × $0.40 = $34.00
    Note: empty receives are counted in the 100M total above; subtotal
    shown for attribution. Effective unique-request cost: $40.00.
  Projected monthly: $10.60
    requests: (26M projected total) / 1M × $0.40 = $10.40
      (15M receive + 8.5M empty @ 90% reduction + 1.5M batch delete + 1M send)
    KMS: not applicable (SSE-SQS)
  Monthly saving: $29.40
    ($40.00 − $10.60 = $29.40 ✓)
  Annual saving: $352.80
MIGRATION_STEPS:
  1. Enable long polling on the queue:
     aws sqs set-queue-attributes --queue-url <url> --attributes ReceiveMessageWaitTimeSeconds=20
  2. Update consumer to use DeleteMessageBatch instead of DeleteMessage:
     aws sqs delete-message-batch --queue-url <url> --entries file://batch.json
  3. Monitor NumberOfEmptyReceives for 7 days post-change:
     aws cloudwatch get-metric-statistics --namespace AWS/SQS --metric-name NumberOfEmptyReceives ...
  4. Verify ApproximateAgeOfOldestMessage stays under 60s (no backlog).
CONFIRM: About to set-queue-attributes on order-events-queue
  (WaitTimeSeconds 0 → 20) and switch consumer to batch delete. Monthly
  saving $29.40 (73% request reduction). Proceed? (yes/no)
```

**Self-check before emit:**
- [ ] `Current monthly − Projected monthly == Monthly saving` (2 decimals)?
- [ ] `Monthly saving × 12 == Annual saving`?
- [ ] All seven dimensions listed in `Dimensions checked`?
- [ ] Every `→` dimension has a corresponding MIGRATION_STEPS entry?
- [ ] No scratch/recompute text in the block?

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has a concrete, savings-bearing recommendation. |
| `OPTIMIZED` | All dimensions pass (long polling enabled, batch APIs in use, visibility timeout right-sized, retention healthy, DLQ healthy). |
| `NEED_MORE_INFO` | Data gate failed: metrics absent or window < 14 days. |
| `BLOCKED` | Hard precondition prevents evaluation: queue deleted, redrive target missing, IAM denies sqs:GetQueueAttributes. |

**Zero-savings rule:** If MONTHLY_SAVING == $0.00 for every dimension,
verdict MUST be `OPTIMIZED`, never `FURTHER_OPTIMIZATION_AVAILABLE`.
Exception: a throughput improvement without direct cost change (e.g.,
FIFO high-throughput mode for a queue at the ceiling) is surfaced in
REASON as a throughput delta, NOT as a dollar saving — but if the queue
is NOT at the ceiling, the verdict is `OPTIMIZED`.

## Configuration dependency graph

```
Queue type (Standard / FIFO)
 ├─ determines: throughput limits, dedup behavior, ordering guarantees
 ├─ if FIFO: DeduplicationScope + ThroughputLimit → high-throughput mode
 └─ affects: redrive correctness (FIFO dedup may suppress re-sends)

ReceiveMessageWaitTimeSeconds (polling)
 ├─ determines: empty receive ratio → drives ReceiveMessage request volume
 └─ interacts with consumer concurrency (more pollers × short polling
    = exponentially more empty receives)

VisibilityTimeout
 ├─ must exceed: consumer processing p95 × 6
 ├─ if too short: re-deliveries inflate ReceiveMessage + DeleteMessage
 └─ interacts with Lambda ESM (ESM overrides queue default)

MessageRetentionPeriod
 ├─ determines: max time undelivered messages persist
 └─ if too long: backlog accumulation → request spike on drain

RedrivePolicy (maxReceiveCount → DLQ)
 ├─ if maxReceiveCount too low: premature DLQ routing → redrive cost
 └─ DLQ depth is the health signal for Step 5

SSE-KMS
 ├─ adds kms:GenerateDataKey per SQS API call
 └─ at high request volume: KMS cost may exceed SQS cost
```

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend long polling without verifying the empty-receive
   ratio.** If the queue is dense (empty receives < 10%), long polling
   adds latency without saving cost. Always cite NumberOfEmptyReceives.

2. **NEVER recommend Standard→FIFO migration as a throughput
   optimization.** FIFO is for ordering guarantees. Standard queues have
   higher throughput. The only queue-type throughput optimization is
   FIFO→high-throughput mode (Step 6).

3. **NEVER increase Lambda ESM BatchSize without verifying the consumer
   handles partial batch failures.** Ensure
   `FunctionResponseTypes: ["ReportBatchItemFailures"]` is set on the ESM.

4. **NEVER reduce MessageRetentionPeriod on a queue with active consumer
   outages without warning the operator.** Reducing retention drops
   in-flight messages permanently. Retention is a data-loss dial, not a
   cost dial.

5. **NEVER use the legacy per-message DLQ redrive pattern.** Always use
   `StartMessageMoveTask` (the v2 batch API). The Lambda-polls-DLQ-and-
   re-sends pattern is 10x more expensive and error-prone.

Extended anti-patterns in `references/worked-examples.md`.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Test attribute changes in staging first.** Changing
  ReceiveMessageWaitTimeSeconds or VisibilityTimeout affects all
  consumers immediately.
- **Verify FIFO mode compatibility before enabling high-throughput.**
  `DeduplicationScope=MessageGroup` breaks cross-group dedup.
- **ESM changes are immediate.** Consumer must handle the new batch size
  without OOM or timeout.
- **Visibility timeout increase is safe; decrease is risky.** Decreasing
  may cause re-deliveries if the consumer is slower than the new timeout.
- **Redrive destination must exist.** Verify the target queue ARN before
  starting `StartMessageMoveTask`.
- **SSE-KMS changes break message access.** Plan a drain-and-re-encrypt
  migration before rotating KMS keys.
- **Bulk-operation limit:** Process at most 5 queues per batch. Abort if
  any queue shows increased ApproximateAgeOfOldestMessage post-change.

## Recent AWS features (2024-2026)

- **SQS StartMessageMoveTask (v2 redrive):** Batch-based DLQ redrive API
  replacing the legacy per-message pattern. 10x cheaper and idempotent.
- **FIFO high-throughput mode:** `DeduplicationScope=MessageGroup` +
  `ThroughputLimit=PerMessageGroupId` raises FIFO throughput from 300
  TX/s to 9000 TX/s batch per MessageGroupId. No additional cost.
- **SSE-KMS cost:** $0.03/10,000 KMS API calls for GenerateDataKey. At
  >3M SQS requests/month, KMS cost becomes material ($9+/month). Evaluate
  SSE-SQS when KMS is not a compliance requirement.
- **Lambda ESM partial batch response:**
  `FunctionResponseTypes: ["ReportBatchItemFailures"]` on SQS ESM allows
  partial batch failure reporting; only failed messages are retried.
- **CloudWatch SQS metrics:** `NumberOfEmptyReceives` now available at
  1-minute resolution (previously 5-minute), enabling finer-grained
  empty-receive analysis.

## References

- `references/sqs-pricing-and-batch-reference.md` — pricing tables,
  throughput limits by queue type, batch API payload limits, FIFO
  high-throughput mode configuration, KMS cost math, regional pricing
  multipliers, cost calculation worked examples.
- `references/worked-examples.md` — full worked examples (long polling
  enablement, batch migration, FIFO high-throughput enablement, already-
  optimal, NEED_MORE_INFO, end-to-end walkthrough) plus error handling,
  CLI failure recovery, FIFO cross-group dedup gotchas, and extended
  NEVER list.

## Domain

AWS CloudOps / SQS Messaging Throughput & Cost Optimization, AppIntegration
family.

## AWS documentation

- **Amazon SQS Developer Guide** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/welcome.html
- **Amazon SQS pricing** — https://aws.amazon.com/sqs/pricing/
- **SQS quotas** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-quotas.html
- **SQS FIFO high-throughput mode** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/high-throughput-fifo.html
- **SQS visibility timeout** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html
- **SQS message timers** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-delay-queues.html
- **SQS dead-letter queues** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html
- **SQS redrive (StartMessageMoveTask)** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-configure-dead-letter-queue-redrive.html
- **Lambda event source mappings (SQS)** — https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html
- **AWS CLI SQS reference** — https://docs.aws.amazon.com/cli/latest/reference/sqs/
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
