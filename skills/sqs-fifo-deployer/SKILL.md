---
name: sqs-fifo-deployer
description: >-
  Provisions Amazon SQS FIFO queues with production defaults: FIFO
  queue attributes (FifoQueue=true, ContentBasedDeduplication,
  DeduplicationScope, ThroughputLimit mode), message group ID for
  ordering, deduplication (content-based vs explicit), high-throughput
  FIFO mode, DLQ for FIFO, visibility timeout tuning, SSE-KMS
  encryption, access policy, redrive policy, and cross-account
  delivery. Emits a READY_TO_DEPLOY checklist with verification
  commands. Use when creating an SQS FIFO queue, setting up message
  group ordering, configuring deduplication, enabling high-throughput
  FIFO, attaching a DLQ, tuning visibility timeout, or configuring
  cross-account delivery. Triggers: create sqs fifo queue, fifo queue
  deduplication, sqs message group id, high throughput fifo, sqs dlq
  redrive, sqs visibility timeout, sqs sse kms, sqs fifo cross
  account.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with sqs access.
  Works with Terraform aws_sqs_queue resources and CloudFormation
  AWS::SQS::Queue templates.
keywords:
  - aws
  - sqs
  - fifo
  - message queue
  - cloudops
  - deploy
  - provisioning
  - deduplication
  - message group
  - high throughput
  - dlq
  - redrive
  - visibility timeout
  - sse kms
  - cross account
tags:
  - aws
  - sqs
  - fifo
  - message-queue
  - cloudops
  - deploy
  - provisioning
  - deduplication
  - message-group
  - high-throughput
  - dlq
  - redrive
  - visibility-timeout
  - sse-kms
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
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
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - sqs
    - fifo
    - message-queue
    - cloudops
    - deploy
    - provisioning
    - deduplication
    - message-group
    - high-throughput
    - dlq
    - redrive
    - visibility-timeout
    - sse-kms
  dependencies:
    - aws-orchestrator
  keywords:
    - create sqs fifo queue
    - fifo queue deduplication
    - sqs message group id
    - high throughput fifo
    - sqs dlq redrive
    - sqs visibility timeout
    - sqs sse kms
    - sqs fifo cross account
  when_to_use: >-
    Invoke when the user wants to create an SQS FIFO queue, configure
    message group ID ordering, set up content-based or explicit
    deduplication, enable high-throughput FIFO mode, attach a dead-
    letter queue (DLQ), tune visibility timeout, configure SSE-KMS
    encryption, set up access policies, configure redrive policies, or
    enable cross-account delivery to a FIFO queue. Do NOT invoke for
    SQS Standard queues (use standard queue skills), SNS topics, or
    Amazon MQ.
---

# SQS FIFO Deployer

An AWS CloudOps agent skill that provisions Amazon SQS FIFO queues
with correct defaults. The skill walks the operator through FIFO
queue attributes (FifoQueue=true, ContentBasedDeduplication,
DeduplicationScope, ThroughputLimit mode), message group ID for
ordering, deduplication strategies (content-based vs explicit
MessageDeduplicationId), high-throughput FIFO mode, DLQ configuration
for FIFO queues, visibility timeout tuning, SSE-KMS encryption, access
policy, redrive policy, and cross-account delivery. It captures queue
topology and ordering requirements, explains why each default matters,
and emits a READY_TO_DEPLOY checklist with copy-pasteable verification
commands.

## Activation keywords

create SQS FIFO queue, FIFO queue deduplication, SQS message group ID,
high throughput FIFO, SQS DLQ redrive, SQS visibility timeout, SQS SSE
KMS, SQS FIFO cross account.

## STRICT output contract

When this skill is invoked with an SQS FIFO provisioning request
(create a FIFO queue, configure deduplication, set up message group
ordering, enable high-throughput mode, attach a DLQ, configure cross-
account delivery, or a partial configuration), the agent MUST respond
with the READY_TO_DEPLOY checklist defined in the "Output format"
section using the literal all-caps labels `SQS_FIFO:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the
checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-based
evals and downstream provisioning pipelines rely on; deviating from
the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[x]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — FIFO queue attributes | Core FIFO model |
| Step 2 — Message group ID for ordering | Ordering guarantee |
| Step 3 — Deduplication (content-based vs explicit) | Dedup strategy |
| Step 4 — High-throughput FIFO mode | Throughput scaling |
| Step 5 — DLQ for FIFO | Dead-letter handling |
| Step 6 — Visibility timeout tuning | Consumer lifecycle |
| Step 7 — SSE-KMS encryption | Encryption at rest |
| Step 8 — Access policy | Cross-account + producer/consumer |
| Step 9 — Redrive policy | DLQ movement |
| Step 10 — Cross-account delivery | Cross-account producers |
| Step 11 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/deduplication-and-ordering.md | Dedup + ordering detail |
| references/dlq-and-throughput.md | DLQ + throughput detail |

## Mindset

**One-line takeaway:** An SQS FIFO queue guarantees first-in-first-out
ordering within a message group. The message group ID is the
partitioning key — messages with the same group ID are processed in
order; messages with different group IDs are processed in parallel.
Deduplication prevents duplicate messages within the 5-minute
deduplication window, either by content hash (content-based) or by
explicit deduplication ID. High-throughput FIFO mode increases the
queue's throughput by decoupling deduplication from the queue level,
enabling per-message-group deduplication.

Three misconceptions dominate SQS FIFO misdesign at provisioning time:

- **"FIFO queues are just like Standard queues with ordering."** They
  are fundamentally different. FIFO queues require the `.fifo` suffix
  in the queue name. They require FifoQueue=true at creation (immutable
  attribute — a Standard queue CANNOT be converted to FIFO). They
  enforce per-message-group ordering. They have lower throughput than
  Standard queues (3,000 messages/second with batching, or 300 TPS
  per API action) unless high-throughput mode is enabled. They support
  deduplication. Standard queues support none of these.

- **"Message group ID is just a label."** It is the ordering partition.
  Messages within the same group ID are strictly ordered. Messages
  with different group IDs can be processed in parallel, enabling
  throughput scaling. The number of in-flight message groups directly
  determines the achievable parallelism. A single message group ID
  serializes ALL messages through one consumer. Choosing the right
  partitioning key (like a database entity ID) is critical for both
  correctness (ordering) and performance (parallelism).

- **"Deduplication and high-throughput mode are independent."** They
  are coupled. Content-based deduplication hashes the message body to
  generate a deduplication ID. This works at the QUEUE level — all
  messages, regardless of group, share the deduplication window.
  High-throughput FIFO mode (DeduplicationScope=messageGroup,
  ThroughputLimit=messagesPerGroupId) moves deduplication to the
  MESSAGE GROUP level, enabling 300 TPS per API action per message
  group (instead of per queue). Enabling high-throughput mode without
  understanding the deduplication scope change can cause unexpected
  duplicate messages.

## Configuration dependency graph (novel heuristic)

SQS FIFO queue configurations are NOT independent. The queue type
(FIFO) must be set at creation and is immutable. Deduplication scope
interacts with throughput mode. The DLQ must be a FIFO queue (Standard
DLQs cannot be used with FIFO queues). Visibility timeout interacts
  with message processing time. Use this graph to sequence
  provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Queue type (FifoQueue=true) | Queue name ends with `.fifo` | IMMUTABLE after creation — cannot convert Standard to FIFO | ordering, deduplication |
| Content-based deduplication | FifoQueue=true | when enabled, SQS hashes message body for dedup ID; when disabled, producer must send explicit dedup ID | automatic dedup |
| DeduplicationScope | FifoQueue=true; ThroughputLimit must also be set | default is `queue`; changing to `messageGroup` enables per-group dedup | high-throughput mode |
| ThroughputLimit | FifoQueue=true; DeduplicationScope must also be set | default is `perQueue`; changing to `messagesPerGroupId` enables per-group throughput | high-throughput mode |
| High-throughput FIFO | DeduplicationScope=messageGroup + ThroughputLimit=messagesPerGroupId | both attributes must be set together; setting only one is rejected | 300 TPS per group |
| DLQ (redrive policy) | DLQ must be a FIFO queue; DLQ must exist before redrive policy is attached | a Standard DLQ CANNOT be used with a FIFO queue — API rejects | dead-letter handling |
| Visibility timeout | nothing — queue-level attribute | must be >= consumer processing time; too low causes duplicate processing | consumer lifecycle |
| SSE-KMS encryption | KMS key exists (if customer-managed) | encryption is queue-level; all messages encrypted with the key | encryption at rest |
| Access policy | nothing — queue-level attribute | cross-account producers/consumers need explicit Principal in policy | cross-account delivery |
| Redrive policy | DLQ ARN known | deadLetterTargetArn + maxReceiveCount; maxReceiveCount must be > 0 | DLQ movement |
| Cross-account delivery | Access policy on the queue permits sender account | sender account needs sqs:SendMessage permission | cross-account producers |

**The message-group-and-deduplication row is the one a baseline model
misses.** Creating the FIFO queue is necessary but NOT sufficient. The
message group ID determines ordering parallelism. The deduplication
strategy (content-based vs explicit) determines duplicate prevention.
The high-throughput mode requires BOTH DeduplicationScope and
ThroughputLimit to be set together. The procedure below forces an
explicit decision on each.

**Cross-dependency gotchas:**
- The `.fifo` suffix in the queue name is MANDATORY. A queue named
  `my-queue` without `.fifo` cannot have FifoQueue=true.
- The DLQ for a FIFO queue MUST also be a FIFO queue. A Standard DLQ
  is rejected by the API.
- High-throughput mode requires setting BOTH DeduplicationScope and
  ThroughputLimit. Setting only one results in an API error.
- ContentBasedDeduplication=true generates dedup IDs from message body
  hashes. If the producer sends explicit dedup IDs, this attribute is
  ignored for those messages.
- Visibility timeout must be longer than the consumer's processing
  time. If it expires before the consumer deletes the message, the
  message becomes visible again and may be processed twice.

## Expert heuristic: message group ID partitioning for parallelism

A baseline model says "create a FIFO queue." The correct heuristic
recognizes that the message group ID is the parallelism lever.

```text
FIFO queue throughput:
  Standard FIFO queue (perQueue):  3,000 messages/sec with batching
                                    300 transactions/sec per API action
                                    (shared across ALL message groups)

  High-throughput FIFO (perGroupId):
                                    300 TPS per API action PER message group
                                    With N message groups: up to N * 300 TPS
                                    Scales linearly with group count

Message group ID as partitioning key:
  Single group ID (e.g., "all-messages"):
    → ALL messages serialized through one stream
    → Only ONE consumer can process at a time
    → Maximum throughput: 300 TPS (one consumer)
    → Use when: global ordering is required

  Per-entity group ID (e.g., order-123, order-456):
    → Each entity gets its own ordered stream
    → Multiple consumers process different entities in parallel
    → Throughput scales with the number of active groups
    → Use when: per-entity ordering is sufficient (most common)

Key implication: choosing a coarse group ID (e.g., "all") serializes
everything. Choosing a fine-grained group ID (e.g., customer-123)
maximizes parallelism while preserving per-entity ordering.
```

**Key implication:** the #1 cause of "my FIFO queue is slow" is a
single message group ID serializing all messages. Use per-entity
group IDs to scale parallelism.

## Expert heuristic: deduplication ID management

Deduplication prevents duplicate processing within a 5-minute window.
The deduplication strategy determines how dedup IDs are generated.

```text
Deduplication strategies:

1. Content-based (ContentBasedDeduplication=true):
   → SQS generates dedup ID = SHA-256 hash of message body
   → No producer-side dedup ID needed
   → Caveat: two messages with DIFFERENT bodies but SAME logical
     content are NOT deduplicated
   → Use when: message body uniquely identifies the message

2. Explicit (MessageDeduplicationId):
   → Producer sends a dedup ID with each message
   → Producer controls dedup semantics (can use business key,
     event ID, or composite key)
   → Overrides content-based dedup if both are present
   → Use when: message body may vary but logical content is the same
     (e.g., retry with updated timestamp but same order ID)

3. High-throughput mode (DeduplicationScope=messageGroup):
   → Dedup window is per message group, not per queue
   → Same dedup ID in DIFFERENT groups does NOT deduplicate
   → Enables per-group throughput scaling
   → Use when: high throughput is needed AND per-group dedup is
     semantically correct

Dedup window: 5 minutes from first receipt.
  → Same dedup ID within 5 min: SQS accepts the message but does NOT
    enqueue it again (producer gets a success response).
  → Same dedup ID after 5 min: SQS enqueues as a new message.
```

**Key implication:** the deduplication strategy must align with the
business semantics. Content-based dedup fails when the same logical
message has different bodies. Explicit dedup fails when the producer
generates inconsistent dedup IDs. High-throughput mode changes the
dedup scope from queue-level to group-level.

## Expert heuristic: high-throughput FIFO quota caveats

High-throughput FIFO mode removes the per-queue throughput limit but
introduces new constraints that are often missed.

```text
High-throughput FIFO requirements:
  DeduplicationScope = messageGroup
  ThroughputLimit    = messagesPerGroupId

  Both must be set together. Setting only one → API error.

Throughput:
  Up to 300 TPS per API action per message group
  With 10 active groups: up to 3,000 TPS (vs 300 TPS for standard FIFO)
  With 100 active groups: up to 30,000 TPS

Caveats:
  1. Dedup scope change: dedup is now per-group. The same dedup ID
     in two different groups will NOT be deduplicated. If your dedup
     logic assumed queue-level scope, this changes behavior.

  2. Account-level quota: high-throughput FIFO queues count against
     a separate quota. The default is 100 high-throughput FIFO queues
     per account (soft limit). Request a quota increase if needed.

  3. Cost: high-throughput FIFO has a different pricing tier than
     standard FIFO. API requests are billed at a higher rate. Monitor
     costs when switching from standard to high-throughput.

  4. No rollback: once a queue is configured for high-throughput, the
     DeduplicationScope and ThroughputLimit CAN be changed back, but
     in-flight messages may be affected during the transition.

  5. Message group behavior: with high-throughput mode, the number of
     active message groups directly determines throughput. Too few
     groups = low throughput. Too many groups = more overhead.
```

**Key implication:** high-throughput FIFO is NOT a free throughput
upgrade. It changes deduplication semantics, billing, and quota
allocation. Evaluate all three before enabling.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Queue name ends with `.fifo` | Mandatory for FIFO queues | Verify naming convention |
| FIFO vs Standard decision | FIFO type is immutable after creation | Assess ordering requirements |
| Deduplication strategy decided | Content-based vs explicit dedup ID | Assess dedup requirements |
| DLQ is also FIFO (if using DLQ) | Standard DLQ cannot attach to FIFO queue | `aws sqs get-queue-attributes --queue-url <dlq-url> --attribute-names FifoQueue` |
| KMS key ARN (if using SSE-KMS) | Customer-managed key for encryption | `aws kms describe-key --key-id <id>` |
| Consumer processing time (for visibility timeout) | Visibility timeout must exceed processing time | Assess consumer workload |
| Cross-account IDs (if cross-account delivery) | Access policy needs principal account IDs | `aws sts get-caller-identity` |
| IAM permissions for SQS actions | sqs:CreateQueue, SetQueueAttributes, etc. | `aws iam list-attached-role-policies` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — FIFO queue attributes

FIFO queues require specific attributes at creation time. These are
immutable after the queue is created.

```bash
QUEUE_URL=$(aws sqs create-queue \
  --queue-name "order-processing.fifo" \
  --attributes "FifoQueue=true,ContentBasedDeduplication=true,VisibilityTimeout=60,DelaySeconds=0,MessageRetentionPeriod=345600" \
  --query 'QueueUrl' --output text)

echo "Queue URL: $QUEUE_URL"
```

**Key FIFO attributes:**

| Attribute | Default | Description |
|---|---|---|
| FifoQueue | false (must set true) | Enables FIFO ordering — immutable after creation |
| ContentBasedDeduplication | false | Generates dedup ID from message body hash |
| DeduplicationScope | queue | Set to `messageGroup` for high-throughput |
| ThroughputLimit | perQueue | Set to `messagesPerGroupId` for high-throughput |
| VisibilityTimeout | 30 | Seconds before message becomes visible again after receive |
| MessageRetentionPeriod | 345600 (4 days) | How long messages are retained |
| DelaySeconds | 0 | Per-queue delay for message delivery |

**Verify the queue:**

```bash
aws sqs get-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attribute-names "QueueArn,FifoQueue,ContentBasedDeduplication,DeduplicationScope,ThroughputLimit,VisibilityTimeout"
```

## Step 2 — Message group ID for ordering

The message group ID (`MessageGroupId`) is the ordering partition.
Messages with the same group ID are processed in FIFO order.
Messages with different group IDs are processed in parallel.

```bash
# Send messages with different group IDs (parallel processing)
aws sqs send-message \
  --queue-url "$QUEUE_URL" \
  --message-body '{"orderId": "order-001", "status": "created"}' \
  --message-group-id "customer-123"

aws sqs send-message \
  --queue-url "$QUEUE_URL" \
  --message-body '{"orderId": "order-002", "status": "created"}' \
  --message-group-id "customer-456"
```

**Receive messages:**

```bash
aws sqs receive-message \
  --queue-url "$QUEUE_URL" \
  --max-number-of-messages 10 \
  --wait-time-seconds 20
```

**Key:** messages from the same group are returned in order. Messages
from different groups can be received by different consumers in
parallel.

## Step 3 — Deduplication (content-based vs explicit)

### Content-based deduplication

When `ContentBasedDeduplication=true`, SQS generates a deduplication
ID from the SHA-256 hash of the message body.

```bash
# Content-based dedup — same body within 5 min is NOT re-enqueued
aws sqs send-message \
  --queue-url "$QUEUE_URL" \
  --message-body '{"orderId": "order-001"}' \
  --message-group-id "customer-123"

# This second message with the SAME body is silently dropped (within 5 min)
aws sqs send-message \
  --queue-url "$QUEUE_URL" \
  --message-body '{"orderId": "order-001"}' \
  --message-group-id "customer-123"
```

### Explicit deduplication ID

When `ContentBasedDeduplication=false` (or overridden), the producer
sends an explicit `MessageDeduplicationId`.

```bash
# Explicit dedup — producer controls dedup semantics
aws sqs send-message \
  --queue-url "$QUEUE_URL" \
  --message-body '{"orderId": "order-001", "timestamp": "2026-01-01T10:00:00Z"}' \
  --message-group-id "customer-123" \
  --message-deduplication-id "order-001"
```

**Key:** use explicit dedup when the same logical message may have
different bodies (e.g., retries with updated timestamps). Use a stable
business key as the dedup ID.

## Step 4 — High-throughput FIFO mode

High-throughput FIFO mode requires setting BOTH DeduplicationScope and
ThroughputLimit. This enables per-message-group throughput scaling.

```bash
# High-throughput FIFO queue
QUEUE_URL=$(aws sqs create-queue \
  --queue-name "high-throughput-orders.fifo" \
  --attributes "FifoQueue=true,DeduplicationScope=messageGroup,ThroughputLimit=messagesPerGroupId,VisibilityTimeout=60" \
  --query 'QueueUrl' --output text)
```

**Critical:** both `DeduplicationScope=messageGroup` and
`ThroughputLimit=messagesPerGroupId` must be set together. Setting
only one results in an API error.

**Throughput comparison:**

```text
Standard FIFO:        300 TPS per API action (shared across all groups)
High-throughput FIFO:  300 TPS per API action PER message group
                       10 groups = 3,000 TPS
                       100 groups = 30,000 TPS
```

## Step 5 — DLQ for FIFO

The DLQ for a FIFO queue MUST also be a FIFO queue. A Standard queue
cannot serve as a DLQ for a FIFO queue.

```bash
DLQ_URL=$(aws sqs create-queue \
  --queue-name "order-processing-dlq.fifo" \
  --attributes "FifoQueue=true" --query 'QueueUrl' --output text)

DLQ_ARN=$(aws sqs get-queue-attributes --queue-url "$DLQ_URL" \
  --attribute-names "QueueArn" --query 'Attributes.QueueArn' --output text)

aws sqs set-queue-attributes --queue-url "$QUEUE_URL" \
  --attributes "RedrivePolicy={\"deadLetterTargetArn\":\"${DLQ_ARN}\",\"maxReceiveCount\":\"5\"}"
```

**Key:** `maxReceiveCount` determines how many times a message is
received before it is moved to the DLQ. See Step 9 for redrive.

## Step 6 — Visibility timeout tuning

The visibility timeout determines how long a message is invisible to
other consumers after being received. If the consumer does not delete
the message before the timeout expires, the message becomes visible
again and may be processed by another consumer (causing duplicates).

```bash
aws sqs set-queue-attributes --queue-url "$QUEUE_URL" \
  --attributes "VisibilityTimeout=120"
```

**Guidelines:** set the visibility timeout to AT LEAST 2x the expected
processing time. Use `change-message-visibility` for per-message
overrides. See `references/dlq-and-throughput.md` for the full tuning
table.

## Step 7 — SSE-KMS encryption

SSE-KMS encrypts messages at rest using a KMS key (AWS-managed or
customer-managed).

```bash
aws sqs set-queue-attributes --queue-url "$QUEUE_URL" \
  --attributes "KmsMasterKeyId=arn:aws:kms:us-east-1:123456789012:key/abc123,KmsDataKeyReusePeriodSeconds=300"
```

The KMS key policy must allow SQS to `kms:GenerateDataKey` and
`kms:Decrypt`. For cross-account producers, the key policy must also
allow those accounts. See `references/dlq-and-throughput.md` for KMS
key policy examples.

## Step 8 — Access policy

The queue access policy controls who can send and receive messages.
By default, only the queue owner can access the queue. For
cross-account delivery, grant `sqs:SendMessage` to the producer's
account and ensure the producer's IAM role also permits it.

## Step 9 — Redrive policy

The redrive policy defines the DLQ and `maxReceiveCount`. Messages
that exceed `maxReceiveCount` are moved to the DLQ.

```bash
# Redrive from DLQ back to the main queue
aws sqs start-message-move-task \
  --source-arn "$DLQ_ARN" \
  --destination-arn "$MAIN_QUEUE_ARN" --query 'TaskHandle' --output text
```

**Key:** `StartMessageMoveTask` is the modern API for moving messages
from a DLQ back to the source queue. It preserves message attributes.

## Step 10 — Cross-account delivery

Cross-account delivery allows producers in one account to send
messages to a FIFO queue in another account. This requires:

1. The queue access policy grants `sqs:SendMessage` to the producer
   account.
2. The producer's IAM role allows `sqs:SendMessage` to the queue.
3. If SSE-KMS is enabled, the KMS key policy allows the producer
   account.

See `references/dlq-and-throughput.md` for a full cross-account
access policy example with Terraform.

**Key:** for FIFO queues, cross-account messages must include both
`MessageGroupId` and `MessageDeduplicationId` (or the queue must have
`ContentBasedDeduplication=true`).

## Step 11 — Recent features

**Recent AWS features (2023-2026):**

- **High-throughput FIFO mode (2023-2024):** AWS introduced
  DeduplicationScope and ThroughputLimit attributes, enabling per-
  message-group throughput scaling. This removed the per-queue 300 TPS
  bottleneck for FIFO queues.

- **StartMessageMoveTask API (2023-2024):** The modern API for moving
  messages from a DLQ back to the source queue, replacing the custom
  Lambda-based redrive patterns. Preserves message attributes and
  supports partial moves.

- **SSE-KMS for SQS (maturity 2023-2024):** Full SSE-KMS support for
  FIFO queues, including cross-account KMS key usage and
  KmsDataKeyReusePeriodSeconds tuning.

- **FIFO queue visibility timeout per-message (2023-2024):**
  Enhanced ChangeMessageVisibility API for per-message timeout
  adjustments, enabling dynamic timeout based on message processing
  complexity.

- **Terraform provider improvements (2023-2024):** The Terraform
  `aws_sqs_queue` resource now supports DeduplicationScope,
  ThroughputLimit, KmsMasterKeyId, and redrive_policy attributes with
  full lifecycle management.

- **Cross-account DLQ redrive (2024-2025):** AWS enhanced the
  StartMessageMoveTask to support cross-account DLQ redrive, allowing
  DLQs in one account to redrive to source queues in another account
  with proper IAM permissions.

## NEVER do these things

1. **NEVER use a Standard queue as a DLQ for a FIFO queue.** The DLQ
   for a FIFO queue MUST also be a FIFO queue. The API will reject a
   redrive policy pointing to a Standard queue DLQ.

2. **NEVER omit the `.fifo` suffix in the queue name.** FIFO queue
   names MUST end with `.fifo`. The API rejects
   `create-queue --queue-name "my-queue" --attributes "FifoQueue=true"`
   without the suffix.

3. **NEVER use a single message group ID for all messages.** A single
   group ID serializes ALL messages through one consumer, eliminating
   parallelism. Use per-entity group IDs (e.g., customer ID, order ID)
   to scale throughput.

4. **NEVER set DeduplicationScope or ThroughputLimit alone.**
   High-throughput FIFO mode requires BOTH
   `DeduplicationScope=messageGroup` AND
   `ThroughputLimit=messagesPerGroupId`. Setting only one results in
   an API error.

5. **NEVER assume content-based deduplication catches logical
   duplicates.** Content-based dedup hashes the message BODY. Two
   messages with different bodies but the same logical content (e.g.,
   an order retry with a new timestamp) are NOT deduplicated. Use
   explicit `MessageDeduplicationId` for semantic dedup.

6. **NEVER set visibility timeout lower than the consumer processing
   time.** If the timeout expires before the consumer deletes the
   message, the message becomes visible again and may be processed
   twice. Set the timeout to at least 2x the expected processing time.

7. **NEVER assume high-throughput mode is free.** High-throughput FIFO
   has a different pricing tier (higher per-request cost), changes
   deduplication scope from queue-level to group-level, and counts
   against a separate account quota. Evaluate all three before
   enabling.

8. **NEVER forget MessageGroupId when sending to a FIFO queue.** Every
   message sent to a FIFO queue MUST include a `MessageGroupId`.
   Without it, the API rejects the message.

9. **NEVER convert a Standard queue to FIFO or vice versa.** The
   queue type (FifoQueue attribute) is IMMUTABLE after creation. To
   change types, create a new queue and migrate consumers/producers.

10. **NEVER assume cross-account delivery works without access policy
    AND IAM permissions.** Cross-account delivery requires BOTH: (1)
    the queue access policy grants `sqs:SendMessage` to the producer's
    account, AND (2) the producer's IAM role allows `sqs:SendMessage`
    to the queue. Both sides must be configured.

## Output format

```text
SQS_FIFO: <queue-name> (<queue-url>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Queue name: <name>.fifo
  [✓|✗] FifoQueue: true (immutable)
  [✓|✗] ContentBasedDeduplication: true | false (explicit dedup ID)
  [✓|✗] DeduplicationScope: queue | messageGroup
  [✓|✗] ThroughputLimit: perQueue | messagesPerGroupId
  [✓|✗] High-throughput mode: enabled (per-group dedup + throughput) | disabled
  [✓|✗] Message group ID strategy: <per-entity|single-group> — <description>
  [✓|✗] Visibility timeout: <seconds> (consumer processing time estimate: <seconds>)
  [✓|✗] DLQ: <dlq-name>.fifo (<dlq-arn>) — maxReceiveCount: <count> | None
  [✓|✗] SSE-KMS encryption: enabled (<key-arn>) | disabled
  [✓|✗] Access policy: <same-account|cross-account> — <description>
  [✓|✗] Redrive policy: configured (maxReceiveCount=<count>) | not configured
  [✓|✗] Cross-account delivery: enabled (producer accounts: <list>) | disabled
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws sqs get-queue-attributes --queue-url <url> --attribute-names All
  aws sqs get-queue-attributes --queue-url <dlq-url> --attribute-names All
```

### Worked example — standard FIFO with deduplication, DLQ, and SSE-KMS

```text
SQS_FIFO: order-processing.fifo (https://sqs.us-east-1.amazonaws.com/123456789012/order-processing.fifo)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Queue name: order-processing.fifo
  [✓] FifoQueue: true (immutable)
  [✓] ContentBasedDeduplication: false (explicit dedup ID)
  [✓] DeduplicationScope: queue
  [✓] ThroughputLimit: perQueue
  [✓] High-throughput mode: disabled
  [✓] Message group ID strategy: per-entity (customer ID) — per-customer ordering with parallel processing
  [✓] Visibility timeout: 120 (consumer processing time estimate: 60s)
  [✓] DLQ: order-processing-dlq.fifo (arn:aws:sqs:us-east-1:123456789012:order-processing-dlq.fifo) — maxReceiveCount: 5
  [✓] SSE-KMS encryption: enabled (arn:aws:kms:us-east-1:123456789012:key/abc123)
  [✓] Access policy: cross-account — producer account 999999999999 granted sqs:SendMessage
  [✓] Redrive policy: configured (maxReceiveCount=5)
  [✓] Cross-account delivery: enabled (producer accounts: 999999999999)
  [✓] Tags: Environment=production, Application=order-service
VERIFICATION_COMMANDS:
  aws sqs get-queue-attributes --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/order-processing.fifo --attribute-names All
  aws sqs get-queue-attributes --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/order-processing-dlq.fifo --attribute-names All
```

## Error handling

- **Message not delivered:** ensure `MessageGroupId` is included on
  every send. If `ContentBasedDeduplication=false`, ensure
  `MessageDeduplicationId` is also included.
- **Duplicate processing:** visibility timeout may be too short —
  increase to at least 2x processing time. Or content-based dedup is
  not catching logical duplicates — switch to explicit dedup ID.
- **Throughput limit hit:** standard FIFO is limited to 300 TPS per
  API action. Enable high-throughput mode or distribute message groups.
- **DLQ attachment fails:** the DLQ must be a FIFO queue. Standard
  DLQs are rejected for FIFO main queues.
- **Cross-account delivery fails:** verify both the queue access policy
  grants `sqs:SendMessage` to the producer account AND the producer's
  IAM role permits it. If SSE-KMS, the key policy must allow the
  producer account.

## Domain

AWS CloudOps / Amazon SQS FIFO Queue Provisioning and Message
Ordering.

## AWS documentation

- **SQS FIFO queues** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-fifo-queues.html
- **Deduplication** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/using-messagededuplicationid-property.html
- **High-throughput FIFO** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/quotas-queues.html
- **DLQ and redrive** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html
- **SSE-KMS** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-server-side-encryption.html
