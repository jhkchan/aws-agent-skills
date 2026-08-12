# SQS Queue Attributes and Redrive Reference Guide

Supplementary reference for the SQS Dead-Letter Troubleshooter skill.
Loaded on-demand when a diagnostic needs queue attribute semantics,
redrive policy parsing, message lifecycle details, or DLQ redrive API
usage.

## Queue attributes reference

| Attribute | Default | Max | Notes |
|---|---|---|---|
| `VisibilityTimeout` | 30s | 43,200s (12h) | Time a received message is invisible to other consumers |
| `MessageRetentionPeriod` | 345,600s (4d) | 1,209,600s (14d) | Messages older than this are silently deleted (NOT moved to DLQ) |
| `DelaySeconds` | 0 | 900s (15m) | Delivery delay for standard queues (FIFO uses `DelaySeconds` per message) |
| `MaximumMessageSize` | 262,144 (256 KB) | 262,144 | Cannot be increased; use Extended Client Library for larger payloads |
| `ReceiveMessageWaitTimeSeconds` | 0 | 20 | Long polling duration; reduces empty receives and API costs |
| `RedrivePolicy` | (none) | — | JSON: `{"deadLetterTargetArn":"...","maxReceiveCount":"N"}` |
| `FifoQueue` | false | — | true for FIFO queues (name must end in `.fifo`) |
| `ContentBasedDeduplication` | false | — | FIFO only: auto-deduplicate using message body hash within 5-min window |
| `DeduplicationScope` | queue | messageGroup | FIFO high-throughput mode: `queue` or `messageGroup` |
| `FifoThroughputLimit` | perQueue | perMessageGroupId | FIFO high-throughput mode |

## RedrivePolicy structure

```json
{
  "deadLetterTargetArn": "arn:aws:sqs:us-east-1:111111111111:my-dlq",
  "maxReceiveCount": "5"
}
```

- `deadLetterTargetArn`: The ARN of the DLQ. Must be in the same region
  and account. For FIFO source queues, the DLQ MUST also be FIFO.
- `maxReceiveCount`: String-encoded integer. The number of receive
  attempts after which a message is moved to the DLQ. Default
  recommendation: 3-5 for most consumers.

### Setting the RedrivePolicy

```bash
aws sqs set-queue-attributes \
  --queue-url <source-queue-url> \
  --attributes '{"RedrivePolicy":"{\"deadLetterTargetArn\":\"arn:aws:sqs:us-east-1:111111111111:my-dlq\",\"maxReceiveCount\":\"5\"}"}'
```

Note: the value of RedrivePolicy is a JSON-encoded string inside the
attributes JSON. Double-escaping is required.

## maxReceiveCount semantics

`maxReceiveCount` counts **receive attempts**, not minutes or processing
cycles. Each time a consumer calls `ReceiveMessage` and the message is
delivered, the receive count increments.

### Receive count increment flow

```
1. Message enters queue (ApproximateReceiveCount = 0)
2. Consumer calls ReceiveMessage → message delivered, count = 1
3a. Consumer processes and deletes → message removed (success)
3b. Consumer fails OR visibility timeout expires → message returns
    to queue (visible again)
4. Consumer calls ReceiveMessage again → count = 2
5. Repeat until count > maxReceiveCount
6. Message moved to DLQ
```

### Time-to-DLQ calculation

The effective time-to-DLQ depends on maxReceiveCount and VisibilityTimeout:

```
maxReceiveCount = 3, VT = 30s → minimum ~90s (3 × 30s)
maxReceiveCount = 3, VT = 5s  → minimum ~15s (3 × 5s)
maxReceiveCount = 5, VT = 60s → minimum ~300s (5 × 60s)
```

These are MINIMUM times. Actual time depends on polling frequency and
consumer availability.

## Message lifecycle

```
Producer → SendMessage → message enters queue (VISIBLE)
  ↓
Consumer → ReceiveMessage → message becomes INVISIBLE (VT starts)
  ↓
  ├─ Consumer processes successfully → DeleteMessage → message REMOVED
  │
  └─ Consumer fails / VT expires → message becomes VISIBLE again
       ↓
       Repeat receive cycle until ApproximateReceiveCount > maxReceiveCount
       ↓
       Message moved to DLQ
```

## ApproximateReceiveCount attribute

Each message carries an `ApproximateReceiveCount` attribute that
increments on every `ReceiveMessage` delivery. This attribute is
available when receiving messages:

```bash
aws sqs receive-message \
  --queue-url <queue-url> \
  --max-number-of-messages 5 \
  --attribute-names ApproximateReceiveCount \
  --output json | \
  jq '.Messages[] | {
    MessageId: .MessageId,
    ReceiveCount: .Attributes.ApproximateReceiveCount
  }'
```

On DLQ messages, `ApproximateReceiveCount` equals the source queue's
`maxReceiveCount` at the time of migration — confirming the message
exhausted its retries.

## DLQ type compatibility

| Source Queue Type | DLQ Type Required | Error if Mismatch |
|---|---|---|
| Standard | Standard | — |
| FIFO (.fifo) | FIFO (.fifo) | `InvalidParameterCombination` on StartMessageMoveTask; ordering loss |
| Standard | FIFO | Redrive failures; messages not delivered |
| FIFO | Standard | `InvalidParameterCombination` on StartMessageMoveTask; ordering loss |

### Creating a FIFO DLQ

```bash
aws sqs create-queue \
  --queue-name my-dlq.fifo \
  --attributes FifoQueue=true \
  --output json
```

The queue name MUST end in `.fifo`. Update the source queue's
RedrivePolicy to point to the FIFO DLQ ARN.

## DLQ message inspection

DLQ messages carry the original message body plus metadata:

```bash
aws sqs receive-message \
  --queue-url <dlq-url> \
  --max-number-of-messages 10 \
  --attribute-names All \
  --message-attribute-names All \
  --output json | \
  jq '.Messages[] | {
    MessageId: .MessageId,
    ReceiveCount: .Attributes.ApproximateReceiveCount,
    SentTimestamp: .Attributes.SentTimestamp,
    MessageGroupId: .Attributes.MessageGroupId,
    Body: .Body[0:200]
  }'
```

Key attributes on DLQ messages:
- `ApproximateReceiveCount`: How many times the message was received
  before migration. Should equal maxReceiveCount.
- `MessageGroupId`: For FIFO queues, identifies which group the message
  belongs to. All DLQ messages from the same stuck group share this ID.
- `SentTimestamp`: When the message was originally sent. Useful for
  correlating with deploy timestamps or incident windows.

## CloudWatch metrics for SQS diagnosis

| Metric | What it tells you |
|---|---|
| `ApproximateNumberOfMessagesVisible` | Messages available for receive (backlog size) |
| `ApproximateNumberOfMessagesNotVisible` | Messages in-flight (received but not deleted) |
| `ApproximateNumberOfMessagesDelayed` | Messages waiting for delay to expire |
| `ApproximateAgeOfOldestMessage` | Age of the oldest message in seconds. Approaching MessageRetentionPeriod = expiry risk |
| `NumberOfMessagesSent` | Messages put on the queue |
| `NumberOfMessagesReceived` | Messages received by consumers |
| `NumberOfMessagesDeleted` | Messages successfully processed and deleted |

### Diagnostic metric patterns

| Pattern | Diagnosis |
|---|---|
| NotVisible high, Deleted low | Consumer receiving but not completing — VT or processing time mismatch |
| Visible growing, Received = 0 | Consumer not polling — Lambda event source mapping disabled or no consumer |
| AgeOfOldestMessage approaching MessageRetentionPeriod | Messages will expire before processing — scale consumer or raise retention |
| Sent >> Deleted sustained | Consumer can't keep up — scale, raise concurrency, or raise VT |
