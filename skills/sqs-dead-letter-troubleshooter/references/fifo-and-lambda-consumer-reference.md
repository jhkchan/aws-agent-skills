# SQS FIFO and Lambda Consumer Reference Guide

Supplementary reference for the SQS Dead-Letter Troubleshooter skill.
Loaded on-demand when a diagnostic needs FIFO message ordering semantics,
Lambda event source mapping configuration, batch failure handling, or
message group behavior.

## FIFO queue behavior

### MessageGroupId and ordering

FIFO queues guarantee strict ordering within a MessageGroupId. Messages
in different MessageGroupIds are independent — they can be processed in
parallel.

```
Queue: orders.fifo
MessageGroupId: "cust-A"
  msg-1 → processed first
  msg-2 → processed second (AFTER msg-1)
  msg-3 → processed third (AFTER msg-2)

MessageGroupId: "cust-B"
  msg-4 → processed independently (parallel with cust-A)
  msg-5 → processed after msg-4 (within cust-B)
```

### Poison message effect in FIFO

If a message fails repeatedly (poison message), it blocks ALL messages
behind it in the same MessageGroupId:

```
MessageGroupId: "cust-A"
  msg-1 → processed ✓
  msg-2 → FAIL (poison) → received 5x → DLQ
  msg-3 → BLOCKED (FIFO ordering: cannot deliver until msg-2 is done)
  msg-4 → BLOCKED (waiting for msg-3)

MessageGroupId: "cust-B" (not affected)
  msg-5 → processed ✓
  msg-6 → processed ✓
```

Once msg-2 moves to the DLQ, msg-3 becomes deliverable. If msg-3 also
fails (same consumer bug), the stall continues for that group.

### Message deduplication

FIFO queues deduplicate messages within a 5-minute window:
- **Content-based deduplication** (`ContentBasedDeduplication: true`):
  uses a SHA-256 hash of the message body.
- **Explicit deduplication ID**: producer provides
  `MessageDeduplicationId` per message.

If a producer sends the same message twice within 5 minutes, the second
is silently dropped. This can cause "missing messages" symptoms if the
producer is unaware of deduplication.

### FIFO throughput

| Mode | Throughput limit |
|---|---|
| Standard FIFO | 300 messages/second per API action, 300 TPS per queue |
| FIFO high-throughput (`FifoThroughputLimit: perMessageGroupId`) | 1,000 TPS per MessageGroupId, up to 30,000 TPS per queue |

Diagnostically, if a FIFO queue's throughput is low but no poison
message is present, check whether the throughput limit is per-queue (all
groups share 300 TPS) or per-group (each group gets its own 1,000 TPS).

## Lambda event source mapping for SQS

The Lambda event source mapping is the polling configuration that
connects SQS to Lambda. It has its own parameters that can override
queue-level settings.

### Key parameters

| Parameter | Default | Effect |
|---|---|---|
| `BatchSize` | 10 | Messages per Lambda invocation (1-10,000) |
| `VisibilityTimeout` | 30 (seconds) | OVERRIDES the queue's VisibilityTimeout for this mapping |
| `MaximumBatchingWindowInSeconds` | 0 | Collect messages for N seconds before invoking (0 = immediate) |
| `FunctionResponseTypes` | (none) | Add `ReportBatchItemFailures` for partial batch failure handling |
| `Enabled` | true | Set to false to pause processing |
| `MaxRecordCount` | (varies) | Maximum records in a single invocation |

### Critical: VisibilityTimeout override

The event source mapping's `VisibilityTimeout` takes precedence over
the queue's `VisibilityTimeout`:

```bash
# Queue VT: 300s
# Event source mapping VT: 30s (default)
# EFFECTIVE VT: 30s (the mapping's value wins)
```

Operators who set the queue's VT to 300s but leave the event source
mapping at the default 30s still see premature re-delivery.

**Fix:** Set the VT on BOTH the queue and the event source mapping:

```bash
# Queue-level
aws sqs set-queue-attributes \
  --queue-url <queue-url> \
  --attributes VisibilityTimeout=300

# Event source mapping
aws lambda update-event-source-mapping \
  --uuid <mapping-uuid> \
  --visibility-timeout 300
```

### Rule of thumb: VisibilityTimeout >= 6x processing time

The visibility timeout should be at least 6x the consumer's expected
processing time. This accounts for:
- Lambda cold starts (up to 10s for some runtimes)
- Retry attempts within the Lambda timeout
- Batch processing overhead (BatchSize > 1)
- Transient downstream latency spikes

## ReportBatchItemFailures (partial batch handling)

Without `ReportBatchItemFailures`, a single bad record in a batch causes
the ENTIRE batch to retry. All messages in the batch increment their
receive count simultaneously.

### Enabling partial batch failures

```bash
aws lambda update-event-source-mapping \
  --uuid <mapping-uuid> \
  --function-response-types '["ReportBatchItemFailures"]'
```

### Consumer response format

The Lambda must return a `batchItemFailures` list with the message IDs
that failed processing:

```json
{
  "batchItemFailures": [
    {"itemIdentifier": "failed-message-id-1"},
    {"itemIdentifier": "failed-message-id-3"}
  ]
}
```

Only the failed messages are retried; successful messages in the same
batch are deleted and not re-delivered.

### Effect on DLQ accumulation

Without `ReportBatchItemFailures`:
- 1 poison message in a batch of 10 → ALL 10 retry.
- All 10 increment their receive count.
- After maxReceiveCount retries, ALL 10 messages move to the DLQ.
- 9 perfectly good messages land in the DLQ alongside the 1 poison.

With `ReportBatchItemFailures`:
- 1 poison message in a batch of 10 → only the 1 fails.
- The other 9 are deleted successfully.
- Only the 1 poison message eventually reaches the DLQ.

## Lambda concurrency and SQS

### How Lambda concurrency interacts with SQS polling

The Lambda event source mapping polls SQS and invokes Lambda
asynchronously. The number of concurrent Lambda invocations is bounded
by:
1. The function's reserved concurrency (if set).
2. The account-level concurrent execution limit (default: 1,000).

When either limit is reached:
- The event source mapping stops polling (or polls but cannot invoke).
- Messages remain in the queue past their visibility timeout.
- The receive count increments on the next poll cycle.
- After maxReceiveCount retries, messages move to the DLQ.

### Diagnosis pattern: Lambda throttle → SQS DLQ

```
1. Queue backlog grows (consumer can't invoke fast enough)
2. Messages exceed visibility timeout while waiting for Lambda
3. Receive count increments
4. Messages move to DLQ after maxReceiveCount
5. DLQ fills while source queue backlog also grows
```

CloudWatch signals:
- `AWS/Lambda Throttles > 0` (sustained)
- `AWS/Lambda ConcurrentExecutions` at the reserved or account limit
- `AWS/SQS ApproximateNumberOfMessages` (source) growing
- `AWS/SQS ApproximateNumberOfMessages` (DLQ) growing

### Fix: raise reserved concurrency

```bash
aws lambda put-function-concurrency \
  --function-name <consumer-lambda> \
  --reserved-concurrent-executions <new-value>
```

Verify the account-level concurrency limit supports the new value. If
not, request a quota increase via AWS Support Center.

### Alternative: set a concurrency floor

If a "noisy neighbor" function in the account consumes all concurrency,
set a reserved concurrency floor on the SQS consumer to guarantee a
minimum number of concurrent executions:

```bash
aws lambda put-function-concurrency \
  --function-name <sqs-consumer-lambda> \
  --reserved-concurrent-executions 20
```

This guarantees 20 concurrent executions for the SQS consumer,
regardless of other functions' load.

## SQS Extended Client Library

For payloads > 256 KB:

- **Producer:** stores the payload in S3, sends a message with an S3
  pointer (instruction token) to SQS.
- **Consumer:** receives the SQS message, fetches the payload from S3
  using the pointer.

If the consumer does NOT use the Extended Client Library:
- It receives only the S3 pointer (a small JSON with bucket and key).
- The consumer sees a tiny message body that is meaningless without the
  S3 fetch.

Libraries available:
- Java: `AmazonSQSExtendedClient`
- Python: `amazon-sqs-extended-client-python`

## start-message-move-task API (v2 redrive)

### Starting a redrive

```bash
aws sqs start-message-move-task \
  --source-arn <dlq-arn> \
  [--destination-arn <target-queue-arn>] \
  [--max-number-of-messages-per-second <rate>] \
  --output json
# Returns: {"TaskHandle": "AQX5..."}
```

- `--source-arn`: The DLQ ARN (required).
- `--destination-arn`: Defaults to the source queue that originally fed
  this DLQ. Override for a custom destination.
- `--max-number-of-messages-per-second`: Rate limit to avoid
  overwhelming the consumer.

### Checking task status

```bash
aws sqs describe-message-move-task \
  --task-handle <task-handle> \
  --output json
```

Returns:
- `Status`: `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLING`
- `MessagesMoved`: count of messages moved so far
- `ApproximateNumberOfMessagesMoved`: approximate total

### Cancelling a task

```bash
aws sqs cancel-message-move-task \
  --task-handle <task-handle>
```

### Common redrive failures

| Status / Error | Cause |
|---|---|
| `FAILED` with type mismatch error | DLQ and destination have different queue types (standard vs FIFO) |
| `RUNNING` with `MessagesMoved: 0` | Destination queue does not exist, or DLQ is empty, or redrive-allow-policy blocks the source |
| `TaskHandle` not found | Task already completed or was cancelled |
| `COMPLETED` but fewer than expected moved | Messages were deleted from DLQ during the task (retention expiry, manual purge) |

### RedriveAllowPolicy

The DLQ's `RedriveAllowPolicy` controls which source queues can redrive:

```json
{
  "redrivePermission": "allowAll"
}
```

OR

```json
{
  "redrivePermission": "byQueue",
  "sourceQueueArns": ["arn:aws:sqs:...:source-queue"]
}
```

If `redrivePermission` is `byQueue` and the source queue ARN is not
listed, redrive is blocked.
