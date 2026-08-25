# Advanced Patterns — sqs-throughput-optimizer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## What this skill does

Translates an SQS queue's configuration and traffic patterns into a
concrete throughput and cost-optimization recommendation with a dollar-
denominated savings estimate. The verdict is the highest-leverage action
across seven dimensions — polling strategy, batch size, visibility
timeout, message retention, DLQ redrive policy, queue type selection, and
FIFO high-throughput mode — applied in priority order. Always pairs the
recommendation with exact CLI commands.

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

### Lambda ESM notes (from Steps 1-3)

For Lambda ESM consumers, the ESM controls WaitTimeSeconds internally
(always uses long polling). Short polling findings apply to EC2/ECS/EKS
consumers calling `ReceiveMessage` directly.

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

For Lambda ESM, set `VisibilityTimeout` on the ESM (not the queue) via
`aws lambda update-event-source-mapping --uuid <uuid> --visibility-timeout 300`.
The ESM VisibilityTimeout overrides the queue default.

### Storage pricing (from Step 4)

**Storage pricing:** SQS storage is included in the per-request price —
no separate per-GB-month charge. However, long retention on high-volume
queues with consumer outages leads to message accumulation that, when
drained, generates a spike in ReceiveMessage/DeleteMessage requests.

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
