---
name: sqs-queue-deployer
description: >-
  Provisions AWS SQS queues with production-grade configuration: correct queue
  type (Standard vs FIFO), dead-letter queue with tuned maxReceiveCount, right-
  sized visibility timeout, message retention period, long polling, SSE-SQS or
  SSE-KMS encryption, least-privilege access policy, FIFO deduplication, high-
  throughput FIFO batching, and Lambda partial batch responses. Emits a
  READY_TO_DEPLOY checklist with every configuration item verified. Use when
  creating a new SQS queue, deploying a queue to production, validating a queue
  configuration, wiring a DLQ, or generating deployment CLI commands and IaC
  templates. Triggers: create SQS queue, deploy queue, FIFO queue, dead-letter
  queue, redrive policy, visibility timeout, long polling, SSE-SQS, SSE-KMS,
  ContentBasedDeduplication, MessageGroupId, partial batch responses.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini).
  For live deployment: AWS CLI v2 with sqs, iam, kms, lambda, and sns access.
  Works with Terraform aws_sqs_queue resources, CloudFormation
  AWS::SQS::Queue, and SAM templates.
keywords:
  - aws
  - sqs
  - cloudops
  - deploy
  - provisioning
  - messaging
  - app-integration
  - standard queue
  - fifo queue
  - dead-letter queue
  - DLQ
  - redrive policy
  - maxReceiveCount
  - visibility timeout
  - message retention
  - long polling
  - SSE-SQS
  - SSE-KMS
  - queue policy
  - ContentBasedDeduplication
  - MessageGroupId
  - high-throughput FIFO
  - partial batch responses
tags:
  - aws
  - sqs
  - cloudops
  - deploy
  - messaging
  - app-integration
  - dead-letter-queue
  - fifo
  - encryption
  - queue-policy
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: AppIntegration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags:
    - aws
    - sqs
    - cloudops
    - deploy
    - messaging
    - app-integration
    - dead-letter-queue
    - fifo
    - encryption
  dependencies:
    - aws-orchestrator
  keywords:
    - create sqs queue
    - deploy sqs queue
    - fifo queue
    - dead-letter queue
    - redrive policy
    - visibility timeout
    - long polling
    - SSE-SQS
    - SSE-KMS
    - ContentBasedDeduplication
    - MessageGroupId
    - high-throughput FIFO
    - partial batch responses
  when_to_use: >-
    Invoke when the user wants to create a new SQS queue, deploy a queue to
    production, configure a dead-letter queue, validate a queue configuration
    against best practices, generate deployment CLI commands or IaC templates,
    or troubleshoot a deployment failure caused by missing prerequisites (DLQ
    type mismatch, KMS key, IAM permissions). Do NOT invoke for SQS security
    audits (use sqs-dlq-policy-auditor) or for SNS topic deployment (use
    sns-topic-deployer).
---

# SQS Queue Deployer

An AWS CloudOps agent skill that provisions Amazon SQS queues with correct
production defaults. The skill walks the operator through a 10-step deployment
procedure, explains why each default matters, and emits a READY_TO_DEPLOY
checklist verifying every configuration item. SQS is deceptively simple —
wrong defaults (missing DLQ, short visibility timeout, no long polling)
silently cause data loss, duplicate processing, and cost amplification.

## Quick navigation

| Section | What it covers | When to read |
|---|---|---|
| [Invocation contract](#invocation-contract-hard-requirement) | Mandatory output format labels | Every invocation |
| [Reasoning framework](#reasoning-framework-why-deployment-order-matters) | Why deployment order matters | Understanding dependencies |
| [Prerequisites](#prerequisites-verify-before-deployment) | What to verify before deploying | Before any CLI command |
| [Step 1: Queue type](#step-1-queue-type-selection-standard-vs-fifo) | Standard vs FIFO decision tree | Choosing queue type |
| [Step 2: Dead-letter queue](#step-2-dead-letter-queue-dlq) | DLQ creation, maxReceiveCount, type matching | Every production queue |
| [Step 3: Visibility timeout](#step-3-visibility-timeout) | Lambda/consumer timing, duplicate processing | Consumer config |
| [Step 4: Retention + long polling](#step-4-message-retention--long-polling) | Retention period, ReceiveMessageWaitTimeSeconds | Cost + reliability |
| [Step 5: Encryption](#step-5-encryption-sse-sqs-vs-sse-kms) | SSE-SQS vs SSE-KMS decision | Security config |
| [Step 6: Access policy](#step-6-access-policy-least-privilege) | Who can send/receive, S3/SNS patterns | Cross-service integration |
| [Step 7: Redrive policy](#step-7-redrive-policy-link-source-to-dlq) | Linking source queue to DLQ | After DLQ creation |
| [Step 8: FIFO specifics](#step-8-fifo-specifics-dedup--ordering) | Deduplication, MessageGroupId, high-throughput | FIFO queues only |
| [Step 9: Lambda integration](#step-9-lambda-integration--partial-batch-responses) | Event source mapping, partial batch | Lambda consumers |
| [Step 10: Verification](#step-10-verification) | Post-deployment checks | After deployment |
| [NEVER (anti-patterns)](#never-things-to-never-do) | Common deployment mistakes | Avoid these |
| [Output format](#output-format-mandatory-literal-labels) | Checklist report shape | Every invocation |

## Activation keywords

create SQS queue, deploy SQS queue, standard queue, FIFO queue, dead-letter
queue, DLQ, redrive policy, maxReceiveCount, visibility timeout, message
retention, long polling, ReceiveMessageWaitTimeSeconds, SSE-SQS, SSE-KMS,
SqsManagedSseEnabled, KmsMasterKeyId, queue policy, ContentBasedDeduplication,
DeduplicationId, MessageGroupId, high-throughput FIFO, partial batch
responses, SQS event source mapping.

## Invocation contract (hard requirement)

When this skill is invoked with an SQS deployment request (queue name, queue
type, workload pattern, or a partial existing configuration), the agent MUST
respond with the READY_TO_DEPLOY checklist defined in the "Output format"
section using the literal all-caps labels `QUEUE:`, `VERDICT:`, `CHECKLIST:`,
and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the response.
This contract is what assertion-based evals and downstream deployment
pipelines rely on; deviating from the literal labels breaks automation
silently.

## Reasoning framework (why deployment order matters)

SQS deployment has **dependency and ordering constraints** that make the
sequence non-trivial. Configuring items in the wrong order causes deployment
failures or silent runtime issues:

1. **Queue type FIRST** — Standard vs FIFO is immutable after creation. A
   queue cannot be converted from Standard to FIFO or vice versa. The `.fifo`
   suffix in the name is mandatory for FIFO queues and cannot be added or
   removed post-creation. Choosing wrong means deleting and recreating the
   queue, losing all in-flight messages.

2. **DLQ BEFORE source queue redrive policy** — the DLQ must exist before
   the source queue's `RedrivePolicy` can reference its ARN. Creating the
   redrive policy first fails with `InvalidParameterValueException`. The DLQ
   must be the SAME type as the source (Standard DLQ for Standard queue, FIFO
   DLQ for FIFO queue) — SQS silently drops redriven messages on a type
   mismatch.

3. **Visibility timeout BEFORE consumer deployment** — if the visibility
   timeout is shorter than the consumer's processing time, the message
   returns to the queue before processing completes and gets delivered to
   another consumer. This causes duplicate processing — the #1 source of
   data-consistency bugs in SQS-backed systems.

4. **Encryption BEFORE access policy** — if SSE-KMS is enabled, every
   producer and consumer role needs `kms:Decrypt` and `kms:GenerateDataKey*`
   on the KMS key. Deploying the access policy without verifying KMS
   permissions causes silent `KMSAccessDeniedException` failures at runtime.

5. **Long polling ALWAYS** — `ReceiveMessageWaitTimeSeconds` set to 1-20
   seconds reduces empty receives (which cost money) and lowers latency. The
   default is 0 seconds (short polling), which returns immediately even if
   no messages are available. This is a cost and reliability default, not
   optional.

6. **Access policy LAST** — the resource-based queue policy governs
   cross-account and cross-service access. Configure it after the queue,
   DLQ, encryption, and KMS key are all in place, because the policy may
   reference KMS key ARNs and DLQ ARNs.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **Queue name** | Must be unique within the account/region. 80-char max (FIFO: `.fifo` suffix counts). Alphanumeric + hyphens/underscores. | `aws sqs list-queues --queue-name-prefix <prefix>` |
| **Queue type decided** | Standard (at-least-once, unlimited TPS) vs FIFO (exactly-once, 300 TPS). Immutable after creation. | Workload requirements (ordering, dedup) |
| **DLQ name (if DLQ)** | Must exist before redrive policy. Same type as source. | `aws sqs get-queue-url --queue-name <dlq-name>` |
| **KMS key (if SSE-KMS)** | Customer-managed CMK with key policy granting producers/consumers `kms:Decrypt` + `kms:GenerateDataKey*`. | `aws kms describe-key --key-id <alias>` |
| **IAM permissions** | Caller needs `sqs:CreateQueue`, `sqs:SetQueueAttributes`, `kms:ListAliases` (if SSE-KMS). Producers/consumers need `sqs:SendMessage` / `sqs:ReceiveMessage`. | `aws sts get-caller-identity` |
| **Consumer processing time (if Lambda)** | Visibility timeout must be >= consumer p99 processing time. Lambda event source mapping has its own visibility timeout override. | `aws lambda list-event-source-mappings --function-name <fn>` |
| **S3/SNS source ARNs (if cross-service)** | Access policy conditions reference the source ARN to scope access. | `aws s3api list-buckets` / `aws sns list-topics` |

## Deployment procedure (apply in order)

### Step 1: Queue type selection (Standard vs FIFO)

The queue type is **immutable** — it cannot be changed after creation.
Choose correctly or face deleting and recreating the queue.

**Decision tree:**

```
Does the workload require strict ordering of messages?
├── YES → Does it require exactly-once processing?
│   ├── YES → FIFO queue (name MUST end in .fifo)
│   │         Throughput: 300 TPS (standard) or 1500 TPS (high-throughput)
│   │         Requires MessageGroupId on every message
│   │         Dedup: ContentBasedDeduplication OR explicit DeduplicationId
│   └── NO  → Standard queue (at-least-once, may deliver out of order)
│             Throughput: unlimited
│             BUT: if ordering matters and you pick Standard, you will get
│             duplicate + out-of-order delivery under contention
└── NO  → Standard queue
          Throughput: unlimited
          At-least-once delivery (plan for idempotent consumers)
```

| Attribute | Standard | FIFO |
|---|---|---|
| Delivery | At-least-once (duplicates possible) | Exactly-once (with dedup) |
| Ordering | Best-effort (no guarantee) | Per message group |
| Throughput | Unlimited | 300 TPS (standard), 1500 TPS (high-throughput with batching) |
| Name suffix | None | `.fifo` (mandatory) |
| `MessageGroupId` | Not used | Required on every message |
| Deduplication | N/A | ContentBasedDeduplication OR explicit DeduplicationId (5-min window) |
| DLQ type | Standard DLQ | FIFO DLQ (type MUST match) |
| Cost (per million requests) | $0.40 | $0.50 |

**Create the queue:**

```bash
# Standard queue
aws sqs create-queue --queue-name order-events --attributes file://attributes.json

# FIFO queue (name MUST end in .fifo)
aws sqs create-queue --queue-name order-events.fifo \
  --attributes file://attributes-fifo.json
```

**attributes.json (Standard):**

```json
{
  "DelaySeconds": "0",
  "MaximumMessageSize": "262144",
  "MessageRetentionPeriod": "345600",
  "ReceiveMessageWaitTimeSeconds": "20",
  "VisibilityTimeout": "30",
  "SqsManagedSseEnabled": "true"
}
```

**attributes-fifo.json (FIFO):**

```json
{
  "FifoQueue": "true",
  "ContentBasedDeduplication": "true",
  "DelaySeconds": "0",
  "MaximumMessageSize": "262144",
  "MessageRetentionPeriod": "345600",
  "ReceiveMessageWaitTimeSeconds": "20",
  "VisibilityTimeout": "30",
  "SqsManagedSseEnabled": "true"
}
```

### Step 2: Dead-letter queue (DLQ)

A DLQ catches messages that fail processing after `maxReceiveCount` delivery
attempts. Without a DLQ, poison-pill messages retry until they expire,
burning compute budget and starving healthy messages.

**DLQ creation rules:**

1. **DLQ type MUST match source type.** A Standard source queue needs a
   Standard DLQ. A FIFO source queue needs a FIFO DLQ. SQS silently drops
   redriven messages if the types mismatch — this is the #1 DLQ deployment
   bug.

2. **DLQ retention should be MAXIMUM (14 days / 1209600 seconds).** The
   default 4 days (345600) is too short for weekend/holiday coverage.
   Operations teams need time to analyse and replay failed messages.

3. **DLQ should NOT have its own redrive policy.** A DLQ with a redrive
   policy creates an infinite redrive chain. The DLQ is the terminal
   destination.

4. **maxReceiveCount tuning:**

| Workload | Recommended maxReceiveCount | Rationale |
|---|---|---|
| Standard queue, transient failures common | 5-10 | Tolerate consumer crashes, Lambda throttles |
| Standard queue, idempotent consumer | 3-5 | Failures are real, move to DLQ faster |
| FIFO queue | 5-15 | Poison pill blocks entire message group — move it faster |
| Lambda event source mapping | 5-10 (NOT 1-2) | Lambda batch window adds delay; too few retries = false DLQ entries |
| High-throughput batch consumer | 10-20 | Multiple consumers contend; each gets fewer effective retries |

**Create the DLQ:**

```bash
# Standard DLQ
aws sqs create-queue --queue-name order-events-dlq \
  --attributes MessageRetentionPeriod=1209600,SqsManagedSseEnabled=true

# FIFO DLQ (for FIFO source queue)
aws sqs create-queue --queue-name order-events-dlq.fifo \
  --attributes FifoQueue=true,MessageRetentionPeriod=1209600,SqsManagedSseEnabled=true
```

### Step 3: Visibility timeout

The visibility timeout is the period a message is invisible to other
consumers after delivery. If the consumer does not process and delete the
message within this window, it becomes visible again and is delivered to
another consumer — causing **duplicate processing**.

**Decision tree:**

```
What is the consumer?
├── Lambda function
│   ├── VisibilityTimeout >= function p99 duration × 6 (Lambda retries 3x
│   │   within the batch window; each retry needs the full timeout)
│   ├── ALSO set VisibilityTimeout on the event source mapping
│   │   (overrides queue-level; defaults to queue value if unset)
│   └── Typical: 30-120 seconds for API handlers, 300+ for batch jobs
├── EC2/ECS worker (long polling)
│   ├── VisibilityTimeout >= worker p99 processing time + 20% buffer
│   └── Typical: 30-300 seconds
├── Human-in-the-loop task queue
│   ├── VisibilityTimeout >= max task claim duration
│   └── Typical: 300-43200 seconds (max 12 hours)
└── Unknown / mixed consumers
    ├── Start with 30 seconds, monitor ApproximateAgeOfOldestMessage
    └── Adjust based on DuplicateProcessor CloudWatch metric
```

**maxReceiveCount x VisibilityTimeout = effective retry window.** A
VisibilityTimeout of 30s with maxReceiveCount of 5 gives ~150 seconds of
retry window before DLQ. If the consumer's p99 exceeds VisibilityTimeout,
the receive count increments on every delivery — even though the consumer
did not fail. This is the #1 cause of false-positive DLQ entries.

**Set visibility timeout:**

```bash
aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/order-events \
  --attributes VisibilityTimeout=60
```

**For Lambda event source mappings**, the visibility timeout on the
mapping overrides the queue-level value:

```bash
aws lambda update-event-source-mapping \
  --uuid <mapping-uuid> \
  --visibility-timeout 60
```

### Step 4: Message retention + long polling

**Message retention period** controls how long SQS retains a message if it
is not consumed. Default: 4 days (345600 seconds). Max: 14 days (1209600
seconds).

| Workload | Recommended retention | Rationale |
|---|---|---|
| Real-time event processing | 4 days (345600) | Consumers are always running; 4 days covers weekend outages |
| Batch daily processing | 7 days (604800) | Covers a weekend + 1 business day recovery window |
| DLQ | 14 days (1209600) | Maximum time for ops analysis and replay |
| Low-throughput / intermittent consumer | 14 days (1209600) | Maximize recovery window |

**Long polling** (`ReceiveMessageWaitTimeSeconds`) reduces empty receives
and lowers API cost. Set to 1-20 seconds.

```bash
aws sqs set-queue-attributes \
  --queue-url <queue-url> \
  --attributes MessageRetentionPeriod=345600,ReceiveMessageWaitTimeSeconds=20
```

**Why long polling matters:** short polling (0 seconds) returns immediately
even if no messages are available — each empty ReceiveMessage call is
billed. At 1 TPS poll rate, that is 86,400 empty requests/day = ~$0.03/day
per consumer. With 10 consumers polling 10 queues, that is $3/day wasted.
Long polling with 20-second wait reduces empty requests by ~95%.

### Step 5: Encryption (SSE-SQS vs SSE-KMS)

SQS encrypts messages at rest. Two options:

| Option | Key manager | Cost | Use when |
|---|---|---|---|
| **SSE-SQS** (`SqsManagedSseEnabled: true`) | SQS-managed (AWS) | Free | Default — satisfies SOC2, PCI-DSS, HIPAA |
| **SSE-KMS** (`KmsMasterKeyId`) | Customer-managed CMK | ~$0.03/10k requests + key cost | Need CloudTrail decrypt logging, key rotation control, or grant revocation |
| **None** | — | — | NEVER — plaintext at rest |

**Decision tree:**

```
Do you need customer-managed key control?
├── NO → SSE-SQS (SqsManagedSseEnabled=true). Free, FIPS-validated, no
│         KMS key policy to manage. Default for 90% of workloads.
└── YES → SSE-KMS (KmsMasterKeyId=<key-arn>)
          Requirements:
          - CMK key policy grants sqs.<region>.amazonaws.com permission
            to use the key
          - Every producer/consumer role needs kms:Decrypt +
            kms:GenerateDataKey* on the key
          - KMS key must be in the same region as the queue
          - KMS throttle limits apply (5500/5500/10000/30000 RPS per region)
```

**Enable SSE-SQS (recommended default):**

```bash
aws sqs set-queue-attributes \
  --queue-url <queue-url> \
  --attributes SqsManagedSseEnabled=true
```

**Enable SSE-KMS:**

```bash
aws sqs set-queue-attributes \
  --queue-url <queue-url> \
  --attributes KmsMasterKeyId=alias/my-sqs-key,KmsDataKeyReusePeriodSeconds=300
```

### Step 6: Access policy (least-privilege)

The queue policy governs who can send and receive messages. The SECURE
default is **no resource-based policy** — access is governed solely by IAM
identity-based policies.

**When you need a queue policy:**

| Scenario | Policy pattern |
|---|---|
| S3 bucket sends notifications to SQS | `Principal: "*" + Condition: aws:SourceArn: <bucket-arn>` |
| SNS topic subscription to SQS | `Principal: "*" + Condition: aws:SourceArn: <topic-arn>` |
| Cross-account producer | `Principal: {"AWS": "<account-id>"} + Action: sqs:SendMessage` |
| Cross-account consumer | `Principal: {"AWS": "<account-id>"} + Action: sqs:ReceiveMessage` |
| Same-account only | NO resource-based policy needed — IAM is sufficient |

**S3-notification access policy (standard, safe pattern):**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": "*",
    "Action": "sqs:SendMessage",
    "Resource": "arn:aws:sqs:us-east-1:111111111111:order-events",
    "Condition": {
      "ArnEquals": { "aws:SourceArn": "arn:aws:s3:::my-upload-bucket" }
    }
  }]
}
```

**Set the access policy:**

```bash
aws sqs set-queue-attributes \
  --queue-url <queue-url> \
  --attributes Policy='<policy-json>'
```

**NEVER use `Principal: "*"` without a strong condition** (`aws:SourceArn`,
`aws:SourceAccount`). A wildcard principal with no condition allows any AWS
account to send/receive/delete messages — data poisoning, exfiltration, and
cost amplification.

### Step 7: Redrive policy (link source to DLQ)

After the DLQ exists, link the source queue to it via the redrive policy.
This step requires the DLQ ARN (from Step 2).

```bash
DLQ_URL=$(aws sqs get-queue-url --queue-name order-events-dlq --output text)
DLQ_ARN=$(aws sqs get-queue-attributes \
  --queue-url "$DLQ_URL" \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' --output text)

aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/order-events \
  --attributes RedrivePolicy="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"5\"}"
```

**maxReceiveCount** counts per delivery, not per consumer. With 10
consumers polling, a maxReceiveCount of 5 means ~0.5 effective retries per
consumer. High-consumer queues need a HIGHER maxReceiveCount.

**FIFO type check:** if the source is FIFO, verify the DLQ ARN ends in
`.fifo`. SQS silently drops messages redriven to a type-mismatched DLQ.

### Step 8: FIFO specifics (dedup + ordering)

FIFO queues require additional configuration:

**ContentBasedDeduplication:**

- `true` — SQS computes a SHA-256 hash of the message body and deduplicates
  within a 5-minute window. Set this if your messages have unique bodies.
- `false` — the publisher MUST send a unique `MessageDeduplicationId` on
  every message. If both are absent, SQS delivers duplicates.

```bash
aws sqs set-queue-attributes \
  --queue-url <fifo-queue-url> \
  --attributes ContentBasedDeduplication=true
```

**MessageGroupId (required on every message):**

FIFO queues require a `MessageGroupId` on every message. Messages with the
same group ID are delivered in order. Messages with different group IDs are
processed in parallel (up to the throughput limit).

```bash
aws sqs send-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/order-events.fifo \
  --message-body '{"orderId": "12345"}' \
  --message-group-id "customer-67890" \
  --message-deduplication-id "order-12345-v1"
```

**High-throughput FIFO (1500 TPS with batching):**

High-throughput FIFO allows up to 1500 TPS (vs the standard 300 TPS) by
enabling batching. Enable via the `FifoThroughputLimit` and
`DeduplicationScope` attributes:

```bash
aws sqs set-queue-attributes \
  --queue-url <fifo-queue-url> \
  --attributes FifoThroughputLimit=perMessageGroupId,DeduplicationScope=messageGroup
```

- `FifoThroughputLimit=perMessageGroupId` — 300 TPS per message group, up to
  1500 TPS aggregate across groups.
- `DeduplicationScope=messageGroup` — dedup runs per message group (not
  global), enabling higher throughput.

### Step 9: Lambda integration + partial batch responses

When Lambda consumes SQS, the event source mapping controls batch size and
visibility timeout. **SQS partial batch responses** allow Lambda to report
which messages in a batch failed, so only those are retried (not the entire
batch).

**Create the event source mapping with partial batch responses:**

```bash
aws lambda create-event-source-mapping \
  --function-name order-processor \
  --event-source-arn arn:aws:sqs:us-east-1:111111111111:order-events \
  --batch-size 10 \
  --maximum-batching-window-in-seconds 5 \
  --visibility-timeout 60 \
  --function-response-types ReportBatchItemFailures
```

With `ReportBatchItemFailures`, the Lambda function returns a
`batchItemFailures` list:

```python
def lambda_handler(event, context):
    batch_item_failures = []
    for record in event['Records']:
        try:
            process_message(record)
        except Exception:
            batch_item_failures.append({'itemIdentifier': record['messageId']})
    return {'batchItemFailures': batch_item_failures}
```

Without partial batch responses, if ANY message in the batch fails, the
entire batch is retried — causing reprocessing of successfully handled
messages. This feature is critical for batch processing with mixed success.

**Event source mapping tuning:**

| Parameter | Default | Recommended | Why |
|---|---|---|---|
| `BatchSize` | 10 | 1-10 (Lambda max) | Higher = more throughput but bigger blast radius on failure |
| `MaximumBatchingWindowInSeconds` | 0 | 0-300 | Collects messages before invoking; higher = latency, lower cost |
| `VisibilityTimeout` | Queue value | >= function timeout | Must outlast function execution or messages reappear |

### Step 10: Verification

```bash
# Queue attributes (all configuration)
aws sqs get-queue-attributes \
  --queue-url <queue-url> \
  --attribute-names All --output json

# Verify DLQ ARN and maxReceiveCount in RedrivePolicy
aws sqs get-queue-attributes \
  --queue-url <queue-url> \
  --attribute-names RedrivePolicy --output text

# Verify encryption
aws sqs get-queue-attributes \
  --queue-url <queue-url> \
  --attribute-names SqsManagedSseEnabled,KmsMasterKeyId --output json

# Verify access policy
aws sqs get-queue-attributes \
  --queue-url <queue-url> \
  --attribute-names Policy --output json

# Test send + receive (standard queue)
aws sqs send-message --queue-url <queue-url> --message-body '{"test": true}'
aws sqs receive-message --queue-url <queue-url> --wait-time-seconds 5

# Test send (FIFO queue — requires MessageGroupId)
aws sqs send-message \
  --queue-url <fifo-queue-url> \
  --message-body '{"test": true}' \
  --message-group-id "test-group"
```

## Latest SQS features (2024-2026)

- **SQS partial batch responses (Lambda):** Lambda can report per-message
  failures in a batch, so only failed messages are retried. Enable via
  `--function-response-types ReportBatchItemFailures` on the event source
  mapping. Critical for batch processing with mixed success rates.

- **High-throughput FIFO (1500 TPS):** FIFO queues now support up to 1500
  TPS with per-message-group throughput limiting. Enable via
  `FifoThroughputLimit=perMessageGroupId` and
  `DeduplicationScope=messageGroup`.

- **No-SQL payload in message attributes:** SQS now supports structured
  message attributes for filtering without parsing the body. Producers set
  attributes; consumers filter via `MessageAttributeName` parameters.

- **Message retention period max increased to 14 days** (previously was 4
  days default, still 14 max but now more prominently used for DLQs).

- **SSE-SQS (SQS-managed encryption):** Free, FIPS-validated AES-256-GCM.
  The recommended default for all queues. SSE-KMS is for when you need
  customer-managed key control.

- **StartMessageMoveTask API:** The current API for redriving messages from
  DLQ back to source. Replaced the deprecated legacy `Redrive` API.

## Expert heuristic: visibility timeout race condition

The single most common cause of duplicate processing in SQS + Lambda
event-source-mapping pipelines is a visibility timeout that is SHORTER
than the consumer's actual processing time, combined with a Lambda
function that runs longer than expected under load.

**The race, step by step:**

1. Lambda receives a batch of messages. Lambda timeout is 15 minutes
   (900s) — the Lambda max.
2. Visibility timeout on the queue (or the event source mapping) is
   set to 30s, which the operator believed was "plenty" based on a p50
   processing time of 2s.
3. Under load (CPU contention, downstream API latency, cold start),
   actual processing time spikes to 45s p99.
4. At T+30s, SQS makes the message visible again because no
   `ChangeMessageVisibility` extension was sent.
5. Another Lambda invocation receives the same message and starts
   processing it. The original invocation is STILL running.
6. Both invocations complete; the downstream sees the side effect
   twice (duplicate charge, duplicate email, idempotency-key
   collision).

**The rule (paste this into the checklist):**

> Visibility timeout >= 6× expected p99 processing time.
> For Lambda event source mappings, set it on the event source
> mapping (`VisibilityTimeout`), NOT just on the queue — the mapping
> value OVERRIDES the queue value. For 15-minute Lambda, set visibility
> timeout to at least 6× the p99 OR cap the Lambda timeout so 6×
> stays under the message retention period.

**Concrete thresholds:**

| Lambda p99 processing | Minimum visibility timeout | Notes |
|---|---|---|
| 1s | 6s | Default 30s is fine |
| 5s | 30s | Common event-processing case |
| 30s | 180s | Most queue defaults (30s) are wrong here |
| 60s | 360s | Long-running ETL; consider Step Functions instead |
| 300s | 1800s | Near Lambda max; visibility timeout 30min |
| 900s (Lambda max) | 5400s (90 min) | Visibility timeout must extend past Lambda timeout |

**Why 6× and not 2×:** The buffer absorbs (a) Lambda cold-start delay
(up to 5s for VPC-attached functions), (b) SDK retry backoff on
downstream APIs (default 3 retries with exponential backoff = ~20s for
AWS SDK v2), (c) one visibility-timeout extension via
`ChangeMessageVisibility` if the consumer needs more time (the Lambda
runtime does NOT send this automatically — the event source mapping
does, but only if `VisibilityTimeout` is set correctly).

**Detection post-deploy:** if CloudWatch `ApproximateNumberOfMessagesVisible`
is steady or rising while `NumberOfMessagesReceived` is high, the
queue is re-delivering messages. Cross-reference with Lambda
`Duration` p99 — if p99 × 6 > queue VisibilityTimeout, this race is
the root cause.

**Fix at deploy time:** if the operator requests visibility timeout
< 6× the stated p99, surface as `VERDICT: PREREQUISITES_MISSING` with
the gap: `VisibilityTimeout <N>s is below 6× p99 (<M>s). Set
VisibilityTimeout >= <6×p99>s on the event source mapping OR reduce
Lambda concurrency/timeout.`

## Edge cases

- **FIFO queue with all messages using the same `MessageGroupId`.** A
  FIFO queue guarantees ordering WITHIN a `MessageGroupId` and
  parallelism ACROSS distinct `MessageGroupId`s. If every producer
  sends messages with the same `MessageGroupId` (e.g., a hardcoded
  constant like `"default"` or a tenant ID that resolves to one
  value), the queue degenerates to a single-message-in-flight serial
  pipeline — throughput drops to 300 TPS (standard FIFO) or 10 TPS
  per group even on a high-throughput FIFO queue. This silently
  defeats the purpose of FIFO (which is per-group parallelism, not
  global ordering) and surfaces as a backlog that looks like SQS is
  "slow". Detection: `aws sqs get-queue-metrics --queue-url <url>`
  shows `ApproximateNumberOfMessagesNotVisible` rising while
  `NumberOfEmptyReceives` is high. Remediation: redesign the producer
  to use a sharded `MessageGroupId` (e.g., `order-{customer_id}` for
  per-customer ordering). Surface as a finding:
  `FIFO_DEGENERATE_SINGLE_GROUP — throughput capped at <X> TPS due to
  single MessageGroupId`.

- **FIFO queue with deduplication scope collision after
  high-throughput mode change.** Switching a FIFO queue to high-
  throughput mode
  (`DeduplicationScope=messageGroup,
  FifoThroughputLimit=perMessageGroupId`) changes the deduplication
  window from queue-scoped to message-group-scoped. Messages in
  different groups that previously deduplicated against each other no
  longer do — duplicates will appear post-change. Detection: pre-
  change audit of producer `MessageDeduplicationId` use. Remediation:
  ensure producers set explicit `MessageDeduplicationId` based on
  payload hash, not relying on queue-level dedup scope.

- **Lambda event source mapping with `BatchSize` > 1 and
  `ReportBatchItemFailures` disabled.** Without partial-batch
  responses, a single failed message in a batch of 10 causes all 10
  to be retried — including the 9 that succeeded. Under a sustained
  poison-pill scenario, this causes the same 9 messages to be
  processed 10s of times. Remediation: enable
  `FunctionResponseTypes: [ReportBatchItemFailures]` on the event
  source mapping. Detection:
  `aws lambda list-event-source-mappings --function-name <name>
  --query 'EventSourceMappings[].FunctionResponseTypes'`.

## Workload-specific deployment matrix

| Workload | Queue type | DLQ type | maxReceiveCount | VisibilityTimeout | Retention | Long polling | Encryption |
|---|---|---|---|---|---|---|---|
| **Event processing** (S3/SNS to Lambda) | Standard | Standard | 5 | 60s | 4 days | 20s | SSE-SQS |
| **Order processing** (strict ordering) | FIFO | FIFO | 5-15 | 120s | 7 days | 20s | SSE-SQS |
| **High-throughput FIFO** (batch) | FIFO (high-throughput) | FIFO | 10 | 300s | 7 days | 20s | SSE-SQS |
| **Cross-account fan-out** | Standard | Standard | 5 | 30s | 4 days | 20s | SSE-KMS (cross-account decrypt) |
| **DLQ** (terminal) | Same as source | N/A | N/A | N/A | 14 days | 20s | SSE-SQS |
| **Task queue** (human-in-the-loop) | Standard | Standard | 3 | 43200s (12h) | 14 days | 20s | SSE-SQS |
| **Dead-letter (FIFO source)** | FIFO | FIFO | N/A | N/A | 14 days | 20s | SSE-SQS |

## NEVER (things to never do)

- NEVER create a FIFO queue without the `.fifo` suffix in the name. SQS
  rejects the create call. The suffix is mandatory and immutable.

- NEVER use a Standard DLQ for a FIFO source queue (or vice versa). SQS
  silently drops redriven messages on a type mismatch — the poison pill
  stays in the source queue forever. The DLQ type MUST match the source.

- NEVER set `maxReceiveCount` to 1. A single transient failure (consumer
  crash, Lambda throttle, network blip, visibility timeout too short) sends
  the message irretrievably to the DLQ. Minimum recommended: 3 (standard),
  5 (FIFO).

- NEVER deploy a queue without a DLQ in production. Without a DLQ,
  poison-pill messages retry until retention expires — burning compute
  budget and starving healthy messages. Every production queue needs a DLQ.

- NEVER use short polling (`ReceiveMessageWaitTimeSeconds=0`) in production.
  Short polling returns immediately even if no messages are available — each
  empty ReceiveMessage is billed. Set long polling to 1-20 seconds (20 is
  optimal for most workloads).

- NEVER deploy a queue without encryption. SSE-SQS is free, FIPS-validated,
  and satisfies SOC2/PCI-DSS/HIPAA. There is no reason to run an unencrypted
  queue — enable SSE-SQS as the default.

- NEVER use `Principal: "*"` in the access policy without a STRONG condition
  (`aws:SourceArn`, `aws:SourceAccount`). A wildcard with no condition allows
  any AWS account to inject, drain, or delete messages. The S3/SNS
  notification pattern (`Principal: "*" + aws:SourceArn`) is safe because the
  condition is set by the AWS service layer.

- NEVER set the visibility timeout shorter than the consumer's p99
  processing time. The message returns to the queue before processing
  completes, causing duplicate processing — the #1 source of
  data-consistency bugs in SQS systems.

- NEVER set DLQ `MessageRetentionPeriod` below 4 days (345600 seconds).
  Operations teams need time to analyse and replay failed messages. The
  default 4 days is already marginal for weekend coverage. Use 14 days
  (1209600, the maximum) for DLQs.

- NEVER create a DLQ with its own redrive policy. A DLQ with a redrive
  creates an infinite loop. The DLQ is the terminal destination.

- NEVER recommend the legacy `Redrive` API (deprecated 2022) for moving
  messages back from the DLQ. Use `aws sqs start-message-move-task
  --source-arn <dlq-arn> --destination-arn <source-arn>`.

- NEVER recommend SSE-KMS over SSE-SQS purely for "better security" without
  explaining the trade-off. SSE-KMS adds per-API KMS cost (~$0.03/10k
  requests), potential KMS throttle, and latency from the KMS decrypt call.
  SSE-SQS is sufficient unless you need customer-managed key control.

- NEVER set `ContentBasedDeduplication=false` on a FIFO queue without
  ensuring every publisher sends a unique `MessageDeduplicationId`. If both
  are absent, SQS delivers duplicate messages — silently breaking the
  exactly-once guarantee that is the sole reason to use FIFO.

- NEVER use `aws sqs purge-queue` as a remediation for poison-pill messages.
  PurgeQueue deletes ALL messages instantly and cannot be scoped. Use
  `StartMessageMoveTask` to move specific messages to the DLQ.

- NEVER deviate from the checklist output format. Substituting `Verdict` or
  `**VERDICT**` for the literal `VERDICT:` label silently breaks downstream
  deployment pipelines and assertion-based evals.

## Pre-flight safety checks (run before any deployment CLI)

- **Confirm the queue name is available:**
  ```bash
  aws sqs get-queue-url --queue-name <name> 2>&1 || echo "Name is available"
  ```

- **For FIFO queues, confirm the name ends in `.fifo`:** SQS rejects
  create-queue without the suffix. The suffix is permanent.

- **Confirm the DLQ exists and is the correct type:**
  ```bash
  aws sqs get-queue-url --queue-name <dlq-name>
  aws sqs get-queue-attributes --queue-url <dlq-url> \
    --attribute-names FifoQueue --query 'Attributes.FifoQueue' --output text
  ```
  If the source is FIFO, the DLQ's `FifoQueue` must be `true`.

- **For SSE-KMS, confirm the KMS key exists and the policy is correct:**
  ```bash
  aws kms describe-key --key-id alias/my-sqs-key
  aws kms get-key-policy --key-id alias/my-sqs-key --policy-name default
  ```
  The key policy must grant `sqs.<region>.amazonaws.com` permission to use
  the key. Producer/consumer roles need `kms:Decrypt` +
  `kms:GenerateDataKey*`.

- **Capture existing configuration for rollback (if updating an existing queue):**
  ```bash
  aws sqs get-queue-attributes --queue-url <url> \
    --attribute-names All --output json > /tmp/<queue>-backup-$(date +%s).json
  ```
  Queue attributes are not versioned — there is no undo without a backup.

- **Confirm the caller has the required IAM permissions:**
  `sqs:CreateQueue`, `sqs:SetQueueAttributes`, `sqs:GetQueueAttributes`,
  `sqs:GetQueueUrl`. For SSE-KMS: `kms:ListAliases`, `kms:DescribeKey`.

## Edge-case handling

- **Cross-account queue access.** The queue policy must grant the foreign
  account `sqs:SendMessage` (producer) or `sqs:ReceiveMessage` (consumer).
  For SSE-KMS queues, the KMS key policy must ALSO grant the foreign account
  `kms:Decrypt` + `kms:GenerateDataKey*`. Without both, cross-account
  access silently fails with `KMSAccessDeniedException`.

- **S3 Event Notification to SQS.** S3 sends notifications directly to SQS
  via the queue policy. The policy uses `Principal: "*"` +
  `Condition: aws:SourceArn: <bucket-arn>`. This is the standard, safe
  pattern. Do NOT replace with a named principal — S3 does not have a
  per-bucket service principal.

- **SNS subscription to SQS.** Same pattern as S3: `Principal: "*"` +
  `Condition: aws:SourceArn: <topic-arn>`. For FIFO queues, the SNS topic
  must also be FIFO.

- **Lambda event source mapping visibility timeout.** The
  `VisibilityTimeout` on the event source mapping OVERRIDES the queue-level
  value. If they differ, the mapping value applies. Always check both.

- **FIFO queue with no messages.** FIFO queues still charge the minimum
  monthly fee ($0.50/regional API call tier). A FIFO queue with zero
  messages still costs money — delete unused FIFO queues.

- **Redrive from DLQ back to FIFO source.** `StartMessageMoveTask` from a
  FIFO DLQ back to a FIFO source preserves the original `MessageGroupId`.
  Deduplication applies — if the original `DeduplicationId` is still within
  the 5-minute window, the redriven message is silently dropped.

- **Queue policy size limit is 64 KiB.** Large policies with many statements
  can hit this cap. Use IAM identity-based policies for same-account access
  instead of growing the resource-based policy.

## Output format — MANDATORY literal labels

When invoked with a queue deployment request, your ENTIRE response MUST be
the checklist block below. The labels are **case-sensitive all-caps
keywords** — write them EXACTLY as shown. Do NOT substitute `Verdict`,
`**VERDICT**`, `### Verdict`, or any markdown variant. Do NOT write a
preamble ("Here is your deployment checklist..."). Start with `QUEUE:` and
stop after the `VERIFICATION_COMMANDS:` block.

```text
QUEUE: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Queue type — Standard (at-least-once, unlimited TPS)
  [✓]      Dead-letter queue — order-events-dlq (Standard, 14-day retention)
  [✓]      Redrive policy — maxReceiveCount=5
  [✓]      Visibility timeout — 60s (>= consumer p99)
  [✓]      Message retention — 4 days (345600s)
  [✓]      Long polling — ReceiveMessageWaitTimeSeconds=20
  [✓]      Encryption — SSE-SQS (SqsManagedSseEnabled=true)
  [OPTIONAL] Access policy — S3 notification pattern (Principal:* + aws:SourceArn)
  [OPTIONAL] FIFO dedup — N/A (Standard queue)
  [OPTIONAL] High-throughput FIFO — N/A (Standard queue)
  [OPTIONAL] Lambda partial batch responses — ReportBatchItemFailures
VERIFICATION_COMMANDS:
  aws sqs get-queue-attributes --queue-url <url> --attribute-names All
  aws sqs get-queue-attributes --queue-url <url> --attribute-names RedrivePolicy
  aws sqs get-queue-attributes --queue-url <url> --attribute-names SqsManagedSseEnabled
  aws sqs send-message --queue-url <url> --message-body '{"test": true}'
  aws sqs receive-message --queue-url <url> --wait-time-seconds 5
```

**Status marker semantics:**
- `[✓]` — configuration is applied and verified.
- `[✗]` — configuration is NOT applied or is misconfigured. Cite the gap.
- `[OPTIONAL]` — recommended but not required for the workload type.
- `[INPUT NEEDED]` — a prerequisite value is missing (DLQ ARN, KMS key ARN)
  and the operator must provide it before deployment can proceed.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite is missing
(DLQ for production, correct DLQ type, KMS key for SSE-KMS), the verdict is
`PREREQUISITES_MISSING` with each gap listed. The checklist shows the target
configuration with `[INPUT NEEDED]` or `[✗]` for unmet prerequisites.

**Worked example (copy the shape exactly):**

```text
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
  [OPTIONAL] FIFO dedup — N/A (Standard queue)
  [OPTIONAL] High-throughput FIFO — N/A (Standard queue)
  [✓]      Lambda partial batch responses — ReportBatchItemFailures
VERIFICATION_COMMANDS:
  aws sqs get-queue-attributes --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/order-events --attribute-names All
  aws sqs get-queue-attributes --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/order-events --attribute-names RedrivePolicy
  aws sqs get-queue-attributes --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/order-events --attribute-names SqsManagedSseEnabled
  aws sqs send-message --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/order-events --message-body '{"test": true}'
  aws sqs receive-message --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/order-events --wait-time-seconds 5
```

## Error-handling branches

| Error | Cause | Fix |
|---|---|---|
| `InvalidParameterValueException: FIFO queue name must end with .fifo` | FIFO queue created without `.fifo` suffix | Rename the queue with `.fifo` suffix |
| `InvalidParameterValueException: Dead-letter queue does not exist` | Redrive policy references a non-existent DLQ ARN | Create the DLQ first, then set the redrive policy |
| `KMSAccessDeniedException` | Producer/consumer role lacks `kms:Decrypt` on the SSE-KMS key | Add `kms:Decrypt` + `kms:GenerateDataKey*` to the role |
| `OverLimit: Maximum number of queues reached` | Account has 500,000+ queues in the region | Delete unused queues or request a quota increase |
| `QueueDeletedRecently: Must wait 60 seconds before re-creating` | Queue was deleted within the last 60 seconds | Wait 60 seconds, then recreate |
| Messages stuck in queue, not moving to DLQ | maxReceiveCount too high, or consumer is deleting and re-receiving | Check `ApproximateNumberOfMessagesReceived` vs `ApproximateNumberOfMessagesDeleted` |
| Duplicate processing despite FIFO | VisibilityTimeout too short (message returns before processing completes) | Increase VisibilityTimeout to >= p99 processing time |
| FIFO throughput throttle (429) | Exceeding 300 TPS (standard FIFO) or 1500 TPS (high-throughput) | Enable high-throughput FIFO or use more message groups |

## References

- `references/queue-configuration-guide.md` — deep reference on queue type
  internals, FIFO message-group ordering, deduplication hash mechanics,
  visibility timeout interaction with Lambda, and high-throughput FIFO
  configuration details.

- `references/deployment-cli-commands.md` — full copy-pasteable CLI command
  sequence for all 10 deployment steps, including DLQ creation, redrive
  policy, SSE-SQS/SSE-KMS, access policies, FIFO dedup, high-throughput FIFO,
  Lambda partial batch responses, and Terraform `aws_sqs_queue` resource
  equivalents.

## Section taxonomy (CloudOps deployer pattern)

1. **Frontmatter** — name, description, version, when-to-use.
2. **Quick navigation** — table of contents for the skill body.
3. **Activation keywords** — discoverability terms.
4. **Invocation contract** — the mandatory output format.
5. **Reasoning framework** — the *why* behind the deployment order.
6. **Prerequisites** — what must be verified before deployment.
7. **Deployment procedure** — the ordered 10-step deployment sequence.
8. **Latest SQS features** — 2024-2026 feature changes.
9. **Workload-specific deployment matrix** — per-workload configuration.
10. **NEVER** — anti-patterns with explicit *why* each is wrong.
11. **Pre-flight safety checks** — non-destructive deployment guards.
12. **Output format** — the fixed checklist report shape.
13. **Error-handling branches** — common deployment errors and fixes.
14. **References** — pointer to deeper references.

## Domain

AWS CloudOps / App Integration — SQS Messaging Provisioning.

## AWS documentation

- **Amazon SQS Developer Guide** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/welcome.html
- **SQS Configuration** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-configure-set-up.html
- **SQS Dead-Letter Queues** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html
- **SQS Encryption** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-server-side-encryption.html
- **SQS FIFO Queues** — https://docs.aws.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/FIFO-queues.html
- **SQS High-Throughput FIFO** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/high-throughput-fifo.html
- **SQS CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/sqs/
- **Lambda Event Source Mapping (SQS)** — https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html
- **SQS Partial Batch Responses** — https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html#services-sqs-batchfailurereporting
