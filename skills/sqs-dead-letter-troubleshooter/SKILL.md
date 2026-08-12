---
name: sqs-dead-letter-troubleshooter
description: >-
  Diagnoses Amazon SQS messages accumulating in dead-letter queues through a
  ten-category diagnostic tree: redrive policy maxReceiveCount too low,
  processing time exceeding visibility timeout, message size exceeding
  256 KB, batch receive failures, FIFO message group stuck (poison message
  blocks entire MessageGroupId), DLQ queue type mismatch (standard DLQ
  for FIFO source), redrive configuration via StartMessageMoveTask v2,
  approximate number of messages visible vs not visible, visibility
  timeout reset semantics, receive request attempt count, Lambda trigger
  concurrency limits causing throttling and DLQ overflow, and message
  retention expiry before processing. Walks symptoms to a verified root
  cause with evidence-backed probes; emits ROOT_CAUSE_IDENTIFIED,
  INSUFFICIENT_DATA.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline queue classification works from pasted queue attributes and message samples. Live-account diagnosis uses aws sqs get-queue-attributes, list-dead-letter-source-queues, receive-message, get-queue-url, aws lambda get-event-source-mapping, aws cloudwatch get-metric-statistics, aws cloudtrail lookup-events, and aws sqs start-message-move-task (AWS CLI v2, SSO or key-based credentials).
keywords:
- SQS
- dead-letter queue
- DLQ
- maxReceiveCount
- redrive policy
- visibility timeout
- poison message
- FIFO
- MessageGroupId
- StartMessageMoveTask
- message redrive
- approximateNumberOfMessages
- Lambda trigger
- throttling
- message retention
- troubleshooting
tags:
- sqs
- appintegration
- troubleshooting
- dead-letter
- fifo
- visibility-timeout
- redrive
- lambda-trigger
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: AppIntegration
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing SQS messages accumulating in a dead-letter queue (maxReceiveCount too low, visibility timeout exceeded, FIFO poison message blocking a group, DLQ type mismatch, Lambda concurrency throttling, message retention expiry), walking a symptom to the failed layer with verify and fix commands, validating why messages are being moved to the DLQ prematurely or in bulk, or planning a redrive from DLQ back to the source queue using StartMessageMoveTask.
  when_not_to_use: SQS queue creation and IaC (use the CloudFormation or Terraform SQS resource docs), SNS-to-SQS subscription debugging (use sns-delivery-troubleshooter), Lambda handler code debugging for message processing failures (use application logs and a debugger), EventBridge-to-SQS target delivery issues (use eventbridge-rule-not-firing-troubleshooter), or IAM policy authoring for SQS access (use iam-least-privilege-advisor). This skill diagnoses DLQ accumulation patterns; it does not author queue policies or debug application handler logic.
  activation_triggers:
  - SQS dead-letter queue
  - SQS DLQ filling
  - SQS messages in DLQ
  - SQS maxReceiveCount
  - SQS redrive policy
  - SQS visibility timeout exceeded
  - SQS poison message
  - SQS FIFO message group stuck
  - SQS MessageGroupId blocked
  - SQS start-message-move-task
  - SQS redrive from DLQ
  - SQS message retention expired
  - SQS Lambda throttling DLQ
  - SQS approximateNumberOfMessages
  - SQS DLQ not FIFO
  - troubleshoot SQS dead-letter
  invocation_schema: 'Input: either (a) a symptom description ("DLQ filling", "messages not processing", "FIFO queue stuck"), optionally paired with the source queue and DLQ attributes (get-queue-attributes output), OR (b) a QueueURL plus DLQArn for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {MAX_RECEIVE_COUNT_TOO_LOW, VISIBILITY_TIMEOUT_EXCEEDED, MESSAGE_SIZE_LIMIT, BATCH_RECEIVE_FAILURE, FIFO_POISON_MESSAGE, DLQ_TYPE_MISMATCH, REDRIVE_MISCONFIGURED, VISIBILITY_TIMEOUT_RESET, LAMBDA_CONCURRENCY_THROTTLE, MESSAGE_RETENTION_EXPIRED, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline queue classification):\nSymptom: \"SQS source queue orders-queue is draining slowly\nand its DLQ orders-dlq has accumulated 8000 messages in the\nlast hour. The consumer is a Lambda function with a 30s\ntimeout. maxReceiveCount is set to 3.\"\nSourceQueueURL: https://sqs.us-east-1.amazonaws.com/111111111111/orders-queue\nDLQArn: arn:aws:sqs:us-east-1:111111111111:orders-dlq\nRedrivePolicy: {deadLetterTargetArn: \"arn:...orders-dlq\",\n  maxReceiveCount: \"3\"}\nVisibilityTimeout: 30\nMessageRetentionPeriod: 1209600\nLambda Timeout: 30\nLambda EventSourceMapping BatchSize: 10"
---

# SQS Dead-Letter Troubleshooter

## Quick start

- **Symptom → layer map (first plausible match drives the first probe):**
  DLQ filling rapidly, all message types → MAX_RECEIVE_COUNT_TOO_LOW or
  LAMBDA_CONCURRENCY_THROTTLE; DLQ filling slowly, specific message shapes
  → FIFO_POISON_MESSAGE or VISIBILITY_TIMEOUT_EXCEEDED; messages vanish
  without reaching DLQ → MESSAGE_RETENTION_EXPIRED; DLQ type mismatch
  error on redrive → DLQ_TYPE_MISMATCH; redrive does not move messages →
  REDRIVE_MISCONFIGURED.
- **maxReceiveCount counts receive ATTEMPTS, not minutes or processing
  cycles.** Each time a consumer calls `ReceiveMessage` and the message
  is delivered, the receive-count increments. If the consumer receives
  the message but does not delete it (because processing failed), the
  message returns to the queue after the visibility timeout and the
  count increments on the next receive. A maxReceiveCount of 3 means the
  message is moved to the DLQ after 3 failed receive-and-not-delete
  cycles, regardless of wall-clock time.
- **A poison message in a FIFO message group blocks ALL messages in that
  MessageGroupId.** FIFO queues process messages in order within a
  MessageGroupId. If message N fails repeatedly and lands in the DLQ,
  messages N+1, N+2, ... behind it are stuck waiting because FIFO
  guarantees strict ordering. The entire MessageGroupId is stalled until
  the poison message is removed or successfully processed.
- **StartMessageMoveTask is the v2 API for DLQ redrive.** The legacy
  `Redrive` API (with `RedrivePolicy`) is deprecated. Use
  `aws sqs start-message-move-task` to move messages from the DLQ back
  to the source queue. It supports rate limiting, destination queue
  override, and task cancellation.
- **Visibility timeout resets on each ReceiveMessage call.** When a
  consumer receives a message, the visibility timeout makes it invisible
  to other consumers. If the same consumer (or a different one) receives
  the message again after the timeout expires, the timer resets. A
  processing duration consistently exceeding the visibility timeout causes
  duplicate processing and accelerates DLQ accumulation.

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

## Quick reference — symptom triage table

| Symptom phrase / error | Most likely layer | First probe |
|---|---|---|
| DLQ filling rapidly with all message types | MAX_RECEIVE_COUNT_TOO_LOW / LAMBDA_CONCURRENCY_THROTTLE | `get-queue-attributes` (RedrivePolicy maxReceiveCount); CloudWatch `Throttles` on consumer Lambda |
| DLQ filling slowly, same message shapes | FIFO_POISON_MESSAGE / VISIBILITY_TIMEOUT_EXCEEDED | Inspect DLQ messages; compare Lambda Duration to VisibilityTimeout |
| Messages vanish without reaching DLQ | MESSAGE_RETENTION_EXPIRED | `get-queue-attributes` (MessageRetentionPeriod); CloudWatch `ApproximateAgeOfOldestMessage` |
| FIFO queue throughput drops to zero for one group | FIFO_POISON_MESSAGE | Identify the stuck MessageGroupId; check if that group's messages are in the DLQ |
| `StartMessageMoveTask` fails with InvalidParameterCombination | DLQ_TYPE_MISMATCH | Check if source is FIFO and DLQ is standard (or vice versa) |
| Lambda consumer throttled, DLQ fills | LAMBDA_CONCURRENCY_THROTTLE | CloudWatch `Throttles` + `ConcurrentExecutions` vs reserved concurrency |
| Redrive task created but messages not moving | REDRIVE_MISCONFIGURED | `describe-message-move-task`; verify DestinationArn and DLQ redrive-allow-policy |
| Duplicate processing, DLQ fills with duplicates | VISIBILITY_TIMEOUT_RESET | Compare Lambda Duration p99 to queue VisibilityTimeout |

## Pre-flight: queue state and gather-info gate

Before running symptom-specific probes, gather the canonical queue
configuration and short-circuit on queue states that mimic DLQ issues.

### Account-wide pre-flight commands

```bash
# 1. Source queue attributes (RedrivePolicy, VisibilityTimeout,
#    MessageRetentionPeriod, ApproximateNumberOfMessages,
#    ApproximateNumberOfMessagesNotVisible, FifoQueue, Deduplication)
aws sqs get-queue-attributes \
  --queue-url <source-queue-url> \
  --attribute-names All --output json

# 2. DLQ attributes (RedrivePolicy, ApproximateNumberOfMessages,
#    queue type, redrive-allow-policy)
aws sqs get-queue-attributes \
  --queue-url <dlq-url> \
  --attribute-names All --output json

# 3. List queues that use this DLQ (reverse lookup)
aws sqs list-dead-letter-source-queues \
  --queue-url <dlq-url> --output json

# 4. Consumer Lambda event source mapping (if Lambda-triggered)
aws lambda get-event-source-mapping \
  --function-name <consumer-lambda> --output json 2>/dev/null

# 5. CloudWatch queue metrics (ApproximateNumberOfMessagesVisible,
#    ApproximateAgeOfOldestMessage, NumberOfMessagesSent, Deleted)
aws cloudwatch get-metric-statistics --namespace AWS/SQS \
  --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=<queue-name> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json
```

### Queue-state short-circuit

| Attribute / State | Effect on diagnosis |
|---|---|
| `ApproximateNumberOfMessages` (DLQ) growing | Messages are actively failing. Proceed to identify why. |
| `ApproximateNumberOfMessages` (DLQ) stable | Historical accumulation; no new failures. Check when growth stopped (deploy timestamp, config change). |
| `ApproximateNumberOfMessagesNotVisible` (source) high | Messages are in-flight (being processed) but not completing. Visibility timeout / processing time mismatch likely. |
| `ApproximateAgeOfOldestMessage` > `MessageRetentionPeriod` × 0.8 | Messages are approaching retention expiry. They will be deleted by SQS, not moved to DLQ. |
| `FifoQueue: true` (source) + `FifoQueue: false` (DLQ) | DLQ type mismatch. FIFO source requires FIFO DLQ. |

### Input validation gate

If the input is malformed (missing QueueURL, absent DLQ Arn, no consumer
context for Lambda-triggered queues), emit:

```text
TARGET: <queue-url or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum the source
  QueueURL and the DLQ Arn or URL.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the source QueueURL, (2)
  the DLQ URL or Arn, (3) the consumer type (Lambda, EC2, ECS, manual),
  and (4) for Lambda consumers, the function name and event source
  mapping configuration.
```

## Process — Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on the
observed symptom, then walk the layer-specific probes in order. Each
layer ends with either a positive root-cause confirmation (failing probe
that matches the symptom) or a pass that moves to the next layer.
**Never emit ROOT_CAUSE_IDENTIFIED without a failing probe that matches
the symptom.**

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

### Step 1: Symptom entry — pick the diagnostic branch

Map the symptom to a branch and jump to that branch's section. If the
symptom matches none of the categories, route to Step 12
(INSUFFICIENT_DATA).

| Symptom | Branch |
|---|---|
| DLQ filling rapidly, all message types | Step 2 — maxReceiveCount |
| DLQ filling, Lambda consumer in play | Step 3 — Lambda concurrency |
| DLQ filling, specific message shapes only | Step 4 — Visibility timeout |
| FIFO queue throughput dropped for one group | Step 5 — FIFO poison message |
| Messages vanish without reaching DLQ | Step 6 — Message retention |
| Redrive / StartMessageMoveTask fails | Step 7 — DLQ type mismatch |
| Redrive task created, messages not moving | Step 8 — Redrive misconfigured |
| Consumer receives duplicates | Step 9 — Visibility timeout reset |
| Messages > 256 KB | Step 10 — Message size |
| None of the above | Step 12 — INSUFFICIENT_DATA |

### Step 2: maxReceiveCount too low

Symptom: the DLQ is filling rapidly with messages of all types, and the
consumer is processing some messages successfully but not all.

```bash
aws sqs get-queue-attributes \
  --queue-url <source-queue-url> \
  --attribute-names RedrivePolicy VisibilityTimeout --output json
```

Parse the RedrivePolicy:

```bash
aws sqs get-queue-attributes \
  --queue-url <source-queue-url> \
  --attribute-names RedrivePolicy --output json | \
  jq '.Attributes.RedrivePolicy | fromjson'
```

Check `maxReceiveCount`:

| maxReceiveCount | Typical scenario | Diagnosis |
|---|---|---|
| 1 | Every failed processing attempt → DLQ | Almost always too low for transient failures. Should be ≥ 3. |
| 3 | Default for many configurations | Reasonable for idempotent consumers. Check if failure rate is higher than expected. |
| 5 | Moderate resilience | Good for consumers with occasional transient failures. |
| 10+ | High resilience | Rarely the cause of premature DLQ migration. Look at processing failures instead. |

Inspect DLQ messages for their `ApproximateReceiveCount`:

```bash
aws sqs receive-message \
  --queue-url <dlq-url> \
  --max-number-of-messages 5 \
  --message-attribute-names All \
  --attribute-names All --output json | \
  jq '.Messages[] | {
    ApproximateReceiveCount: .Attributes.ApproximateReceiveCount,
    SentTimestamp: .Attributes.SentTimestamp
  }'
```

If `ApproximateReceiveCount` equals maxReceiveCount for all inspected
messages, the messages exhausted their retries legitimately. The issue
is the consumer failing to process, not maxReceiveCount being too low.

If `ApproximateReceiveCount` is much lower than expected (e.g., 1 or 2
when maxReceiveCount is 5), check for a misconfigured redrive policy or
a DLQ that is receiving messages from a different source.

**Verdict:** If maxReceiveCount is 1 or 2 and the consumer has transient
failures (timeouts, downstream throttling), ROOT_CAUSE_IDENTIFIED,
`LAYER: MAX_RECEIVE_COUNT_TOO_LOW`. Fix: raise maxReceiveCount to at
least 3-5.

### Step 3: Lambda concurrency throttling

Symptom: the DLQ is filling and the consumer is a Lambda function.
CloudWatch shows Lambda `Throttles` or `ConcurrentExecutions` at the
account/reserved concurrency limit.

```bash
# Event source mapping configuration
aws lambda get-event-source-mapping \
  --function-name <consumer-lambda> --output json | \
  jq '{BatchSize, MaximumBatchingWindowInSeconds, VisibilityTimeout,
       FunctionArn, State}'

# Lambda concurrency metrics
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Throttles \
  --dimensions Name=FunctionName,Value=<consumer-lambda> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json

aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name ConcurrentExecutions \
  --dimensions Name=FunctionName,Value=<consumer-lambda> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Maximum --output json
```

Check reserved concurrency:

```bash
aws lambda get-function-concurrency \
  --function-name <consumer-lambda> --output json
```

If `Throttles > 0` in the same window as DLQ growth, the Lambda is being
throttled. Messages are not processed within the visibility timeout,
the receive count increments, and messages move to the DLQ.

**Common throttle causes:**

| Pattern | Cause |
|---|---|
| Account-level concurrent executions at 1000 (default) | Account-level concurrency limit reached. Request a quota increase or optimize the consumer. |
| Reserved concurrency set to a low value (e.g., 10) | Intentionally low reserved concurrency. Raise it if the consumer can handle more. |
| Reserved concurrency set to 0 | The function is disabled for concurrent execution. This is a common mistake. |
| Another function in the account consuming all concurrency | A "noisy neighbor" function. Set reserved concurrency on the SQS consumer to guarantee floor. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: LAMBDA_CONCURRENCY_THROTTLE`.
Fix: raise reserved concurrency, raise account-level concurrency limit,
or set a reserved concurrency floor on the SQS consumer Lambda.

### Step 4: Visibility timeout exceeded

Symptom: the DLQ is filling and the consumer's processing time exceeds
the visibility timeout. Messages become visible again during processing,
causing duplicate receives and accelerated receive-count increment.

```bash
# Queue visibility timeout
aws sqs get-queue-attributes \
  --queue-url <source-queue-url> \
  --attribute-names VisibilityTimeout --output json

# Event source mapping visibility timeout (overrides queue for Lambda)
aws lambda get-event-source-mapping \
  --function-name <consumer-lambda> --output json | \
  jq '.VisibilityTimeout'
```

Compare against the consumer's processing time:

```bash
# Lambda consumer Duration
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=<consumer-lambda> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum,p99 --output json
```

If Lambda Duration p99 > VisibilityTimeout, the consumer is processing
messages that become visible again before completion. This causes:

1. Duplicate delivery (another consumer instance receives the same
   message).
2. Accelerated receive-count increment (each duplicate receive counts).
3. Premature DLQ migration (messages that would have succeeded if given
   more time).

**Rule of thumb:** VisibilityTimeout should be ≥ 6x the expected
processing time. This accounts for retries within the Lambda timeout and
batch processing overhead.

For Lambda consumers, set the visibility timeout on the event source
mapping:

```bash
aws lambda update-event-source-mapping \
  --uuid <mapping-uuid> \
  --visibility-timeout <seconds>
```

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: VISIBILITY_TIMEOUT_EXCEEDED`.
Fix: raise the visibility timeout on both the queue and the event source
mapping to ≥ 6x the consumer's p99 processing time.

### Step 5: FIFO poison message — group stuck

Symptom: a FIFO queue's throughput drops to zero for a specific
MessageGroupId while other groups continue to flow. Messages in the
stuck group are not being delivered or are failing repeatedly.

```bash
# Check if the source queue is FIFO
aws sqs get-queue-attributes \
  --queue-url <source-queue-url> \
  --attribute-names FifoQueue --output json

# Inspect DLQ messages for a common MessageGroupId
aws sqs receive-message \
  --queue-url <dlq-url> \
  --max-number-of-messages 10 \
  --message-attribute-names All \
  --attribute-names All --output json | \
  jq '.Messages[] | {
    MessageId: .MessageId,
    MessageGroupId: .Attributes.MessageGroupId,
    ApproximateReceiveCount: .Attributes.ApproximateReceiveCount,
    Body: .Body[0:200]
  }'
```

If all DLQ messages share the same MessageGroupId, that group is the
stuck partition. The poison message (the one that first failed) is
likely in the DLQ or at the head of the source queue for that group.

**FIFO poison message diagnosis:**

1. Identify the stuck MessageGroupId (from DLQ messages or source queue
   inspection).
2. The message with the highest receive count in that group is the
   poison message.
3. If the poison message is in the DLQ: the group is unblocked (FIFO
   moves to the next message). If the group is still stuck, the NEXT
   message is also failing (same code bug).
4. If the poison message is still in the source queue (not yet at
   maxReceiveCount): the group is blocked until this message is
   processed or moved to the DLQ.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: FIFO_POISON_MESSAGE`.

**Fix options:**
- Fix the consumer code to handle the poison message's payload.
- If the message is malformed and unfixable: let it reach maxReceiveCount
  and move to the DLQ, then purge it from the DLQ.
- Temporarily raise maxReceiveCount to accelerate the poison message's
  move to DLQ.
- For FIFO queues, consider using `MessageGroupId` partitioning to
  isolate bad messages from the main flow.

### Step 6: Message retention expired

Symptom: messages are vanishing from the source queue without reaching
the DLQ. The consumer is slow or backlogged.

```bash
aws sqs get-queue-attributes \
  --queue-url <source-queue-url> \
  --attribute-names MessageRetentionPeriod --output json
```

`MessageRetentionPeriod` is in seconds. Default: 345,600 (4 days). Max:
1,209,600 (14 days).

Check the age of the oldest message:

```bash
aws cloudwatch get-metric-statistics --namespace AWS/SQS \
  --metric-name ApproximateAgeOfOldestMessage \
  --dimensions Name=QueueName,Value=<queue-name> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Maximum --output json
```

If `ApproximateAgeOfOldestMessage` approaches or exceeds
`MessageRetentionPeriod`, messages are being silently deleted by SQS
before the consumer processes them. They never reach the DLQ because
retention expiry is a queue-level deletion, not a processing failure.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: MESSAGE_RETENTION_EXPIRED`.
Fix: increase `MessageRetentionPeriod` and/or scale the consumer to
drain the backlog faster.

### Step 7: DLQ type mismatch

Symptom: `StartMessageMoveTask` fails with
`InvalidParameterCombination` or messages are not redriving correctly
from the DLQ.

```bash
# Source queue type
aws sqs get-queue-attributes \
  --queue-url <source-queue-url> \
  --attribute-names FifoQueue --output json

# DLQ type
aws sqs get-queue-attributes \
  --queue-url <dlq-url> \
  --attribute-names FifoQueue --output json
```

| Source Queue | DLQ | Result |
|---|---|---|
| Standard | Standard | Correct |
| FIFO | FIFO (.fifo) | Correct |
| FIFO | Standard | WRONG — DLQ must be FIFO for a FIFO source |
| Standard | FIFO | WRONG — DLQ should be standard for a standard source |

A FIFO source queue with a standard DLQ causes:
- Message ordering loss (standard DLQ does not preserve FIFO order).
- StartMessageMoveTask failures when redriving (type mismatch between
  DLQ and source).
- Redrive policy validation errors in some configurations.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: DLQ_TYPE_MISMATCH`. Fix:
create a FIFO DLQ (with `.fifo` suffix) and update the source queue's
RedrivePolicy.

### Step 8: Redrive misconfigured

Symptom: `StartMessageMoveTask` was called but messages are not moving
from the DLQ back to the source queue.

```bash
# Start a message move task
aws sqs start-message-move-task \
  --source-arn <dlq-arn> \
  --max-number-of-messages-per-second 50 \
  --output json

# Check task status (using the TaskHandle)
aws sqs describe-message-move-task \
  --task-handle <task-handle> --output json
```

Common redrive failures:

| `describe-message-move-task` status | Cause |
|---|---|
| `RUNNING` with `MessagesMoved: 0` | Destination queue is empty in the DLQ, OR the DLQ redrive-allow-policy does not permit the source queue. |
| `FAILED` | DLQ type mismatch, destination queue deleted, or permissions issue. |
| `COMPLETED` with `MessagesMoved` < expected | Some messages were deleted from the DLQ between task start and completion (retention expiry, manual purge). |
| `TaskHandle` not found | The task already completed or was cancelled. |

Check the DLQ's redrive-allow-policy:

```bash
aws sqs get-queue-attributes \
  --queue-url <dlq-url> \
  --attribute-names RedriveAllowPolicy --output json
```

The `RedriveAllowPolicy` controls which source queues can redrive from
this DLQ. If it is set to `allowAll: false` and does not list the source
queue ARN, redrive is blocked.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: REDRIVE_MISCONFIGURED`.

### Step 9: Visibility timeout reset — duplicate processing

Symptom: the consumer receives duplicate messages (same MessageId
processed multiple times), and the DLQ fills with duplicates.

Each `ReceiveMessage` call resets the visibility timeout for the
received message. If a consumer receives a message, processes it slowly,
and the visibility timeout expires, the message becomes visible again.
Another `ReceiveMessage` (from the same consumer or a different one)
resets the timer — but the first consumer may still be processing.

```bash
# Check for duplicate processing in Lambda logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/<consumer-lambda> \
  --start-time $(date -d '-1 hour' +%s)000 \
  --filter-pattern '"DUPLICATE" OR "already processed"' \
  --output json

# Check ApproximateReceiveCount on source queue messages
aws sqs receive-message \
  --queue-url <source-queue-url> \
  --max-number-of-messages 5 \
  --attribute-names ApproximateReceiveCount --output json | \
  jq '.Messages[] | {
    MessageId: .MessageId,
    ReceiveCount: .Attributes.ApproximateReceiveCount
  }'
```

A high `ApproximateReceiveCount` (3+) on source queue messages indicates
they have been received multiple times — the visibility timeout is
expiring before processing completes.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: VISIBILITY_TIMEOUT_RESET`.
Fix: increase the visibility timeout and ensure the consumer is idempotent
(handles duplicate delivery gracefully).

### Step 10: Message size limit

Symptom: the consumer cannot process certain messages, and those
messages accumulate in the DLQ. The consumer logs show payload errors or
truncated data.

```bash
# Check message body size on DLQ messages
aws sqs receive-message \
  --queue-url <dlq-url> \
  --max-number-of-messages 5 \
  --attribute-names All --output json | \
  jq '.Messages[] | {
    MessageId: .MessageId,
    BodySize: (.Body | length)
  }'
```

SQS message body limit: 256 KB (262,144 bytes).

If messages approach or exceed this limit:
- Messages > 256 KB are rejected by `SendMessage` (they never enter the
  queue). If they are in the queue/DLQ, they were sent via the Extended
  Client Library (S3-backed).
- If the consumer does not use the Extended Client Library, it receives
  only the S3 pointer and cannot process the payload.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: MESSAGE_SIZE_LIMIT`. Fix:
use the SQS Extended Client Library on both producer and consumer, or
reduce payload size.

### Step 11: Batch receive failures

Symptom: the consumer processes messages in batches (Lambda BatchSize >
1) and entire batches are failing, causing all messages in the batch to
increment their receive count simultaneously.

```bash
aws lambda get-event-source-mapping \
  --function-name <consumer-lambda> --output json | \
  jq '{BatchSize, FunctionResponseTypes, MaximumBatchingWindowInSeconds}'
```

For Lambda SQS triggers:
- `BatchSize`: 1-10,000 (default 10).
- `FunctionResponseTypes`: should include `ReportBatchItemFailures` for
  partial batch failure handling.
- Without `ReportBatchItemFailures`, a single bad record in a batch
  causes the ENTIRE batch to retry — all 10 messages increment their
  receive count.

If the consumer does not implement `ReportBatchItemFailures`:
- One poison message in a batch of 10 causes all 10 messages to retry.
- The receive count for all 10 increments on each batch retry.
- 9 perfectly good messages reach the DLQ alongside the 1 poison
  message.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: BATCH_RECEIVE_FAILURE`. Fix:
implement `ReportBatchItemFailures` in the consumer and return
`batchItemFailures` listing only the failed message IDs.

### Step 12: INSUFFICIENT_DATA

If none of the above produced a positive root-cause match, emit:

```text
TARGET: <queue-url>
VERDICT: INSUFFICIENT_DATA
REASON: The available evidence does not conclusively identify a root
  cause. One or more probes returned ambiguous results or required
  operator input that was not provided.
LAYER: UNKNOWN
EVIDENCE:
  - <list what was probed and what was inconclusive>
REMEDIATION: Provide: (1) the source queue and DLQ attributes
  (get-queue-attributes --attribute-names All), (2) a sample DLQ
  message body with attributes (ApproximateReceiveCount,
  MessageGroupId for FIFO), (3) the consumer configuration (Lambda
  event source mapping, EC2/ECS polling loop), and (4) CloudWatch
  metrics for the relevant time window (Throttles, Duration,
  ApproximateAgeOfOldestMessage).
```

## Output format

```text
TARGET: <source-queue-url> → <dlq-url>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <MAX_RECEIVE_COUNT_TOO_LOW | VISIBILITY_TIMEOUT_EXCEEDED |
        MESSAGE_SIZE_LIMIT | BATCH_RECEIVE_FAILURE |
        FIFO_POISON_MESSAGE | DLQ_TYPE_MISMATCH |
        REDRIVE_MISCONFIGURED | VISIBILITY_TIMEOUT_RESET |
        LAMBDA_CONCURRENCY_THROTTLE | MESSAGE_RETENTION_EXPIRED |
        UNKNOWN>
EVIDENCE:
  - <observed symptom — error string or behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <queue-name> in <region>.
  Proceed? (yes/no)"
```

### Worked example — FIFO poison message blocks group

```text
TARGET: orders.fifo → orders-dlq.fifo
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: FIFO queue orders.fifo has a poison message in MessageGroupId
  "cust-9912" that has been received 5 times (maxReceiveCount=5) without
  successful processing. The message contains a malformed JSON payload
  that causes the consumer Lambda to throw a JSON parse error. All
  messages behind it in MessageGroupId "cust-9912" are blocked by FIFO
  ordering guarantees. Other MessageGroupIds are flowing normally
  (Step 5).
LAYER: FIFO_POISON_MESSAGE
EVIDENCE:
  - Symptom: FIFO queue orders.fifo throughput dropped to near-zero for
    customer cust-9912 at 14:30 UTC. Other customer groups continue
    processing normally. DLQ orders-dlq.fifo has accumulated 23 messages
    in the last hour, all with MessageGroupId "cust-9912".
  - Probe: aws sqs receive-message on orders-dlq.fifo returns 10
    messages, ALL with Attributes.MessageGroupId = "cust-9912". The
    first message (by SentTimestamp) has ApproximateReceiveCount: 5 and
    Body containing "{bad json: missing closing brace".
  - Probe: aws logs filter-log-events on the consumer Lambda shows
    repeated "SyntaxError: Unexpected token" for MessageGroupId
    "cust-9912" starting at 14:30 UTC.
  - Passing: maxReceiveCount is 5 (reasonable); VisibilityTimeout is
    120s (exceeds Lambda Duration p99 of 8s); Lambda Throttles = 0;
    other MessageGroupIds are processing normally (no concurrency issue).
REMEDIATION:
  1. The poison message is already in the DLQ (receive count reached
     maxReceiveCount). The next message in MessageGroupId "cust-9912"
     should now be deliverable. Verify:
     aws sqs get-queue-attributes --queue-url <orders.fifo-url> \
       --attribute-names ApproximateNumberOfMessages --output json
  2. Fix the consumer to handle malformed JSON gracefully:
     try { JSON.parse(record.body) } catch { return batchItemFailures
     with only the bad record's messageId }
  3. Delete the poison message from the DLQ:
     aws sqs delete-message --queue-url <orders-dlq.fifo-url> \
       --receipt-handle <handle>
  4. Implement ReportBatchItemFailures in the Lambda to prevent one bad
     record from poisoning the entire batch.
CONFIRM: Before deleting the poison message and updating the Lambda,
  emit and await: "CONFIRM: About to delete the malformed message from
  orders-dlq.fifo and redeploy fn-sqs-consumer with JSON error handling.
  Proceed? (yes/no)"
```

### Worked example — Visibility timeout exceeded

```text
TARGET: image-processing-queue → image-processing-dlq
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The queue's VisibilityTimeout is 30 seconds but the consumer
  Lambda fn-image-processor has a Duration p99 of 45 seconds. Messages
  become visible again at T+30s while the Lambda is still processing,
  causing duplicate receives and accelerated receive-count increment.
  Messages that would succeed with more time are moved to the DLQ after
  maxReceiveCount=3 receives (Step 4).
LAYER: VISIBILITY_TIMEOUT_EXCEEDED
EVIDENCE:
  - Symptom: image-processing-dlq has grown from 0 to 5,200 messages in
    the last 2 hours. The source queue's
    ApproximateNumberOfMessagesNotVisible is consistently 30-40
    (messages in-flight).
  - Probe: aws cloudwatch get-metric-statistics on AWS/Lambda Duration
    for fn-image-processor: p99 = 45s, Maximum = 58s. The queue
    VisibilityTimeout is 30s.
  - Probe: aws sqs receive-message on the DLQ shows
    ApproximateReceiveCount = 3 on all inspected messages (they
    exhausted maxReceiveCount=3 in ~90 seconds: 3 receives × 30s VT).
  - Passing: Lambda Throttles = 0 (not a concurrency issue); messages
    are well under 256 KB (not a size issue); queue is standard (not
    FIFO, no poison-message blocking).
REMEDIATION:
  1. Raise the visibility timeout on the queue:
     aws sqs set-queue-attributes \
       --queue-url <image-processing-queue-url> \
       --attributes VisibilityTimeout=300
  2. Raise the visibility timeout on the event source mapping:
     aws lambda update-event-source-mapping \
       --uuid <mapping-uuid> --visibility-timeout 300
  3. Redrive the DLQ messages back to the source queue:
     aws sqs start-message-move-task \
       --source-arn arn:aws:sqs:us-east-1:111111111111:image-processing-dlq
  4. Verify Duration p99 < new VisibilityTimeout / 6 (300/6 = 50s, which
     exceeds the observed p99 of 45s).
CONFIRM: Before updating the visibility timeout, emit and await:
  "CONFIRM: About to raise VisibilityTimeout to 300s on
   image-processing-queue and its event source mapping. Proceed?
   (yes/no)"
```

### Worked example — Lambda concurrency throttling

```text
TARGET: batch-jobs-queue → batch-jobs-dlq
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The consumer Lambda fn-batch-processor has a reserved concurrency
  of 5, but the queue is sustaining 50 messages/second. The Lambda is
  throttled at 5 concurrent executions; the backlog grows faster than
  processing. Messages exceed the visibility timeout while waiting for
  a throttled Lambda slot, incrementing receive count and moving to the
  DLQ (Step 3).
LAYER: LAMBDA_CONCURRENCY_THROTTLE
EVIDENCE:
  - Symptom: batch-jobs-dlq has grown from 0 to 12,000 messages in 3
    hours. The source queue backlog is at 45,000 messages.
  - Probe: aws cloudwatch get-metric-statistics on AWS/Lambda Throttles
    for fn-batch-processor: sustained 200+ throttles per 5-minute
    window.
  - Probe: aws lambda get-function-concurrency returns
    ReservedConcurrentExecutions: 5.
  - Probe: aws cloudwatch ConcurrentExecutions Maximum = 5 (at the
    reserved cap) for the entire 3-hour window.
  - Passing: VisibilityTimeout is 300s (exceeds Duration p99 of 12s);
    messages are under 256 KB; maxReceiveCount is 5 (reasonable);
    ReportBatchItemFailures is configured.
REMEDIATION:
  1. Raise the reserved concurrency on fn-batch-processor:
     aws lambda put-function-concurrency \
       --function-name fn-batch-processor \
       --reserved-concurrent-executions 50
  2. If the account-level concurrency limit is also a bottleneck,
     request a quota increase via the AWS Support Center.
  3. After the backlog drains, redrive the DLQ:
     aws sqs start-message-move-task \
       --source-arn arn:aws:sqs:us-east-1:111111111111:batch-jobs-dlq \
       --max-number-of-messages-per-second 100
  4. Verify Throttles drops to 0 and the source queue backlog drains.
CONFIRM: Before changing concurrency, emit and await:
  "CONFIRM: About to raise fn-batch-processor reserved concurrency from
   5 to 50. Proceed? (yes/no)"
```

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe that
  matches the symptom. A "process of elimination" diagnosis erodes
  operator trust when the real cause is elsewhere.

- NEVER assume maxReceiveCount counts time. It counts receive attempts.
  A maxReceiveCount of 3 can be exhausted in 10 seconds (short VT, fast
  polling) or in 10 minutes (long VT). Always cross-reference with the
  visibility timeout.

- NEVER treat a FIFO queue stall as a global throughput problem. FIFO
  guarantees ordering per MessageGroupId — a stall in one group does NOT
  affect other groups. Always identify the stuck MessageGroupId before
  declaring a queue-wide issue.

- NEVER attach a standard DLQ to a FIFO source queue. The DLQ MUST be
  FIFO (.fifo suffix, FifoQueue: true). A type mismatch causes redrive
  failures and ordering loss.

- NEVER use the deprecated Redrive API for DLQ redrive. Use
  `aws sqs start-message-move-task` (the v2 API). It supports rate
  limiting, destination override, task status tracking, and cancellation.

- NEVER set the visibility timeout lower than the consumer's p99
  processing time. The visibility timeout must exceed the worst-case
  processing duration to prevent duplicate delivery. Rule of thumb:
  VisibilityTimeout ≥ 6x expected processing time.

- NEVER forget that the Lambda event source mapping's VisibilityTimeout
  overrides the queue's. Setting the queue's VT to 300s while leaving
  the event source mapping at the default 30s still causes premature
  re-delivery.

- NEVER process batch messages without `ReportBatchItemFailures`. Without
  partial batch failure reporting, one bad record in a batch of 10 causes
  all 10 to retry — accelerating DLQ migration for 9 perfectly good
  messages.

- NEVER purge a DLQ without understanding why messages are there. Purging
  removes the evidence needed to diagnose the root cause. Always inspect
  DLQ messages first, then purge as a deliberate remediation step.

- NEVER assume `ApproximateNumberOfMessagesVisible` is exact. SQS is
  distributed; the count is eventually consistent. For precise counts,
  use `ReceiveMessage`. For diagnosis, the trend is more useful than the
  absolute number.

- NEVER assume messages that "vanish" went to the DLQ. If the consumer
  is backlogged and `ApproximateAgeOfOldestMessage` approaches
  `MessageRetentionPeriod`, messages are being silently deleted by SQS
  retention expiry — they never reach the DLQ.

- NEVER set Lambda reserved concurrency to 0 unintentionally. This
  disables all concurrent invocations of the function, causing every
  message to wait and eventually move to the DLQ.

- NEVER redrive from the DLQ without fixing the root cause first.
  Redriving poison messages or throttled workloads back to the source
  queue causes them to fail again and return to the DLQ — a redrive loop
  that wastes compute and accelerates costs.

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

## Remediation guidance

### For MAX_RECEIVE_COUNT_TOO_LOW

```bash
aws sqs set-queue-attributes \
  --queue-url <source-queue-url> \
  --attributes '{"RedrivePolicy":"{\"deadLetterTargetArn\":\"<dlq-arn>\",\"maxReceiveCount\":\"5\"}"}'
```

Raise maxReceiveCount to 3-5 for consumers with transient failures.
Consider higher values (10+) only if failures are genuinely transient
and the consumer is idempotent.

### For VISIBILITY_TIMEOUT_EXCEEDED

```bash
# Queue-level
aws sqs set-queue-attributes \
  --queue-url <source-queue-url> \
  --attributes VisibilityTimeout=300

# Event source mapping (for Lambda consumers)
aws lambda update-event-source-mapping \
  --uuid <mapping-uuid> \
  --visibility-timeout 300
```

Target: VisibilityTimeout ≥ 6x consumer p99 processing time.

### For FIFO_POISON_MESSAGE

1. Identify the poison message in the DLQ or source queue.
2. If in the DLQ: the group is unblocked; fix the consumer to handle the
   payload shape, then optionally redrive.
3. If still in the source queue: let it reach maxReceiveCount and move
   to the DLQ, or manually delete it if the consumer cannot process it.
4. Implement `ReportBatchItemFailures` to isolate bad records in future.

### For DLQ_TYPE_MISMATCH

Create a FIFO DLQ and update the source queue's RedrivePolicy:

```bash
# Create FIFO DLQ
aws sqs create-queue \
  --queue-name <new-dlq>.fifo \
  --attributes FifoQueue=true --output json

# Update RedrivePolicy on the source FIFO queue
aws sqs set-queue-attributes \
  --queue-url <source-fifo-queue-url> \
  --attributes '{"RedrivePolicy":"{\"deadLetterTargetArn\":\"<new-fifo-dlq-arn>\",\"maxReceiveCount\":\"5\"}"}'
```

### For REDRIVE_MISCONFIGURED

```bash
# Redrive from DLQ to source using v2 API
aws sqs start-message-move-task \
  --source-arn <dlq-arn> \
  --destination-arn <source-queue-arn> \
  --max-number-of-messages-per-second 50 \
  --output json

# Check status
aws sqs describe-message-move-task \
  --task-handle <task-handle> --output json
```

### For LAMBDA_CONCURRENCY_THROTTLE

```bash
# Raise reserved concurrency
aws lambda put-function-concurrency \
  --function-name <consumer-lambda> \
  --reserved-concurrent-executions <new-value>
```

Verify the account-level concurrency limit supports the new value.

### For MESSAGE_RETENTION_EXPIRED

```bash
aws sqs set-queue-attributes \
  --queue-url <source-queue-url> \
  --attributes MessageRetentionPeriod=1209600
```

Max: 1,209,600 seconds (14 days). Also scale the consumer to drain the
backlog.

### For BATCH_RECEIVE_FAILURE

Implement `ReportBatchItemFailures` in the Lambda consumer and update
the event source mapping:

```bash
aws lambda update-event-source-mapping \
  --uuid <mapping-uuid> \
  --function-response-types '["ReportBatchItemFailures"]'
```

### For VISIBILITY_TIMEOUT_RESET

Same as VISIBILITY_TIMEOUT_EXCEEDED — raise the timeout on both the
queue and event source mapping. Ensure the consumer is idempotent.

### For MESSAGE_SIZE_LIMIT

Use the SQS Extended Client Library (Java, Python) for payloads > 256
KB, or reduce payload size by offloading large data to S3 and passing a
reference.

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

## Domain

AWS CloudOps / SQS App Integration, Dead-Letter Queue Diagnostics,
FIFO Message Ordering, Lambda Event Source Mapping, and Message Redrive
Operations.

## AWS documentation

- **Amazon SQS Developer Guide — Dead-letter queues** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html
- **SQS visibility timeouts** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html
- **SQS message redrive (StartMessageMoveTask)** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-configure-dead-letter-queue-redrive.html
- **SQS FIFO queues** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/FIFO-queues.html
- **Lambda event source mappings for SQS** — https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html
- **Partial batch responses (ReportBatchItemFailures)** — https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html#services-sqs-batchfailurereporting
- **SQS message quotas** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-quotas.html
- **SQS Extended Client Library** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-s3-messages.html
- **SQS CloudWatch metrics** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-monitoring-using-cloudwatch.html
