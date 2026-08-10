---
description: Deploy an AWS SQS queue with production-grade configuration (correct queue type, DLQ with tuned maxReceiveCount, visibility timeout, long polling, SSE-SQS/SSE-KMS encryption, least-privilege access policy, FIFO deduplication, high-throughput FIFO, Lambda partial batch responses). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create sqs queue"
  - "deploy sqs queue"
  - "sqs queue configuration"
  - "sqs dead letter queue"
  - "sqs dlq"
  - "sqs redrive policy"
  - "sqs visibility timeout"
  - "sqs long polling"
  - "sqs encryption"
  - "sqs fifo queue"
  - "sqs content based deduplication"
  - "sqs message group id"
  - "sqs high throughput fifo"
  - "sqs partial batch responses"
  - "sqs access policy"
routes_to: sqs-queue-deployer
---

# /aws:deploy-sqs-queue

Activate the `sqs-queue-deployer` skill and deploy an SQS queue with
production-grade configuration.

## What it does

The skill walks a 10-step deployment procedure and emits a
READY_TO_DEPLOY checklist:

1. Queue type selection (Standard vs FIFO — immutable after creation)
2. Dead-letter queue (correct type, maxReceiveCount, 14-day retention)
3. Visibility timeout (tuned for consumer p99 processing time)
4. Message retention + long polling (cost + reliability)
5. Encryption (SSE-SQS free default vs SSE-KMS customer-managed)
6. Access policy (least-privilege, S3/SNS notification patterns)
7. Redrive policy (link source queue to DLQ)
8. FIFO specifics (deduplication, MessageGroupId, high-throughput)
9. Lambda integration (event source mapping, partial batch responses)
10. Verification commands

## When to use

- You need to create a new SQS queue with production defaults.
- You are deploying a queue to production and want to validate config.
- You need deployment CLI commands or Terraform/SAM templates.
- You want to check for deployment blockers (DLQ type mismatch, missing
  KMS key, FIFO `.fifo` suffix).

## How to invoke

### Slash command

```
/aws:deploy-sqs-queue
```

Then provide: queue name, queue type (Standard/FIFO), DLQ name,
consumer type (Lambda/EC2), workload pattern, and any optional features
(SSE-KMS, high-throughput FIFO, cross-account access).

### Natural language

Any of these routes to the same skill:

- "create an SQS queue"
- "deploy a FIFO queue with a DLQ"
- "set up an SQS queue for S3 notifications"
- "configure high-throughput FIFO"
- "deploy an SQS queue with partial batch responses"

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline. The
output checklist feeds into verification pipelines and audit skills
(sqs-dlq-policy-auditor for post-deployment security checks).

## Example

```
You: /aws:deploy-sqs-queue

     Deploy a production SQS queue "order-events" in us-east-1.
     Standard queue. S3 notifications from bucket "order-uploads".
     Lambda consumer "order-processor" (p99 ~8s). DLQ "order-events-dlq"
     with maxReceiveCount=5, 14-day retention. SSE-SQS. Long polling.
     Account: 111111111111.

Skill:
  QUEUE: order-events
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓]      Queue type — Standard (at-least-once, unlimited TPS)
    [✓]      Dead-letter queue — order-events-dlq (Standard, 14-day retention)
    [✓]      Redrive policy — maxReceiveCount=5
    [✓]      Visibility timeout — 60s (>= Lambda p99 of 8s)
    [✓]      Message retention — 4 days (345600s)
    [✓]      Long polling — ReceiveMessageWaitTimeSeconds=20
    [✓]      Encryption — SSE-SQS (SqsManagedSseEnabled=true)
    [✓]      Access policy — S3 notification pattern (Principal:* + aws:SourceArn)
    [✓]      Lambda partial batch responses — ReportBatchItemFailures
  VERIFICATION_COMMANDS:
    aws sqs get-queue-attributes --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/order-events --attribute-names All
    aws sqs get-queue-attributes --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/order-events --attribute-names RedrivePolicy
    aws sqs get-queue-attributes --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/order-events --attribute-names SqsManagedSseEnabled
```

## References

- Skill definition: `skills/sqs-queue-deployer/SKILL.md`
- Configuration guide: `skills/sqs-queue-deployer/references/queue-configuration-guide.md`
- Deployment CLI commands: `skills/sqs-queue-deployer/references/deployment-cli-commands.md`
- Eval suite: `skills/sqs-queue-deployer/evals/evals.json`
