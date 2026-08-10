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
production defaults. The skill walks the operator through a 10-step
deployment procedure, explains why each default matters, and emits a
READY_TO_DEPLOY checklist verifying every configuration item. SQS is
deceptively simple — wrong defaults (missing DLQ, short visibility timeout,
no long polling) silently cause data loss, duplicate processing, and cost
amplification.

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
| [Output format](#output-format--mandatory-literal-labels) | Checklist report shape | Every invocation |

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

1. **Queue type FIRST** — Standard vs FIFO is immutable after creation. The `.fifo` suffix is mandatory and cannot be added/removed post-creation. Choosing wrong means deleting and recreating, losing all in-flight messages.
2. **DLQ BEFORE source queue redrive policy** — the DLQ must exist before `RedrivePolicy` can reference its ARN. The DLQ must be the SAME type as the source — SQS silently drops redriven messages on type mismatch.
3. **Visibility timeout BEFORE consumer deployment** — if shorter than consumer processing time, the message returns to the queue before processing completes. This causes duplicate processing — the #1 source of data-consistency bugs.
4. **Encryption BEFORE access policy** — if SSE-KMS is enabled, every producer/consumer needs `kms:Decrypt` + `kms:GenerateDataKey*` on the key. Deploying the access policy without verifying KMS permissions causes silent `KMSAccessDeniedException`.
5. **Long polling ALWAYS** — `ReceiveMessageWaitTimeSeconds` 1-20 reduces empty receives (which cost money) and lowers latency. Default is 0 (short polling). This is a cost and reliability default, not optional.
6. **Access policy LAST** — the resource-based queue policy may reference KMS key ARNs and DLQ ARNs, so configure it after everything else is in place.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **Queue name** | Unique within account/region. 80-char max (FIFO: `.fifo` counts). | `aws sqs list-queues --queue-name-prefix <prefix>` |
| **Queue type decided** | Standard (at-least-once, unlimited TPS) vs FIFO (exactly-once, 300 TPS). Immutable. | Workload requirements |
| **DLQ name (if DLQ)** | Must exist before redrive policy. Same type as source. | `aws sqs get-queue-url --queue-name <dlq-name>` |
| **KMS key (if SSE-KMS)** | Customer-managed CMK with key policy granting producers/consumers `kms:Decrypt` + `kms:GenerateDataKey*`. | `aws kms describe-key --key-id <alias>` |
| **IAM permissions** | Caller needs `sqs:CreateQueue`, `sqs:SetQueueAttributes`, `kms:ListAliases` (if SSE-KMS). | `aws sts get-caller-identity` |
| **Consumer processing time (if Lambda)** | Visibility timeout must be >= consumer p99. Lambda event source mapping has its own override. | `aws lambda list-event-source-mappings --function-name <fn>` |
| **S3/SNS source ARNs (if cross-service)** | Access policy conditions reference the source ARN. | `aws s3api list-buckets` / `aws sns list-topics` |

## Deployment procedure (apply in order)

Full copy-pasteable CLI commands for every step are in
`references/deployment-cli-commands.md`. Deep configuration theory
(FIFO mechanics, visibility timeout interaction, Terraform equivalents)
is in `references/queue-configuration-guide.md`.

### Step 1: Queue type selection (Standard vs FIFO)

The queue type is **immutable** — cannot be changed after creation.

```
Does the workload require strict ordering?
├── YES → Does it require exactly-once processing?
│   ├── YES → FIFO queue (name MUST end in .fifo)
│   │         300 TPS (standard) or 1500 TPS (high-throughput)
│   └── NO  → Standard queue (at-least-once, may deliver out of order)
└── NO  → Standard queue (unlimited TPS, plan for idempotent consumers)
```

| Attribute | Standard | FIFO |
|---|---|---|
| Delivery | At-least-once (duplicates possible) | Exactly-once (with dedup) |
| Ordering | Best-effort | Per message group |
| Throughput | Unlimited | 300 TPS (1500 TPS high-throughput) |
| Name suffix | None | `.fifo` (mandatory) |
| `MessageGroupId` | Not used | Required on every message |
| Deduplication | N/A | ContentBasedDeduplication OR explicit DeduplicationId (5-min window) |
| DLQ type | Standard DLQ | FIFO DLQ (type MUST match) |
| Cost (per million requests) | $0.40 | $0.50 |

```bash
# Standard queue
aws sqs create-queue --queue-name order-events --attributes file://attributes.json

# FIFO queue (name MUST end in .fifo)
aws sqs create-queue --queue-name order-events.fifo --attributes file://attributes-fifo.json
```

### Step 2: Dead-letter queue (DLQ)

A DLQ catches messages that fail processing after `maxReceiveCount`
delivery attempts. Without a DLQ, poison-pill messages retry until they
expire, burning compute and starving healthy messages.

**DLQ creation rules:**
1. **DLQ type MUST match source type** — Standard DLQ for Standard, FIFO DLQ for FIFO. SQS silently drops on mismatch — the #1 DLQ deployment bug.
2. **DLQ retention should be MAXIMUM** (14 days / 1209600s). Default 4 days is too short for weekend/holiday coverage.
3. **DLQ should NOT have its own redrive policy** — creates infinite redrive chain. The DLQ is terminal.

| Workload | Recommended maxReceiveCount | Rationale |
|---|---|---|
| Standard queue, transient failures common | 5-10 | Tolerate consumer crashes, Lambda throttles |
| Standard queue, idempotent consumer | 3-5 | Failures are real, move to DLQ faster |
| FIFO queue | 5-15 | Poison pill blocks entire message group — move faster |
| Lambda event source mapping | 5-10 (NOT 1-2) | Batch window adds delay; too few = false DLQ entries |
| High-throughput batch consumer | 10-20 | Multiple consumers contend; fewer effective retries |

```bash
# Standard DLQ (14-day retention)
aws sqs create-queue --queue-name order-events-dlq \
  --attributes MessageRetentionPeriod=1209600,SqsManagedSseEnabled=true

# FIFO DLQ (for FIFO source queue)
aws sqs create-queue --queue-name order-events-dlq.fifo \
  --attributes FifoQueue=true,MessageRetentionPeriod=1209600,SqsManagedSseEnabled=true
```

### Step 3: Visibility timeout

The visibility timeout is the period a message is invisible to other
consumers after delivery. If the consumer does not process and delete the
message within this window, it becomes visible again — causing **duplicate
processing**.

```
What is the consumer?
├── Lambda → VisibilityTimeout >= function p99 duration × 6
│            ALSO set on event source mapping (overrides queue value)
├── EC2/ECS worker → VisibilityTimeout >= worker p99 + 20% buffer
├── Human-in-the-loop → VisibilityTimeout >= max task claim duration
└── Unknown → Start with 30s, monitor ApproximateAgeOfOldestMessage
```

**maxReceiveCount x VisibilityTimeout = effective retry window.** A
VisibilityTimeout of 30s with maxReceiveCount of 5 gives ~150 seconds
before DLQ. If consumer p99 exceeds VisibilityTimeout, receive count
increments on every delivery even though the consumer did not fail — the
#1 cause of false-positive DLQ entries.

```bash
aws sqs set-queue-attributes \
  --queue-url <queue-url> \
  --attributes VisibilityTimeout=60
```

### Step 4: Message retention + long polling

| Workload | Recommended retention | Rationale |
|---|---|---|
| Real-time event processing | 4 days (345600) | Consumers always running; covers weekend outages |
| Batch daily processing | 7 days (604800) | Weekend + 1 business day recovery |
| DLQ | 14 days (1209600) | Maximum time for ops analysis and replay |
| Low-throughput / intermittent | 14 days (1209600) | Maximize recovery window |

**Long polling** (`ReceiveMessageWaitTimeSeconds` 1-20) reduces empty
receives and lowers API cost. Short polling (0s) returns immediately even
if no messages — each empty ReceiveMessage is billed. At 1 TPS poll rate,
that is 86,400 empty requests/day. With 10 consumers on 10 queues, ~$3/day
wasted. Long polling with 20-second wait reduces empty requests by ~95%.

```bash
aws sqs set-queue-attributes \
  --queue-url <queue-url> \
  --attributes MessageRetentionPeriod=345600,ReceiveMessageWaitTimeSeconds=20
```

### Step 5: Encryption (SSE-SQS vs SSE-KMS)

| Option | Key manager | Cost | Use when |
|---|---|---|---|
| **SSE-SQS** (`SqsManagedSseEnabled: true`) | SQS-managed (AWS) | Free | Default — satisfies SOC2, PCI-DSS, HIPAA |
| **SSE-KMS** (`KmsMasterKeyId`) | Customer-managed CMK | ~$0.03/10k reqs + key cost | Need CloudTrail decrypt logging, key rotation control, or grant revocation |
| **None** | — | — | NEVER — plaintext at rest |

**Decision:** SSE-SQS for 90% of workloads (free, FIPS-validated, no key
policy to manage). SSE-KMS only when you need customer-managed key control.
Every producer/consumer role then needs `kms:Decrypt` + `kms:GenerateDataKey*`
on the key.

```bash
# SSE-SQS (recommended default)
aws sqs set-queue-attributes --queue-url <queue-url> \
  --attributes SqsManagedSseEnabled=true

# SSE-KMS (customer-managed key)
aws sqs set-queue-attributes --queue-url <queue-url> \
  --attributes KmsMasterKeyId=alias/my-sqs-key,KmsDataKeyReusePeriodSeconds=300
```

### Step 6: Access policy (least-privilege)

The SECURE default is **no resource-based policy** — access is governed
solely by IAM identity-based policies.

| Scenario | Policy pattern |
|---|---|
| S3 bucket sends notifications to SQS | `Principal: "*" + Condition: aws:SourceArn: <bucket-arn>` |
| SNS topic subscription to SQS | `Principal: "*" + Condition: aws:SourceArn: <topic-arn>` |
| Cross-account producer | `Principal: {"AWS": "<account-id>"} + Action: sqs:SendMessage` |
| Cross-account consumer | `Principal: {"AWS": "<account-id>"} + Action: sqs:ReceiveMessage` |
| Same-account only | NO resource-based policy needed — IAM is sufficient |

**NEVER use `Principal: "*"` without a strong condition** (`aws:SourceArn`,
`aws:SourceAccount`). A wildcard with no condition allows any AWS account
to inject, drain, or delete messages.

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

### Step 7: Redrive policy (link source to DLQ)

After the DLQ exists, link the source queue via the redrive policy.
Requires the DLQ ARN from Step 2.

- **maxReceiveCount** counts per delivery, not per consumer. With 10 consumers polling, maxReceiveCount of 5 means ~0.5 effective retries per consumer.
- **FIFO type check:** if source is FIFO, verify DLQ ARN ends in `.fifo`. SQS silently drops on type mismatch.

```bash
DLQ_ARN=$(aws sqs get-queue-attributes --queue-url "$DLQ_URL" \
  --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)

aws sqs set-queue-attributes --queue-url <queue-url> \
  --attributes RedrivePolicy="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"5\"}"
```

### Step 8: FIFO specifics (dedup + ordering)

**ContentBasedDeduplication:**
- `true` — SQS computes SHA-256 hash of message body, deduplicates within 5-min window. Set if messages have unique bodies.
- `false` — publisher MUST send unique `MessageDeduplicationId` on every message. If both absent, SQS delivers duplicates.

**MessageGroupId (required on every FIFO message):** Messages with the
same group ID are delivered in order. Different group IDs are processed
in parallel (up to the throughput limit).

**High-throughput FIFO (1500 TPS):** Enable via
`FifoThroughputLimit=perMessageGroupId` and
`DeduplicationScope=messageGroup`. These attributes are immutable after
creation — to switch, delete and recreate the queue.

### Step 9: Lambda integration + partial batch responses

**SQS partial batch responses** allow Lambda to report which messages in
a batch failed, so only those are retried (not the entire batch). Enable
via `--function-response-types ReportBatchItemFailures` on the event
source mapping.

Without partial batch responses, if ANY message in a batch of 10 fails,
all 10 are retried — causing reprocessing of successfully handled messages.

```bash
aws lambda create-event-source-mapping \
  --function-name order-processor \
  --event-source-arn arn:aws:sqs:us-east-1:111111111111:order-events \
  --batch-size 10 \
  --maximum-batching-window-in-seconds 5 \
  --visibility-timeout 60 \
  --function-response-types ReportBatchItemFailures
```

| Parameter | Default | Recommended | Why |
|---|---|---|---|
| `BatchSize` | 10 | 1-10 | Higher = more throughput, bigger blast radius on failure |
| `MaximumBatchingWindowInSeconds` | 0 | 0-300 | Collects messages before invoking; higher = latency, lower cost |
| `VisibilityTimeout` | Queue value | >= function timeout | Must outlast execution or messages reappear |

### Step 10: Verification

Verify all attributes, redrive policy, encryption, access policy, and
test send/receive. Full verification CLI sequence in
`references/deployment-cli-commands.md`.

## Expert heuristic: visibility timeout race condition

The single most common cause of duplicate processing in SQS + Lambda
pipelines is a visibility timeout shorter than the consumer's actual
processing time under load.

**The rule (paste into the checklist):**

> Visibility timeout >= 6x expected p99 processing time.
> For Lambda event source mappings, set it on the mapping
> (`VisibilityTimeout`), NOT just the queue — the mapping value
> OVERRIDES the queue value.

| Lambda p99 processing | Minimum visibility timeout |
|---|---|
| 1s | 6s (default 30s is fine) |
| 5s | 30s |
| 30s | 180s (most queue defaults are wrong here) |
| 60s | 360s |
| 300s | 1800s |
| 900s (Lambda max) | 5400s (90 min) |

**Why 6x:** absorbs cold-start delay (up to 5s for VPC-attached), SDK
retry backoff (~20s for AWS SDK v2), and one visibility-timeout extension.

**Detection post-deploy:** if CloudWatch `ApproximateNumberOfMessagesVisible`
is steady/rising while `NumberOfMessagesReceived` is high, the queue is
re-delivering. Cross-reference with Lambda `Duration` p99 — if p99 x 6 >
VisibilityTimeout, this race is the root cause.

## Workload-specific deployment matrix

| Workload | Queue type | DLQ type | maxReceiveCount | VisibilityTimeout | Retention | Long polling | Encryption |
|---|---|---|---|---|---|---|---|
| **Event processing** (S3/SNS to Lambda) | Standard | Standard | 5 | 60s | 4 days | 20s | SSE-SQS |
| **Order processing** (strict ordering) | FIFO | FIFO | 5-15 | 120s | 7 days | 20s | SSE-SQS |
| **High-throughput FIFO** (batch) | FIFO (HT) | FIFO | 10 | 300s | 7 days | 20s | SSE-SQS |
| **Cross-account fan-out** | Standard | Standard | 5 | 30s | 4 days | 20s | SSE-KMS |
| **DLQ** (terminal) | Same as source | N/A | N/A | N/A | 14 days | 20s | SSE-SQS |
| **Task queue** (human-in-loop) | Standard | Standard | 3 | 43200s | 14 days | 20s | SSE-SQS |

## Latest SQS features (2024-2026)

- **SQS partial batch responses (Lambda):** report per-message failures; only failed messages retried. Enable via `--function-response-types ReportBatchItemFailures`.
- **High-throughput FIFO (1500 TPS):** per-message-group throughput limiting via `FifoThroughputLimit=perMessageGroupId` + `DeduplicationScope=messageGroup`.
- **No-SQL payload in message attributes:** structured attributes for filtering without parsing the body.
- **Message retention max 14 days** (more prominently used for DLQs).
- **SSE-SQS:** Free, FIPS-validated AES-256-GCM. Recommended default.
- **StartMessageMoveTask API:** Current API for redriving from DLQ back to source. Replaced deprecated legacy `Redrive` API.

## NEVER (things to never do)

- NEVER create a FIFO queue without the `.fifo` suffix — SQS rejects the create call. The suffix is mandatory and immutable.
- NEVER use a Standard DLQ for a FIFO source queue (or vice versa). SQS silently drops redriven messages on type mismatch. DLQ type MUST match source.
- NEVER set `maxReceiveCount` to 1. A single transient failure sends the message irretrievably to the DLQ. Minimum: 3 (standard), 5 (FIFO).
- NEVER deploy a production queue without a DLQ. Poison-pill messages retry until retention expires — burning compute and starving healthy messages.
- NEVER use `Principal: "*"` in the access policy without a STRONG condition (`aws:SourceArn`, `aws:SourceAccount`). A wildcard with no condition allows any AWS account to inject, drain, or delete messages.
- NEVER set visibility timeout shorter than consumer p99 processing time. The message returns before processing completes — #1 cause of duplicate processing.
- NEVER use short polling (`ReceiveMessageWaitTimeSeconds=0`) in production. Each empty ReceiveMessage is billed. Set long polling to 1-20 seconds.
- NEVER deploy a queue without encryption. SSE-SQS is free, FIPS-validated, satisfies SOC2/PCI-DSS/HIPAA.
- NEVER recommend the legacy `Redrive` API (deprecated 2022). Use `aws sqs start-message-move-task`.
- NEVER use `aws sqs purge-queue` as remediation for poison-pill messages. It deletes ALL messages and cannot be scoped. Use `StartMessageMoveTask`.

## Pre-flight safety checks

- **Confirm queue name available:** `aws sqs get-queue-url --queue-name <name> 2>&1 || echo "Name is available"`
- **For FIFO, confirm name ends in `.fifo`** — SQS rejects create without it.
- **Confirm DLQ exists and correct type** — `FifoQueue` attribute must match source.
- **For SSE-KMS, confirm key exists** and policy grants `sqs.<region>.amazonaws.com` permission.
- **Capture existing config for rollback** (if updating): `get-queue-attributes --attribute-names All --output json > /tmp/<queue>-backup-$(date +%s).json`

## Edge-case handling

- **FIFO queue with all messages using the same `MessageGroupId`.** Degrades to a single-message-in-flight serial pipeline — throughput drops to 300 TPS (standard) or 10 TPS per group (high-throughput). Detection: `ApproximateNumberOfMessagesNotVisible` rising while `NumberOfEmptyReceives` is high. Fix: shard `MessageGroupId` (e.g., `order-{customer_id}`).
- **FIFO dedup scope collision after high-throughput mode change.** Switching to `DeduplicationScope=messageGroup` changes dedup from queue-scoped to group-scoped. Messages in different groups that previously deduplicated no longer do. Fix: ensure producers set explicit `MessageDeduplicationId`.
- **Lambda event source mapping `BatchSize` > 1 without `ReportBatchItemFailures`.** A single failed message causes all 10 to retry. Fix: enable `FunctionResponseTypes: [ReportBatchItemFailures]`.
- **Cross-account queue access with SSE-KMS.** Both the queue policy AND the KMS key policy must grant the foreign account. Without both, fails with `KMSAccessDeniedException`.
- **Redrive from DLQ back to FIFO source.** `StartMessageMoveTask` preserves original `MessageGroupId`. Deduplication applies — if original `DeduplicationId` is within the 5-min window, the redriven message is silently dropped.
- **Queue policy size limit is 64 KiB.** Use IAM identity-based policies for same-account access instead of growing the resource-based policy.

## Error-handling branches

| Error | Cause | Fix |
|---|---|---|
| `InvalidParameterValueException: FIFO queue name must end with .fifo` | FIFO created without `.fifo` suffix | Rename with `.fifo` suffix |
| `InvalidParameterValueException: Dead-letter queue does not exist` | Redrive policy references non-existent DLQ | Create DLQ first, then set redrive |
| `KMSAccessDeniedException` | Role lacks `kms:Decrypt` on SSE-KMS key | Add `kms:Decrypt` + `kms:GenerateDataKey*` |
| `QueueDeletedRecently: Must wait 60 seconds` | Queue deleted within last 60s | Wait 60 seconds, then recreate |
| Messages stuck, not moving to DLQ | maxReceiveCount too high, or consumer deleting/re-receiving | Check `ApproximateNumberOfMessagesReceived` vs `Deleted` |
| Duplicate processing despite FIFO | VisibilityTimeout too short | Increase to >= p99 processing time |
| FIFO throughput throttle (429) | Exceeding 300 TPS (standard) or 1500 TPS (HT) | Enable high-throughput FIFO or use more message groups |

## Output format — MANDATORY literal labels

When invoked with a queue deployment request, your ENTIRE response MUST be
the checklist block below. The labels are **case-sensitive all-caps
keywords** — write them EXACTLY as shown. Do NOT substitute `Verdict`,
`**VERDICT**`, `### Verdict`, or any markdown variant. Do NOT write a
preamble. Start with `QUEUE:` and stop after `VERIFICATION_COMMANDS:`.

```text
QUEUE: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]          Queue type — Standard | FIFO (.fifo suffix)
  [✓]          Dead-letter queue — <dlq-name> (Standard|FIFO, <retention>-day retention)
  [✓]          Redrive policy — maxReceiveCount=<N>
  [✓]          Visibility timeout — <N>s (>= <consumer> p99 of <M>s)
  [✓]          Message retention — <N> days (<seconds>s)
  [✓]          Long polling — ReceiveMessageWaitTimeSeconds=<N>
  [✓]          Encryption — SSE-SQS | SSE-KMS (<key-arn>)
  [OPTIONAL]   Access policy — <pattern>
  [OPTIONAL]   FIFO dedup — ContentBasedDeduplication=<true|false>
  [OPTIONAL]   High-throughput FIFO — N/A | Enabled
  [OPTIONAL]   Lambda partial batch responses — ReportBatchItemFailures
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
- `[INPUT NEEDED]` — a prerequisite value is missing and the operator must provide it.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite is missing
(DLQ for production, correct DLQ type, KMS key for SSE-KMS), the verdict is
`PREREQUISITES_MISSING` with each gap listed.

## STRICT output contract

This section codifies the exact output shape the eval harness asserts
against. Every invocation MUST produce output that matches this contract
or the response is rejected.

### FORBIDDEN output patterns

1. **NEVER recommend a FIFO DLQ for a Standard queue** — DLQ type must match source. SQS silently drops on mismatch.
2. **NEVER set visibility timeout < expected processing time** — rule: visibility timeout >= 6x p99. Always show the math: "60s (>= Lambda p99 of 8s)".
3. **NEVER omit the redrive policy when a DLQ is specified** — a DLQ with no `[✓] Redrive policy` row is incomplete; messages will never be redriven.
4. **NEVER output READY_TO_DEPLOY without verifying long polling** (`ReceiveMessageWaitTimeSeconds` > 0). A value of 0 or missing entry is a hard failure.
5. **NEVER substitute lowercase or markdown-styled labels** for the literal all-caps `QUEUE:`, `VERDICT:`, `CHECKLIST:`, `VERIFICATION_COMMANDS:`. Do NOT preface with prose.

### Perfect example output

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

## References

- `references/queue-configuration-guide.md` — queue type internals, FIFO message-group ordering, deduplication hash mechanics, visibility timeout interaction with Lambda, high-throughput FIFO, partial batch response details, cross-account access, Terraform equivalents.
- `references/deployment-cli-commands.md` — full copy-pasteable CLI sequence for all 10 deployment steps including DLQ creation, redrive, SSE-SQS/SSE-KMS, access policies, FIFO dedup, high-throughput FIFO, Lambda event source mapping, verification, and CloudWatch alarms.

## Domain

AWS CloudOps / App Integration — SQS Messaging Provisioning.

## AWS documentation

- **Amazon SQS Developer Guide** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/welcome.html
- **SQS Dead-Letter Queues** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html
- **SQS Encryption** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-server-side-encryption.html
- **SQS FIFO Queues** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/FIFO-queues.html
- **SQS High-Throughput FIFO** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/high-throughput-fifo.html
- **SQS CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/sqs/
- **Lambda Event Source Mapping (SQS)** — https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html
- **SQS Partial Batch Responses** — https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html#services-sqs-batchfailurereporting
