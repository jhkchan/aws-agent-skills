---
description: Provision an Amazon SQS FIFO queue with production-grade defaults (FifoQueue attributes, content-based/explicit deduplication, DeduplicationScope and ThroughputLimit for high-throughput mode, message group ID ordering, FIFO DLQ with redrive policy, visibility timeout tuning, SSE-KMS encryption, access policy for cross-account delivery). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create sqs fifo queue"
  - "deploy sqs fifo"
  - "fifo queue deduplication"
  - "sqs message group id"
  - "high throughput fifo"
  - "sqs dlq redrive"
  - "sqs visibility timeout"
  - "sqs sse kms"
  - "sqs fifo cross account"
  - "fifo queue"
  - "ordered queue"
  - "sqs fifo"
routes_to: sqs-fifo-deployer
---

# /aws:deploy-sqs-fifo

Activate the `sqs-fifo-deployer` skill and provision an Amazon SQS
FIFO queue with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. FIFO queue attributes (FifoQueue=true, .fifo name suffix)
2. Message group ID for ordering (per-entity partitioning)
3. Deduplication (content-based vs explicit dedup ID)
4. High-throughput FIFO mode (DeduplicationScope + ThroughputLimit)
5. DLQ for FIFO (FIFO DLQ requirement, redrive policy)
6. Visibility timeout tuning (2x processing time rule)
7. SSE-KMS encryption (customer-managed key)
8. Access policy (cross-account producers/consumers)
9. Redrive policy (maxReceiveCount, DLQ movement)
10. Cross-account delivery (access policy + IAM + KMS key policy)
11. Recent features (high-throughput, StartMessageMoveTask)

## When to use

- You need to create an SQS FIFO queue (ordered message delivery).
- You are configuring message group IDs for ordering and parallelism.
- You need content-based or explicit deduplication.
- You want to enable high-throughput FIFO mode.
- You need to attach a FIFO DLQ with a redrive policy.
- You are tuning visibility timeout for consumer processing.
- You need SSE-KMS encryption for queue messages.
- You need cross-account delivery to a FIFO queue.

## When NOT to use

- **SQS Standard queues** — use standard queue skills for
  at-least-once delivery without ordering guarantees.
- **SNS topics** — for pub/sub messaging, not point-to-point queues.
- **Amazon MQ / ActiveMQ** — for traditional message brokers.
- **Kinesis Data Streams** — for real-time streaming with replay.

## How to invoke

### Slash command

```
/aws:deploy-sqs-fifo
```

Then provide: queue name (with .fifo suffix), deduplication strategy
(content-based or explicit), message group ID strategy, visibility
timeout, DLQ name (with .fifo suffix) and maxReceiveCount, KMS key
ARN (if encrypting), cross-account producer account IDs (if cross-
account), tags.

### Natural language

Any of these routes to the same skill:

- "create an SQS FIFO queue with content-based deduplication"
- "set up a high-throughput FIFO queue"
- "configure a FIFO DLQ with redrive policy"
- "enable cross-account delivery to my FIFO queue"
- "create an ordered SQS queue with per-customer ordering"

### CLI routing

```bash
node cli/bin/cli.js route "create an sqs fifo queue"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create SQS FIFO
queues. The output checklist feeds into verification pipelines and
downstream audit skills.

## Example

```
You: /aws:deploy-sqs-fifo

     Create an SQS FIFO queue named order-processing.fifo.
     Content-based deduplication. Per-customer message group IDs.
     Visibility timeout 120s. DLQ: order-processing-dlq.fifo with
     maxReceiveCount 5. SSE-KMS encryption. Cross-account delivery
     from account 999999999999.

Skill:
  SQS_FIFO: order-processing.fifo
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] FifoQueue: true
    [✓] ContentBasedDeduplication: true
    [✓] Message group ID strategy: per-entity (customer ID)
    [✓] Visibility timeout: 120
    [✓] DLQ: order-processing-dlq.fifo — maxReceiveCount: 5
    [✓] SSE-KMS encryption: enabled
    [✓] Cross-account delivery: enabled (producer: 999999999999)
  VERIFICATION_COMMANDS:
    aws sqs get-queue-attributes --queue-url <url> --attribute-names All
```

## References

- Skill definition: `skills/sqs-fifo-deployer/SKILL.md`
- Deduplication and ordering guide: `skills/sqs-fifo-deployer/references/deduplication-and-ordering.md`
- DLQ and throughput guide: `skills/sqs-fifo-deployer/references/dlq-and-throughput.md`
- Eval suite: `skills/sqs-fifo-deployer/evals/evals.json`
