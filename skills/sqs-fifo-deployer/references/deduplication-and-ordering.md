# Deduplication and Ordering — SQS FIFO Deployer

Deep reference on FIFO message ordering mechanics (message group
ID as partitioning key, within-group strict ordering, cross-group
parallelism), deduplication strategies (content-based vs explicit
dedup ID, 5-minute dedup window, high-throughput scope change),
and message group ID selection guidance. Loaded on demand by the
skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## FIFO message ordering

### How ordering works

SQS FIFO guarantees first-in-first-out ordering within a message
group. A message group is defined by the `MessageGroupId`
attribute set by the producer. Messages with the same group ID
are delivered to consumers in the order they were sent.

```text
Producer sends:
  Msg1 (GroupId=customer-123, body="order created")
  Msg2 (GroupId=customer-123, body="payment processed")
  Msg3 (GroupId=customer-456, body="order created")
  Msg4 (GroupId=customer-123, body="order shipped")

Consumer receives:
  Msg1 (GroupId=customer-123) → process
  Msg2 (GroupId=customer-123) → process (AFTER Msg1 — same group)
  Msg3 (GroupId=customer-456) → can be processed IN PARALLEL with Msg1/2
  Msg4 (GroupId=customer-123) → process (AFTER Msg2 — same group)

Ordering guarantee:
  Within customer-123: Msg1 → Msg2 → Msg4 (strict order)
  customer-456: Msg3 (independent, can overlap with customer-123)
```

### Message group ID as partitioning key

The message group ID is the critical design decision for a FIFO
queue. It determines:

1. **Ordering scope:** ordering is guaranteed within a group, not
   across groups.
2. **Parallelism:** the number of active groups determines how
   many consumers can process messages in parallel.
3. **Throughput scaling:** in high-throughput mode, each group
   gets its own 300 TPS allocation.

**Group ID selection patterns:**

| Pattern | Example | Ordering scope | Parallelism | When to use |
|---|---|---|---|---|
| Per-entity | `customer-123` | Per-customer ordering | High (many customers) | Most common — per-entity ordering |
| Per-aggregate | `order-abc-123` | Per-order ordering | Very high (many orders) | When entity = order/transaction |
| Per-tenant | `tenant-acme` | Per-tenant ordering | Medium | Multi-tenant SaaS |
| Per-region | `us-east-1` | Per-region ordering | Low (few regions) | Regional processing |
| Single group | `all` | Global ordering | None (1 consumer) | When strict global ordering is needed |

### Single message group caveat

A single message group ID (e.g., "all") serializes ALL messages
through one stream. Only one consumer can process at a time. This
is the #1 cause of FIFO throughput problems.

```text
Single group ("all"):
  Consumer1 ← Msg1 → process → delete
  Consumer2 ← (blocked — same group, must wait for Msg1 to be deleted)
  Consumer3 ← (blocked)

  Effective throughput: 1 consumer = 300 TPS max (standard FIFO)

Per-entity groups ("customer-123", "customer-456", ...):
  Consumer1 ← Msg1 (customer-123) → process → delete
  Consumer2 ← Msg3 (customer-456) → process → delete (parallel)
  Consumer3 ← Msg5 (customer-789) → process → delete (parallel)

  Effective throughput: N consumers × 300 TPS (if enough groups)
```

## Deduplication

### Content-based deduplication (ContentBasedDeduplication=true)

When enabled, SQS generates a deduplication ID from the SHA-256
hash of the message body. If a message with the same body is sent
within the deduplication window (5 minutes), SQS does NOT enqueue
it again (but returns a success response to the producer).

```bash
# Enable content-based deduplication at queue creation
aws sqs create-queue \
  --queue-name "my-queue.fifo" \
  --attributes "FifoQueue=true,ContentBasedDeduplication=true"

# Send message — SQS generates dedup ID from body hash
aws sqs send-message \
  --queue-url "$QUEUE_URL" \
  --message-body '{"orderId": "order-001"}' \
  --message-group-id "customer-123"
```

**Limitation:** content-based dedup hashes the RAW message body.
Two messages with different bodies (even if logically identical)
are NOT deduplicated. For example:

- `{"orderId": "order-001", "timestamp": "10:00"}` — dedup ID A
- `{"orderId": "order-001", "timestamp": "10:01"}` — dedup ID B
- These are treated as DIFFERENT messages (different hashes).

### Explicit deduplication (MessageDeduplicationId)

The producer sends an explicit `MessageDeduplicationId` with each
message. This overrides content-based dedup (if both are present).
The producer controls dedup semantics.

```bash
# Explicit dedup — producer controls dedup ID
aws sqs send-message \
  --queue-url "$QUEUE_URL" \
  --message-body '{"orderId": "order-001", "timestamp": "10:00"}' \
  --message-group-id "customer-123" \
  --message-deduplication-id "order-001"

# Same logical message, different body — dedup ID is the same → deduplicated
aws sqs send-message \
  --queue-url "$QUEUE_URL" \
  --message-body '{"orderId": "order-001", "timestamp": "10:01"}' \
  --message-group-id "customer-123" \
  --message-deduplication-id "order-001"
```

**When to use explicit dedup:**
- Message body may vary but logical content is the same (retries,
  updated timestamps).
- Producer has a stable business key (order ID, event ID) that
  uniquely identifies the logical message.
- You want to dedup based on a composite key (e.g.,
  `customerId:eventType`).

### Deduplication window

The deduplication window is 5 minutes from the first receipt of
a dedup ID. After 5 minutes, the same dedup ID is treated as a
new message.

```text
Timeline:
  T=0:  Send Msg with dedupId=order-001 → enqueued
  T=30: Send Msg with dedupId=order-001 → deduplicated (not enqueued)
  T=120: Send Msg with dedupId=order-001 → deduplicated (not enqueued)
  T=300: Send Msg with dedupId=order-001 → deduplicated (still within 5 min)
  T=301: Send Msg with dedupId=order-001 → NEW message (5 min window expired)
```

**Key:** the dedup window starts from the FIRST successful send,
not from each subsequent send.

### High-throughput deduplication scope

In high-throughput mode (`DeduplicationScope=messageGroup`), the
dedup window is per message group, not per queue. The same dedup
ID in DIFFERENT groups does NOT deduplicate.

```text
Standard FIFO (DeduplicationScope=queue):
  Msg (dedupId=order-001, group=customer-123) → enqueued
  Msg (dedupId=order-001, group=customer-456) → DEDUPLICATED (same queue-level dedup)

High-throughput FIFO (DeduplicationScope=messageGroup):
  Msg (dedupId=order-001, group=customer-123) → enqueued
  Msg (dedupId=order-001, group=customer-456) → ENQUEUED (different group, different dedup scope)
```

**Key:** this is a semantic change when switching to high-throughput
mode. If your dedup logic assumed queue-level scope, the same dedup
ID may now produce duplicate messages in different groups.

## Message group ID and dedup ID interaction

Every message to a FIFO queue MUST have:
- `MessageGroupId` (required) — determines ordering partition
- `MessageDeduplicationId` OR `ContentBasedDeduplication=true` —
  dedup method

If neither dedup method is provided, the API rejects the message.

```text
Required attributes for FIFO send-message:
  ✓ MessageGroupId (always required)
  ✓ MessageDeduplicationId (if ContentBasedDeduplication=false)
    OR
  ✓ ContentBasedDeduplication=true on the queue (auto-generates dedup ID)

  Missing both → InvalidParameterValue API error
```

## Terraform examples

```hcl
# Standard FIFO queue with content-based dedup
resource "aws_sqs_queue" "standard_fifo" {
  name                        = "order-processing.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  visibility_timeout_seconds  = 120
  message_retention_seconds   = 345600

  tags = {
    Environment = "production"
  }
}

# High-throughput FIFO queue
resource "aws_sqs_queue" "high_throughput_fifo" {
  name                  = "high-throughput-events.fifo"
  fifo_queue            = true
  deduplication_scope   = "messageGroup"
  throughput_limit      = "messagesPerGroupId"
  visibility_timeout_seconds = 60
}

# FIFO DLQ
resource "aws_sqs_queue" "dlq" {
  name       = "order-processing-dlq.fifo"
  fifo_queue = true
}

# Redrive policy
resource "aws_sqs_queue_redrive_policy" "main" {
  queue_url = aws_sqs_queue.standard_fifo.url
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 5
  })
}

# SSE-KMS encryption
resource "aws_sqs_queue" "encrypted_fifo" {
  name              = "secure-queue.fifo"
  fifo_queue        = true
  kms_master_key_id = aws_kms_key.sqs.arn
  kms_data_key_reuse_period_seconds = 300
}
```
