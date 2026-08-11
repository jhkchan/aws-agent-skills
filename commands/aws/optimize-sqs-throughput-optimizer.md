---
description: Optimise SQS queue throughput and cost through long polling enablement, batch API migration, visibility timeout right-sizing, message retention tuning, DLQ redrive policy adjustment, and FIFO high-throughput mode activation with monthly savings estimates.
nl_triggers:
  - "optimise SQS throughput"
  - "SQS cost optimization"
  - "SQS long polling"
  - "SQS batch size"
  - "SQS empty receives"
  - "SQS visibility timeout"
  - "SQS DLQ redrive"
  - "SQS FIFO high throughput"
  - "SQS message retention cost"
  - "SQS SSE-KMS cost"
  - "SQS FinOps savings"
  - "SQS request units"
  - "reduce SQS bill"
  - "queue throughput review"
  - "SQS queue optimization"
routes_to: sqs-throughput-optimizer
---

# /aws:optimize-sqs-throughput-optimizer

Activate the `sqs-throughput-optimizer` skill and optimize an SQS queue's
throughput and cost configuration across seven dimensions: polling
strategy, batch API adoption, visibility timeout, message retention, DLQ
redrive policy, queue type selection, and FIFO high-throughput mode.

## What it does

Reads a queue's CloudWatch metrics (NumberOfEmptyReceives,
NumberOfMessagesSent, NumberOfMessagesReceived, NumberOfMessagesDeleted,
ApproximateNumberOfMessagesVisible, ApproximateAgeOfOldestMessage),
queue attributes (ReceiveMessageWaitTimeSeconds, VisibilityTimeout,
MessageRetentionPeriod, RedrivePolicy, DeduplicationScope,
ThroughputLimit), consumer configuration (Lambda ESM batch size, EC2/ECS
poller pattern), and DLQ depth, then applies the ordered optimization
logic:

1. **Pre-flight** — data sufficiency gate. If metrics are absent or
   window < 14 days, emits NEED_MORE_INFO. If queue is dormant (0
   messages sent), emits OPTIMIZED.
2. **Polling strategy** — eliminate empty receives via long polling.
   Short polling with > 50% empty receive ratio is the #1 cost drain.
3. **Batch API tuning** — switch from single-message APIs (SendMessage,
   DeleteMessage) to batch APIs (SendMessageBatch, DeleteMessageBatch)
   to reduce request count 10x.
4. **Visibility timeout right-sizing** — set to 6× consumer processing
   p95 to eliminate phantom re-deliveries.
5. **Message retention tuning** — verify retention period matches the
   workload's data-loss tolerance (not a cost lever).
6. **DLQ redrive policy** — tune maxReceiveCount; use StartMessageMoveTask
   for batch redrive.
7. **Queue type / FIFO mode** — enable FIFO high-throughput mode for
   queues at the 300 TX/s ceiling.
8. **Impact estimation** — monthly + annual savings, assumptions
   documented.
9. **Verdict** — FURTHER_OPTIMIZATION_AVAILABLE (any dimension has a
   recommendation) or OPTIMIZED (all dimensions pass).

Emits a deterministic optimization block per queue:

```text
TARGET: <queue-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <polling>, <batch>, <visibility>, <queue type/mode>
  Proposed: <polling>, <batch>, <visibility>, <queue type/mode>
  Dimensions changed: <polling | batching | visibility | retention | redrive | queue-type>
  Confidence: <HIGH/MEDIUM/LOW> — <rationale>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
  Assumptions: <list>
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste a queue's metrics and ask any of:

- "optimise this SQS queue's throughput"
- "why is my SQS bill so high?"
- "should I enable SQS long polling?"
- "should I use SQS batch APIs?"
- "is my SQS visibility timeout too short?"
- "how do I reduce SQS empty receives?"
- "should I enable FIFO high-throughput mode?"
- "SQS queue cost optimization review"

A bare queue name + any optimization verb ("optimize this queue",
"throughput review") also routes here via the orchestrator.

## Inputs

- Queue metadata: name, queue type (Standard / FIFO), region, attributes
  (ReceiveMessageWaitTimeSeconds, VisibilityTimeout,
  MessageRetentionPeriod, RedrivePolicy, DeduplicationScope,
  ThroughputLimit).
- CloudWatch metrics (last 14-30 days):
  - `NumberOfEmptyReceives` (Sum)
  - `NumberOfMessagesSent` (Sum)
  - `NumberOfMessagesReceived` (Sum)
  - `NumberOfMessagesDeleted` (Sum)
  - `ApproximateNumberOfMessagesVisible` (Average)
  - `ApproximateAgeOfOldestMessage` (Average)
- Consumer configuration (Lambda ESM BatchSize,
  MaximumBatchingWindowInSeconds, FunctionResponseTypes, or EC2/ECS
  poller pattern).
- DLQ metrics (if redrive configured).
- Cost data from AWS Cost Explorer (optional — CloudWatch request counts
  are the primary cost basis).
- Workload context: ordering requirements, deduplication requirements,
  message size distribution, traffic patterns.

## Outputs

- One optimization block per queue.
- Confidence level with rationale.
- Estimated monthly and annual savings, broken down by dimension.
- Specific migration steps with CLI commands (set-queue-attributes,
  update-event-source-mapping, start-message-move-task).
- Throughput impact surfaced alongside cost (FIFO high-throughput mode
  may be a throughput win without dollar savings).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 3 Optimize specialist for SQS messaging cost).
- `/aws:optimize-apigateway-throttle` for API Gateway throttle and cost
  optimization (the AppIntegration family counterpart for API Gateway).
