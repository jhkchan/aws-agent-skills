---
description: Diagnose Amazon SQS messages accumulating in dead-letter queues through a ten-category diagnostic tree (maxReceiveCount too low, visibility timeout exceeded, FIFO poison message, DLQ type mismatch, Lambda concurrency throttling, message retention expiry, batch receive failures, visibility timeout reset, redrive misconfiguration, message size limit) — emits ROOT_CAUSE_IDENTIFIED with the specific failure layer or INSUFFICIENT_DATA.
nl_triggers:
  - "SQS dead-letter queue"
  - "SQS DLQ filling"
  - "SQS messages in DLQ"
  - "SQS maxReceiveCount"
  - "SQS redrive policy"
  - "SQS visibility timeout exceeded"
  - "SQS poison message"
  - "SQS FIFO message group stuck"
  - "SQS MessageGroupId blocked"
  - "SQS start-message-move-task"
  - "SQS redrive from DLQ"
  - "SQS message retention expired"
  - "SQS Lambda throttling DLQ"
  - "SQS approximateNumberOfMessages"
  - "SQS DLQ not FIFO"
  - "troubleshoot SQS dead-letter"
  - "diagnose SQS DLQ accumulation"
routes_to: sqs-dead-letter-troubleshooter
---

# /aws:troubleshoot-sqs-dead-letter

Activate the `sqs-dead-letter-troubleshooter` skill and diagnose an
Amazon SQS dead-letter queue accumulation through the ten-category
diagnostic tree.

## What it does

Reads a symptom description (DLQ filling, FIFO queue stuck, messages
vanishing) plus the queue and DLQ configuration, then walks the
symptom-driven diagnostic tree to a root cause with positive evidence:

1. **Pre-flight** — source queue and DLQ attributes
   (`get-queue-attributes`), DLQ reverse lookup
   (`list-dead-letter-source-queues`), consumer event source mapping
   (`get-event-source-mapping`), CloudWatch queue metrics.
   Short-circuits on DLQ type mismatch, retention expiry risk, or
   disabled event source mapping.
2. **Symptom entry** — map the symptom to one of: maxReceiveCount too
   low, visibility timeout exceeded, FIFO poison message, DLQ type
   mismatch, Lambda concurrency throttling, message retention expired,
   batch receive failure, visibility timeout reset, redrive
   misconfigured, message size limit.
3. **Layer-specific probes** —
   - maxReceiveCount: inspect DLQ messages for `ApproximateReceiveCount`
     vs `maxReceiveCount`.
   - Visibility timeout: compare consumer Duration p99 against
     `VisibilityTimeout` (both queue and event source mapping).
   - FIFO poison: inspect DLQ for common `MessageGroupId`, examine
     poison message body.
   - Lambda throttle: CloudWatch `Throttles` and `ConcurrentExecutions`
     vs reserved concurrency.
   - Retention: `ApproximateAgeOfOldestMessage` vs
     `MessageRetentionPeriod`.
   - DLQ type: compare `FifoQueue` attribute on source and DLQ.
   - Redrive: `describe-message-move-task` status and
     `RedriveAllowPolicy`.
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with failing probe that matches
   the symptom) or INSUFFICIENT_DATA (a probe requires operator input).

Emits a deterministic diagnostic block per target:

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
```

## When to invoke

Paste a symptom description and ask any of:

- "SQS DLQ is filling up"
- "messages accumulating in dead-letter queue"
- "FIFO queue throughput dropped to zero for one group"
- "SQS messages not being processed"
- "StartMessageMoveTask failed"
- "SQS Lambda consumer throttling"

A bare queue name + any symptom ("queue backed up", "DLQ growing",
"messages stuck") also routes here via the orchestrator.

## Inputs

- Symptom description: DLQ growth rate, which messages are affected
  (all vs specific MessageGroupId), consumer type (Lambda, EC2, ECS),
  when the issue started.
- Queue configuration: SourceQueueURL, DLQArn, RedrivePolicy
  (maxReceiveCount), VisibilityTimeout, MessageRetentionPeriod,
  FifoQueue.
- For live-account diagnosis: consumer configuration (Lambda function
  name, event source mapping BatchSize/VisibilityTimeout), CloudWatch
  metrics for the relevant time window. The skill uses
  `get-queue-attributes`, `receive-message`, `list-dead-letter-source-
  queues`, `get-event-source-mapping`, `get-function-concurrency`,
  `get-metric-statistics`, `lookup-events`, `start-message-move-task`,
  `describe-message-move-task`.

## Outputs

- One diagnostic block per source queue / DLQ pair.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: raise maxReceiveCount, raise visibility timeout,
  fix consumer error handling, raise Lambda concurrency, create FIFO DLQ,
  redrive via StartMessageMoveTask, or increase message retention.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for SQS DLQ issues).
- `/aws:troubleshoot-lambda-invocation` for deeper diagnosis when the
  SQS consumer Lambda fails to process messages (timeout, OOM,
  AccessDenied from the handler).
- `/aws:deploy-sqs-fifo` for creating FIFO queues with correct DLQ
  configuration (FIFO DLQ, content-based deduplication, throughput
  settings).
