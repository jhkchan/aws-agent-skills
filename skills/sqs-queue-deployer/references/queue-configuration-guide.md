# Queue Configuration Guide — SQS Queue Deployer

Deep reference on SQS queue internals, FIFO message-group ordering,
deduplication hash mechanics, visibility timeout interaction with Lambda,
and high-throughput FIFO configuration details.

## Queue type internals

### Standard queue delivery semantics

Standard queues provide **at-least-once** delivery. Under normal operation,
each message is delivered once. Under contention (multiple consumers
polling), a message may be delivered more than once:

1. Consumer A receives message M (visibility timeout starts).
2. Consumer A processes M but is slow (p99 > visibility timeout).
3. Visibility timeout expires. Message M becomes visible again.
4. Consumer B receives message M.
5. Both Consumer A and Consumer B process M.

This is why **consumers MUST be idempotent** for Standard queues. Design
the consumer to handle duplicate messages safely (dedup by a business key,
use a database unique constraint, or track processed message IDs).

### FIFO queue ordering mechanics

FIFO queues guarantee ordering **per message group**. Messages with the
same `MessageGroupId` are delivered in the order they were sent. Messages
with different group IDs are processed in parallel.

```
Producer sends:
  GroupA-1, GroupB-1, GroupA-2, GroupC-1, GroupA-3

Consumer receives (in order):
  GroupA-1 → GroupA-2 → GroupA-3  (ordered within group A)
  GroupB-1                            (parallel with group A)
  GroupC-1                            (parallel with groups A and B)
```

**Message group blocking:** if a message in group A fails processing and
returns to the queue, the ENTIRE group A is blocked until that message is
consumed or moved to the DLQ. This is why maxReceiveCount tuning is MORE
critical for FIFO queues — a poison pill stalls the whole group.

### Deduplication hash mechanics

FIFO queues deduplicate messages within a **5-minute window** using one of
two methods:

**ContentBasedDeduplication=true (topic-level):**

SQS computes a SHA-256 hash of:
- Message body
- Message attributes (not system attributes)

If two messages within 5 minutes produce the same hash, the second is
silently dropped. The hash is computed on the exact byte content —
whitespace differences produce different hashes.

**Explicit DeduplicationId (message-level):**

The publisher sends a `MessageDeduplicationId` on each message. If two
messages within 5 minutes share the same ID, the second is dropped —
regardless of content. This is useful when the same logical message may
have different formatting (timestamps, request IDs in the body).

**Interaction:** if `ContentBasedDeduplication=true` AND the publisher
sends a `DeduplicationId`, the explicit ID takes precedence.

## Visibility timeout deep dive

### The visibility timeout clock

The visibility timeout starts when `ReceiveMessage` delivers the message,
not when the consumer starts processing. For Lambda, the clock starts when
the event source mapping calls ReceiveMessage, which is BEFORE the Lambda
function is invoked. The gap between ReceiveMessage and function start can
be 0-5 seconds (cold start + batching window).

```
Timeline:
  T=0s   ReceiveMessage delivers message (visibility clock starts)
  T=2s   Lambda function starts (cold start)
  T=10s  Lambda function finishes processing
  T=10s  Lambda calls DeleteMessage (message removed)

If processing takes 65 seconds with a 60s visibility timeout:
  T=0s   ReceiveMessage delivers message
  T=60s  Visibility timeout expires (message becomes visible)
  T=65s  Lambda finishes, calls DeleteMessage (too late — message was re-delivered)
```

### Lambda event source mapping visibility timeout

The Lambda event source mapping has its own `VisibilityTimeout` parameter
that **overrides** the queue-level value. The mapping visibility timeout
must be >= the function's `Timeout`. If it is shorter, the message returns
to the queue before the function finishes — guaranteeing duplicate
processing.

**Recommended formula:**
```
event_source_mapping.VisibilityTimeout >= lambda.Timeout * 6
```

The factor of 6 accounts for the Lambda retry policy (3 retries with
exponential backoff within the batch window). Without enough headroom,
the message hits maxReceiveCount before the retries complete.

### VisibilityTimeout vs maxReceiveCount

The effective retry window is:
```
effective_retry_window = VisibilityTimeout × maxReceiveCount
```

At VisibilityTimeout=30s, maxReceiveCount=5: 150 seconds (2.5 minutes).
At VisibilityTimeout=60s, maxReceiveCount=5: 300 seconds (5 minutes).
At VisibilityTimeout=30s, maxReceiveCount=100: 3000 seconds (50 minutes).

If the consumer's p99 exceeds VisibilityTimeout, the message is re-delivered
on every cycle — the receive count increments even though the consumer did
not fail. This is the #1 cause of false-positive DLQ entries.

## High-throughput FIFO configuration

Standard FIFO queues are limited to **300 TPS** aggregate. High-throughput
FIFO extends this to **1500 TPS** by changing the deduplication scope and
throughput limit basis.

### Enabling high-throughput FIFO

```bash
aws sqs create-queue \
  --queue-name high-throughput.fifo \
  --attributes \
    FifoQueue=true,\
    ContentBasedDeduplication=true,\
    FifoThroughputLimit=perMessageGroupId,\
    DeduplicationScope=messageGroup
```

**Attribute meaning:**

| Attribute | Value | Effect |
|---|---|---|
| `FifoThroughputLimit` | `perQueue` (default) | 300 TPS aggregate across all message groups |
| `FifoThroughputLimit` | `perMessageGroupId` | 300 TPS per message group, up to 1500 TPS aggregate |
| `DeduplicationScope` | `queue` (default) | Dedup runs across the entire queue (global) |
| `DeduplicationScope` | `messageGroup` | Dedup runs per message group (allows higher throughput) |

**Trade-off:** high-throughput FIFO loosens deduplication. With
`DeduplicationScope=messageGroup`, two messages in different groups with
the same body are NOT deduplicated. This is acceptable for most workloads
but may cause issues if cross-group dedup is required.

### Cannot change after creation

The `FifoThroughputLimit` and `DeduplicationScope` attributes are immutable
after queue creation. To switch between standard and high-throughput FIFO,
you must delete and recreate the queue.

## Lambda partial batch responses

### How partial batch responses work

Without partial batch responses, if a Lambda function processes a batch of
10 messages and throws on message #7, the entire batch is returned to the
queue. Messages #1-6 (successfully processed) are re-delivered and
reprocessed — causing duplicate side effects.

With partial batch responses (`ReportBatchItemFailures`), the function
returns a `batchItemFailures` list identifying which messages failed. Only
those messages remain in the queue; successful messages are deleted.

### Function response format

```python
def lambda_handler(event, context):
    batch_item_failures = []
    for record in event['Records']:
        try:
            process_message(record)
        except Exception as e:
            # Only this message will be retried
            batch_item_failures.append({
                'itemIdentifier': record['messageId']
            })
    return {
        'batchItemFailures': batch_item_failures
    }
```

**If the function does NOT return `batchItemFailures`:**
- If the function succeeds (no exception): all messages are deleted.
- If the function throws: all messages are returned to the queue.

**If the function returns `batchItemFailures`:**
- Messages in the list are returned to the queue (receive count
  incremented).
- Messages NOT in the list are deleted.

### Event source mapping configuration

```bash
aws lambda create-event-source-mapping \
  --function-name my-processor \
  --event-source-arn arn:aws:sqs:us-east-1:111111111111:my-queue \
  --batch-size 10 \
  --maximum-batching-window-in-seconds 5 \
  --visibility-timeout 300 \
  --function-response-types ReportBatchItemFailures
```

The `--function-response-types ReportBatchItemFailures` flag enables
partial batch response processing. Without it, the `batchItemFailures` in
the response is ignored.

## Cross-account queue access

### Resource-based policy (queue policy)

For cross-account access, the queue policy must explicitly grant the
foreign account the required actions:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::222222222222:root" },
    "Action": ["sqs:SendMessage", "sqs:ReceiveMessage"],
    "Resource": "arn:aws:sqs:us-east-1:111111111111:my-queue"
  }]
}
```

### KMS key policy (for SSE-KMS queues)

If the queue uses SSE-KMS, the KMS key policy must ALSO grant the foreign
account `kms:Decrypt` and `kms:GenerateDataKey*`:

```json
{
  "Sid": "Allow cross-account SQS access",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::222222222222:root" },
  "Action": ["kms:Decrypt", "kms:GenerateDataKey*"],
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "kms:ViaService": "sqs.us-east-1.amazonaws.com"
    }
  }
}
```

**Without both policies, cross-account access fails with
`KMSAccessDeniedException`.** The queue policy allows the API call, but
the KMS key policy blocks the decrypt. This is the most common
cross-account SQS deployment failure.

## Terraform equivalent

```hcl
# Standard queue with DLQ
resource "aws_sqs_queue" "dlq" {
  name                       = "order-events-dlq"
  message_retention_seconds  = 1209600  # 14 days
  sqs_managed_sse_enabled    = true
}

resource "aws_sqs_queue" "main" {
  name                              = "order-events"
  visibility_timeout_seconds        = 60
  message_retention_seconds         = 345600  # 4 days
  receive_wait_time_seconds         = 20      # long polling
  sqs_managed_sse_enabled           = true
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 5
  })
}

# FIFO queue
resource "aws_sqs_queue" "fifo" {
  name                        = "order-events.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  visibility_timeout_seconds  = 120
  receive_wait_time_seconds   = 20
  sqs_managed_sse_enabled     = true
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.fifo_dlq.arn
    maxReceiveCount     = 10
  })
}

# High-throughput FIFO
resource "aws_sqs_queue" "ht_fifo" {
  name                        = "ht-orders.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  fifo_throughput_limit       = "perMessageGroupId"
  deduplication_scope         = "messageGroup"
  visibility_timeout_seconds  = 300
  receive_wait_time_seconds   = 20
  sqs_managed_sse_enabled     = true
}
```

## Edge cases (detailed)

### FIFO queue with all messages using the same MessageGroupId

A FIFO queue guarantees ordering WITHIN a `MessageGroupId` and parallelism
ACROSS distinct `MessageGroupId`s. If every producer sends messages with
the same `MessageGroupId` (e.g., a hardcoded constant like `"default"` or
a tenant ID that resolves to one value), the queue degenerates to a
single-message-in-flight serial pipeline — throughput drops to 300 TPS
(standard FIFO) or 10 TPS per group even on a high-throughput FIFO queue.
This silently defeats the purpose of FIFO (which is per-group parallelism,
not global ordering) and surfaces as a backlog that looks like SQS is
"slow".

Detection: `ApproximateNumberOfMessagesNotVisible` rising while
`NumberOfEmptyReceives` is high. Remediation: redesign the producer to
use a sharded `MessageGroupId` (e.g., `order-{customer_id}` for
per-customer ordering). Surface as:
`FIFO_DEGENERATE_SINGLE_GROUP — throughput capped at <X> TPS due to
single MessageGroupId`.

### FIFO queue with deduplication scope collision after high-throughput mode change

Switching a FIFO queue to high-throughput mode
(`DeduplicationScope=messageGroup,
FifoThroughputLimit=perMessageGroupId`) changes the deduplication window
from queue-scoped to message-group-scoped. Messages in different groups
that previously deduplicated against each other no longer do — duplicates
will appear post-change.

Detection: pre-change audit of producer `MessageDeduplicationId` use.
Remediation: ensure producers set explicit `MessageDeduplicationId` based
on payload hash, not relying on queue-level dedup scope.

### Lambda event source mapping with BatchSize > 1 and ReportBatchItemFailures disabled

Without partial-batch responses, a single failed message in a batch of 10
causes all 10 to be retried — including the 9 that succeeded. Under a
sustained poison-pill scenario, this causes the same 9 messages to be
processed 10s of times.

Remediation: enable `FunctionResponseTypes: [ReportBatchItemFailures]` on
the event source mapping. Detection:
`aws lambda list-event-source-mappings --function-name <name>
--query 'EventSourceMappings[].FunctionResponseTypes'`.

## Expert heuristic: visibility timeout race condition (detailed)

The single most common cause of duplicate processing in SQS + Lambda
event-source-mapping pipelines is a visibility timeout that is SHORTER
than the consumer's actual processing time, combined with a Lambda
function that runs longer than expected under load.

**The race, step by step:**

1. Lambda receives a batch of messages. Lambda timeout is 15 minutes (900s).
2. Visibility timeout on the queue (or event source mapping) is set to
   30s, which the operator believed was "plenty" based on p50 of 2s.
3. Under load (CPU contention, downstream API latency, cold start),
   actual processing time spikes to 45s p99.
4. At T+30s, SQS makes the message visible again because no
   `ChangeMessageVisibility` extension was sent.
5. Another Lambda invocation receives the same message and starts
   processing it. The original invocation is STILL running.
6. Both invocations complete; the downstream sees the side effect twice
   (duplicate charge, duplicate email, idempotency-key collision).

**Why 6x and not 2x:** the buffer absorbs (a) Lambda cold-start delay
(up to 5s for VPC-attached functions), (b) SDK retry backoff on downstream
APIs (default 3 retries with exponential backoff = ~20s for AWS SDK v2),
(c) one visibility-timeout extension via `ChangeMessageVisibility`.

**Fix at deploy time:** if the operator requests visibility timeout
< 6x the stated p99, surface as `VERDICT: PREREQUISITES_MISSING` with
the gap: `VisibilityTimeout <N>s is below 6x p99 (<M>s). Set
VisibilityTimeout >= <6xp99>s on the event source mapping OR reduce
Lambda concurrency/timeout.`

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
