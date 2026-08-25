# Advanced patterns - SQS Dead-Letter Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Mindset

Messages accumulating in a dead-letter queue are a symptom, not a root
cause. The DLQ is doing its job — capturing messages that exceeded
maxReceiveCount. The question is WHY the messages failed processing
`maxReceiveCount` times. Senior integration engineers do not start by
clearing the DLQ; they start by inspecting the DLQ messages for the
failure pattern, checking the consumer's processing behavior against the
visibility timeout, and verifying the redrive configuration. The root
cause is almost always on the consumer side (timeout, concurrency,
error handling) or the configuration side (maxReceiveCount too low,
DLQ type mismatch), not the queue infrastructure itself.

## Philosophy

Four behaviours separate a senior SQS engineer from a generalist:

- **The poison message in FIFO is a group-level problem, not a
  message-level problem.** In a standard queue, a poison message affects
  only itself — it fails, goes to the DLQ, and other messages continue.
  In a FIFO queue, a poison message at position N blocks every message
  behind it in the same MessageGroupId. This means a single malformed
  message can stall an entire partition of work. The symptom is "the
  FIFO queue is stuck" but the root cause is one specific message.
  Always identify the MessageGroupId and check whether only that group
  is stalled while others flow normally.

- **maxReceiveCount counts attempts, not time.** A maxReceiveCount of 3
  does not mean "3 minutes" or "3 processing cycles." It means the
  message was received 3 times (via `ReceiveMessage`) and not deleted.
  With a short visibility timeout and fast polling, a message can hit
  maxReceiveCount=3 in under 10 seconds. With a long visibility timeout,
  the same count takes minutes. The interaction between maxReceiveCount
  and visibility timeout determines the real-world time-to-DLQ.

- **The visibility timeout must exceed the consumer's processing time,
  or messages are re-delivered during processing.** If the visibility
  timeout is 30 seconds and the consumer takes 45 seconds to process a
  message, the message becomes visible again at T+30s. Another consumer
  receives it, starts processing, and at T+45s the first consumer
  finishes and deletes it — but the second consumer is now processing
  a duplicate. With batch processing (Lambda BatchSize: 10), this
  multiplies: 10 messages all become visible at T+30s if processing
  takes longer.

- **StartMessageMoveTask (v2) is the correct API for DLQ redrive.** The
  legacy `Redrive` API is deprecated and does not support rate limiting
  or task cancellation. StartMessageMoveTask takes a SourceArn (DLQ)
  and optional DestinationArn (defaults to the source queue from the
  DLQ's redrive-allow-policy), supports `MaxNumberOfMessagesPerSecond`
  for rate limiting, and returns a `TaskHandle` for tracking and
  cancellation.

### Step 0: Non-obvious behaviours that change diagnosis

These are the operational gotchas a senior SQS engineer knows from
incident experience. Each one routes a diagnosis away from the obvious
layer to a less obvious one:

- **maxReceiveCount counts receive attempts, not minutes or processing
  failures.** Each `ReceiveMessage` that delivers a message increments
  the receive count. If the consumer receives, fails to process, and the
  message returns to the queue after the visibility timeout, the next
  receive increments the count again. A maxReceiveCount of 3 means 3
  receive attempts — which can happen in seconds (short visibility
  timeout, fast polling) or minutes (long visibility timeout).

- **A poison message in a FIFO queue blocks ALL subsequent messages in
  the same MessageGroupId.** FIFO guarantees strict ordering per
  MessageGroupId. If message N fails and goes to the DLQ, messages N+1,
  N+2, etc. cannot be delivered until N is processed (or moved to DLQ).
  Once N is in the DLQ, N+1 becomes deliverable — but if N+1 also fails
  (same code bug), the blockage continues. The symptom is "FIFO queue
  throughput dropped to zero for one partition" and the root cause is a
  specific message in a specific MessageGroupId.

- **The visibility timeout must exceed the consumer's processing time.**
  If the visibility timeout is 30s and the consumer takes 45s, the
  message becomes visible to other consumers at T+30s while the first
  consumer is still processing. This causes: (a) duplicate processing,
  (b) accelerated receive-count increment (the duplicate receive counts
  as another attempt), and (c) premature DLQ migration. For Lambda
  consumers with BatchSize > 1, the processing time for the entire batch
  must be within the visibility timeout.

- **Lambda event source mapping has its own visibility timeout and
  batching settings that override the queue's.** The event source
  mapping's `VisibilityTimeout` (default 30s) takes precedence over the
  queue's `VisibilityTimeout` attribute. Operators who set the queue's
  visibility timeout to 120s but leave the event source mapping at the
  default 30s still see premature re-delivery.

- **SQS messages have a maximum size of 256 KB.** Messages exceeding
  256 KB are rejected by `SendMessage` / `SendMessageBatch` with an
  error. However, extended client libraries (Java, Python) can use S3
  for payloads > 256 KB via the Extended Client Library, which stores
  the payload in S3 and passes a pointer in the SQS message. If the
  consumer does not use the Extended Client Library, it receives only
  the pointer and cannot process the actual payload.

- **The DLQ for a FIFO queue MUST also be FIFO.** A standard DLQ
  attached to a FIFO source queue causes redrive failures and message
  ordering loss. The DLQ must have `.fifo` suffix and `FifoQueue: true`.
  Mixing types is a common infrastructure-as-code error.

- **StartMessageMoveTask is the v2 API for DLQ redrive.** It replaces
  the deprecated `Redrive` API. StartMessageMoveTask takes a
  `SourceArn` (the DLQ ARN), an optional `DestinationArn` (defaults to
  the source queue from the DLQ's configuration), an optional
  `MaxNumberOfMessagesPerSecond` for rate limiting, and returns a
  `TaskHandle`. Use `describe-message-move-task` to check status and
  `cancel-message-move-task` to abort.

- **`ApproximateNumberOfMessagesVisible` is an approximation, not an
  exact count.** SQS is a distributed system; the metric is eventually
  consistent. For precise counts, poll the queue with `ReceiveMessage`.
  For DLQ analysis, the trend (growing vs stable vs shrinking) is more
  useful than the absolute number.

- **`ApproximateNumberOfMessagesNotVisible` represents in-flight
  messages** — messages that have been received but not yet deleted (or
  whose visibility timeout has not expired). A consistently high
  NotVisible count with a low Deleted count indicates the consumer is
  receiving but not completing processing — a visibility timeout or
  processing-time mismatch.

- **Message retention period defaults to 4 days (345,600 seconds) and
  can be set up to 14 days (1,209,600 seconds).** Messages older than
  the retention period are silently deleted by SQS — they do NOT go to
  the DLQ. Operators who see messages "vanish" without reaching the DLQ
  are hitting retention expiry, especially in backlogged queues.

- **Lambda throttling causes SQS DLQ accumulation.** When the Lambda
  consumer is throttled (concurrent executions at the account or
  reserved concurrency limit), messages are not processed. The event
  source mapping retries, incrementing the receive count. After
  maxReceiveCount retries, messages move to the DLQ. The root cause is
  Lambda concurrency, not SQS.

- **`ReceiveMessage` returns `ApproximateReceiveCount` in the message
  attributes.** This attribute tells you how many times the message has
  been received. A count near maxReceiveCount means the message is about
  to be moved to the DLQ. Inspecting this attribute on DLQ messages
  confirms whether the message truly exhausted its retries.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`set-queue-attributes`, `purge-queue`, `delete-message`,
  `start-message-move-task`, `cancel-message-move-task`,
  `put-function-concurrency`, `update-event-source-mapping`), emit and
  await operator approval.

- **Read-only first.** Every probe in the diagnostic tree is read-only
  (`get-queue-attributes`, `receive-message` without deletion,
  `get-event-source-mapping`, `get-metric-statistics`, `lookup-events`,
  `list-dead-letter-source-queues`). Do not perform state-changing
  operations as diagnostic probes.

- **`set-queue-attributes` for VisibilityTimeout** is non-disruptive for
  new messages but does not affect messages already in-flight. Existing
  in-flight messages retain their original visibility timeout.

- **`set-queue-attributes` for RedrivePolicy** changes maxReceiveCount
  for future receive cycles. Messages already at the old maxReceiveCount
  are not retroactively returned from the DLQ.

- **`purge-queue`** deletes ALL messages in the queue immediately and
  cannot be undone. Never purge the source queue as a diagnostic step.
  Purge the DLQ only after all messages have been inspected and the root
  cause is fixed.

- **`delete-message`** removes a single message using its receipt handle.
  The receipt handle is valid only within the visibility timeout window.
  Always delete specific poison messages individually, not via purge.

- **`start-message-move-task`** moves messages from the DLQ back to the
  source queue (or a specified destination). Rate-limit with
  `MaxNumberOfMessagesPerSecond` to avoid overwhelming the consumer.
  Always fix the root cause before redriving.

- **`put-function-concurrency`** changes the reserved concurrency for the
  Lambda function. Setting it to 0 disables invocations. Setting it too
  high can exhaust account-level concurrency for other functions.

- **`update-event-source-mapping`** can change BatchSize,
  VisibilityTimeout, and MaximumBatchingWindowInSeconds. Changes take
  effect on the next polling cycle. Disabling the mapping
  (`--no-enabled`) stops all message processing.

- **Bulk remediation batch limit.** If the diagnosis identifies the same
  root cause across multiple queues, batch remediation into groups of at
  most 5 queues, emit a single CONFIRM per batch, and verify between
  batches.

## Deep reference: SQS DLQ layer model

### Symptom → layer decision matrix (offline classification)

```
Symptom / pattern                                → Layer
DLQ growing fast, all message types               → MAX_RECEIVE_COUNT_TOO_LOW / LAMBDA_CONCURRENCY_THROTTLE
DLQ growing, Lambda Duration > VisibilityTimeout  → VISIBILITY_TIMEOUT_EXCEEDED
FIFO queue stall, one MessageGroupId              → FIFO_POISON_MESSAGE
Messages vanish, no DLQ growth                    → MESSAGE_RETENTION_EXPIRED
StartMessageMoveTask fails                        → DLQ_TYPE_MISMATCH / REDRIVE_MISCONFIGURED
Lambda Throttles > 0                              → LAMBDA_CONCURRENCY_THROTTLE
Duplicate processing, high ApproximateReceiveCount → VISIBILITY_TIMEOUT_RESET
Entire batch fails, all messages retry            → BATCH_RECEIVE_FAILURE
```

### SQS message lifecycle

```
1. Producer → SendMessage → message enters queue (visible)
2. Consumer → ReceiveMessage → message becomes invisible (VT starts)
3a. Consumer processes successfully → DeleteMessage → message removed
3b. Consumer fails / VT expires → message becomes visible again
4. Steps 2-3b repeat until ApproximateReceiveCount > maxReceiveCount
5. Message moves to DLQ
```

### maxReceiveCount × VisibilityTimeout interaction

The effective time-to-DLQ depends on both settings:

```
maxReceiveCount = 3, VT = 30s → minimum ~90s to DLQ (3 × 30s)
maxReceiveCount = 3, VT = 5s  → minimum ~15s to DLQ (3 × 5s)
maxReceiveCount = 5, VT = 60s → minimum ~300s to DLQ (5 × 60s)
```

These are MINIMUM times. Actual time depends on polling frequency and
consumer availability.

### FIFO MessageGroupId behavior

```
Queue: orders.fifo
MessageGroupId: "cust-A"
  msg-1 → processed ✓
  msg-2 → FAIL (poison) → received 5x → DLQ
  msg-3 → BLOCKED (waiting for msg-2)
  msg-4 → BLOCKED (waiting for msg-3)

MessageGroupId: "cust-B"
  msg-5 → processed ✓ (not affected by cust-A stall)
  msg-6 → processed ✓
```

Once msg-2 moves to the DLQ, msg-3 becomes deliverable. If msg-3 also
fails (same consumer bug), the stall continues.

### StartMessageMoveTask (v2 redrive API)

```bash
# Start
aws sqs start-message-move-task \
  --source-arn <dlq-arn> \
  [--destination-arn <target-queue-arn>] \
  [--max-number-of-messages-per-second <rate>] \
  --output json
# Returns: {"TaskHandle": "..."}

# Status
aws sqs describe-message-move-task \
  --task-handle <handle>
# Returns: Status (RUNNING/COMPLETED/FAILED/CANCELLING),
#   MessagesMoved, ApproximateNumberOfMessagesMoved

# Cancel
aws sqs cancel-message-move-task \
  --task-handle <handle>
```

Default destination: the source queue configured in the DLQ's metadata
(the queue that originally fed this DLQ). Override with
`--destination-arn` for a custom target.

### Lambda event source mapping SQS parameters

| Parameter | Default | Effect |
|---|---|---|
| `BatchSize` | 10 | Messages per Lambda invocation (1-10,000) |
| `VisibilityTimeout` | 30 | Overrides queue VT for this mapping |
| `MaximumBatchingWindowInSeconds` | 0 | Collect messages for N seconds before invoking |
| `FunctionResponseTypes` | (none) | Add `ReportBatchItemFailures` for partial batch handling |
| `MaxRecordCount` | (per mapping) | Maximum records in a single invocation |
| `Enabled` | true | Set to false to pause processing |

### SQS queue attributes reference

| Attribute | Default | Max | Notes |
|---|---|---|---|
| `VisibilityTimeout` | 30s | 43,200s (12h) | Time message is invisible after receive |
| `MessageRetentionPeriod` | 345,600s (4d) | 1,209,600s (14d) | Messages older than this are deleted |
| `DelaySeconds` | 0 | 900s (15m) | Delivery delay for standard queues |
| `MaximumMessageSize` | 262,144 (256 KB) | 262,144 | Cannot be increased; use Extended Client Library |
| `ReceiveMessageWaitTimeSeconds` | 0 | 20 | Long polling; reduces empty receives |
| `RedrivePolicy` | (none) | — | `{"deadLetterTargetArn":"...","maxReceiveCount":"N"}` |

## Recent AWS features (2024-2026)

- **StartMessageMoveTask v2 API (2023-2024):** The replacement for the
  deprecated Redrive API. Supports rate limiting
  (`MaxNumberOfMessagesPerSecond`), destination queue override,
  `describe-message-move-task` for status, and `cancel-message-move-task`
  for abort. Diagnostically, always use v2 — the legacy API does not
  support these features and may be removed.
- **SSES (Server-Side Encryption with SSE-SQS) (2024):** SQS-managed
  encryption (distinct from SSE-KMS). Diagnostically, encryption-related
  AccessDenied errors should check the queue's KMS key policy if SSE-KMS
  is used, or verify SSE configuration consistency between producer and
  consumer.
- **FIFO high-throughput mode (2024-2025):** FIFO queues can now sustain
  higher throughput per MessageGroupId. Diagnostically, throughput limits
  are higher than the historical 300 messages/second per group, but
  ordering guarantees remain per group.
- **ApproximateNumberOfMessagesDelayed metric (2024):** CloudWatch now
  reports delayed messages separately. Useful for diagnosing
  `DelaySeconds` configuration issues on standard queues.
- **Lambda event source mapping partial batch response (2024-2025):**
  `ReportBatchItemFailures` is now the recommended default for all new
  SQS-Lambda event source mappings. Diagnostically, mappings created
  before 2024 may not have this enabled, causing full-batch retries.

