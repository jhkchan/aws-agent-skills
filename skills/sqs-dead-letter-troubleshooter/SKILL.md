---
name: sqs-dead-letter-troubleshooter
description: 'Diagnoses Amazon SQS messages accumulating in dead-letter queues through a ten-category diagnostic tree: redrive policy maxReceiveCount too low, processing time exceeding visibility timeout, message size exceeding 256 KB, batch receive failures, FIFO message group stuck (poison message blocks entire MessageGroupId), DLQ queue type mismatch (standard DLQ for FIFO source), redrive configuration via StartMessageMoveTask v2, approximate number of messages visible vs not visible, visibility timeout reset semantics, receive request attempt count, Lambda trigger concurrency limits causing throttling and DLQ overflow, and message retention expiry before processing. Walks symptoms to a verified root cause with evidence-backed probes; emits ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline queue classification works from pasted queue attributes and message samples. Live-account diagnosis uses aws sqs get-queue-attributes, list-dead-letter-source-queues, receive-message, get-queue-url, aws lambda get-event-source-mapping, aws cloudwatch get-metric-statistics, aws cloudtrail lookup-events, and aws sqs start-message-move-task (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AppIntegration
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing SQS messages accumulating in a dead-letter queue (maxReceiveCount too low, visibility timeout exceeded, FIFO poison message blocking a group, DLQ type mismatch, Lambda concurrency throttling, message retention expiry), walking a symptom to the failed layer with verify and fix commands, validating why messages are being moved to the DLQ prematurely or in bulk, or planning a redrive from DLQ back to the source queue using StartMessageMoveTask.
  when_not_to_use: SQS queue creation and IaC (use the CloudFormation or Terraform SQS resource docs), SNS-to-SQS subscription debugging (use sns-delivery-troubleshooter), Lambda handler code debugging for message processing failures (use application logs and a debugger), EventBridge-to-SQS target delivery issues (use eventbridge-rule-not-firing-troubleshooter), or IAM policy authoring for SQS access (use iam-least-privilege-advisor). This skill diagnoses DLQ accumulation patterns; it does not author queue policies or debug application handler logic.
  activation_triggers: SQS dead-letter queue, SQS DLQ filling, SQS messages in DLQ, SQS maxReceiveCount, SQS redrive policy, SQS visibility timeout exceeded, SQS poison message, SQS FIFO message group stuck, SQS MessageGroupId blocked, SQS start-message-move-task, SQS redrive from DLQ, SQS message retention expired, SQS Lambda throttling DLQ, SQS approximateNumberOfMessages, SQS DLQ not FIFO, troubleshoot SQS dead-letter
  invocation_schema: 'Input: either (a) a symptom description ("DLQ filling", "messages not processing", "FIFO queue stuck"), optionally paired with the source queue and DLQ attributes (get-queue-attributes output), OR (b) a QueueURL plus DLQArn for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {MAX_RECEIVE_COUNT_TOO_LOW, VISIBILITY_TIMEOUT_EXCEEDED, MESSAGE_SIZE_LIMIT, BATCH_RECEIVE_FAILURE, FIFO_POISON_MESSAGE, DLQ_TYPE_MISMATCH, REDRIVE_MISCONFIGURED, VISIBILITY_TIMEOUT_RESET, LAMBDA_CONCURRENCY_THROTTLE, MESSAGE_RETENTION_EXPIRED, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline queue classification):\nSymptom: \"SQS source queue orders-queue is draining slowly\nand its DLQ orders-dlq has accumulated 8000 messages in the\nlast hour. The consumer is a Lambda function with a 30s\ntimeout. maxReceiveCount is set to 3.\"\nSourceQueueURL: https://sqs.us-east-1.amazonaws.com/111111111111/orders-queue\nDLQArn: arn:aws:sqs:us-east-1:111111111111:orders-dlq\nRedrivePolicy: {deadLetterTargetArn: \"arn:...orders-dlq\",\n  maxReceiveCount: \"3\"}\nVisibilityTimeout: 30\nMessageRetentionPeriod: 1209600\nLambda Timeout: 30\nLambda EventSourceMapping BatchSize: 10"
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: SQS, dead-letter queue, DLQ, maxReceiveCount, redrive policy, visibility timeout, poison message, FIFO, MessageGroupId, StartMessageMoveTask, message redrive, approximateNumberOfMessages, Lambda trigger, throttling, message retention, troubleshooting
  tags: sqs, appintegration, troubleshooting, dead-letter, fifo, visibility-timeout, redrive, lambda-trigger
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

Symptom-not-cause framing (inspect DLQ messages first; root cause sits on the consumer
or configuration side): [references/advanced-patterns.md](references/advanced-patterns.md).

## Philosophy

Four senior-engineer behaviours (FIFO group blocking, receive attempts not time,
VT vs processing time, v2 redrive API): [references/advanced-patterns.md](references/advanced-patterns.md).

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

Five read-only pre-flight probes (source + DLQ attributes, reverse DLQ lookup,
Lambda mapping, CloudWatch queue metrics): [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Full catalog of non-obvious behaviours (attempt counting, FIFO group blocking, ESM
override, 256 KB, type match, v2 API, approximations): [references/advanced-patterns.md](references/advanced-patterns.md).

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

Probes and interpretation (get-queue-attributes RedrivePolicy, jq parse, DLQ message
receive-count inspection, maxReceiveCount scenario table): [references/diagnostic-commands.md](references/diagnostic-commands.md).

**Verdict:** If maxReceiveCount is 1 or 2 and the consumer has transient
failures (timeouts, downstream throttling), ROOT_CAUSE_IDENTIFIED,
`LAYER: MAX_RECEIVE_COUNT_TOO_LOW`. Fix: raise maxReceiveCount to at
least 3-5.

### Step 3: Lambda concurrency throttling

Symptom: the DLQ is filling and the consumer is a Lambda function.
CloudWatch shows Lambda `Throttles` or `ConcurrentExecutions` at the
account/reserved concurrency limit.

Probes (event source mapping config, Throttles and ConcurrentExecutions metrics,
reserved concurrency) and throttle-cause table: [references/diagnostic-commands.md](references/diagnostic-commands.md).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: LAMBDA_CONCURRENCY_THROTTLE`.
Fix: raise reserved concurrency, raise account-level concurrency limit,
or set a reserved concurrency floor on the SQS consumer Lambda.

### Step 4: Visibility timeout exceeded

Symptom: the DLQ is filling and the consumer's processing time exceeds
the visibility timeout. Messages become visible again during processing,
causing duplicate receives and accelerated receive-count increment.

Probes (queue VT, ESM VT override, Lambda Duration metrics, update mapping) and
failure-mode interpretation: [references/diagnostic-commands.md](references/diagnostic-commands.md).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: VISIBILITY_TIMEOUT_EXCEEDED`.
Fix: raise the visibility timeout on both the queue and the event source
mapping to ≥ 6x the consumer's p99 processing time.

### Step 5: FIFO poison message — group stuck

Symptom: a FIFO queue's throughput drops to zero for a specific
MessageGroupId while other groups continue to flow. Messages in the
stuck group are not being delivered or are failing repeatedly.

Probes (FifoQueue attribute, DLQ message MessageGroupId inspection) and the FIFO
poison diagnosis sequence: [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Probes (MessageRetentionPeriod, ApproximateAgeOfOldestMessage metric) and retention
semantics: [references/diagnostic-commands.md](references/diagnostic-commands.md).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: MESSAGE_RETENTION_EXPIRED`.
Fix: increase `MessageRetentionPeriod` and/or scale the consumer to
drain the backlog faster.

### Step 7: DLQ type mismatch

Symptom: `StartMessageMoveTask` fails with
`InvalidParameterCombination` or messages are not redriving correctly
from the DLQ.

Probes (source vs DLQ FifoQueue types), type-match matrix, and failure list:
[references/diagnostic-commands.md](references/diagnostic-commands.md).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: DLQ_TYPE_MISMATCH`. Fix:
create a FIFO DLQ (with `.fifo` suffix) and update the source queue's
RedrivePolicy.

### Step 8: Redrive misconfigured

Symptom: `StartMessageMoveTask` was called but messages are not moving
from the DLQ back to the source queue.

Probes (start/describe message move task, RedriveAllowPolicy fetch) and the common
redrive-failure table: [references/diagnostic-commands.md](references/diagnostic-commands.md).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: REDRIVE_MISCONFIGURED`.

### Step 9: Visibility timeout reset — duplicate processing

Symptom: the consumer receives duplicate messages (same MessageId
processed multiple times), and the DLQ fills with duplicates.

Probes (duplicate-processing log scan, source ApproximateReceiveCount check) and
reset semantics: [references/diagnostic-commands.md](references/diagnostic-commands.md).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: VISIBILITY_TIMEOUT_RESET`.
Fix: increase the visibility timeout and ensure the consumer is idempotent
(handles duplicate delivery gracefully).

### Step 10: Message size limit

Symptom: the consumer cannot process certain messages, and those
messages accumulate in the DLQ. The consumer logs show payload errors or
truncated data.

Probe (DLQ message body size projection) and 256 KB / Extended Client Library
rules: [references/diagnostic-commands.md](references/diagnostic-commands.md).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: MESSAGE_SIZE_LIMIT`. Fix:
use the SQS Extended Client Library on both producer and consumer, or
reduce payload size.

### Step 11: Batch receive failures

Symptom: the consumer processes messages in batches (Lambda BatchSize >
1) and entire batches are failing, causing all messages in the batch to
increment their receive count simultaneously.

Probe (event source mapping BatchSize / FunctionResponseTypes) and partial-batch
rules: [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Full worked example (Duration p99 45s vs VT 30s; raise VT then redrive):
[references/worked-examples.md](references/worked-examples.md).

### Worked example — Lambda concurrency throttling

Full worked example (reserved concurrency 5 vs 50 msg/s; raise concurrency):
[references/worked-examples.md](references/worked-examples.md).

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

All safety checks (confirmation gate, read-only-first, set-queue-attributes and purge
semantics, move task, concurrency, ESM, bulk batch limit): [references/advanced-patterns.md](references/advanced-patterns.md).

## Remediation guidance

Per-LAYER remediation steps and fix commands (all ten layers):
[references/error-handling.md](references/error-handling.md).

## Deep reference: SQS DLQ layer model

Symptom-to-layer matrix, SQS message lifecycle, maxReceiveCount x VT interaction,
FIFO group behavior, StartMessageMoveTask API, ESM parameters, attribute tables: [references/advanced-patterns.md](references/advanced-patterns.md).

## Recent AWS features (2024-2026)

Recent AWS features (v2 redrive API, SSE-SQS, FIFO high-throughput, delayed metric,
partial batch responses): [references/advanced-patterns.md](references/advanced-patterns.md).

## References (load on demand)

- [Diagnostic commands](references/diagnostic-commands.md) — account-wide pre-flight command listing plus every step's probe commands, tables, and interpretation (Steps 2-11)
- [Worked examples](references/worked-examples.md) — full walkthroughs: visibility timeout exceeded, Lambda concurrency throttling
- [Error handling](references/error-handling.md) — per-LAYER remediation guidance and fix commands moved from SKILL.md
- [Advanced patterns](references/advanced-patterns.md) — mindset, philosophy, Step 0 non-obvious behaviours, pre-flight safety checks, SQS DLQ layer model, recent AWS features
- [FIFO and Lambda consumer reference](references/fifo-and-lambda-consumer-reference.md) — pre-existing deep dive on FIFO ordering and Lambda event source mappings
- [SQS queue and redrive reference](references/sqs-queue-and-redrive-reference.md) — pre-existing queue attribute and redrive policy reference

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
