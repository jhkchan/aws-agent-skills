# Diagnostic commands - SQS Dead-Letter Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Account-wide pre-flight commands

```bash
# 1. Source queue attributes (RedrivePolicy, VisibilityTimeout,
#    MessageRetentionPeriod, ApproximateNumberOfMessages,
#    ApproximateNumberOfMessagesNotVisible, FifoQueue, Deduplication)
aws sqs get-queue-attributes \
  --queue-url <source-queue-url> \
  --attribute-names All --output json

# 2. DLQ attributes (RedrivePolicy, ApproximateNumberOfMessages,
#    queue type, redrive-allow-policy)
aws sqs get-queue-attributes \
  --queue-url <dlq-url> \
  --attribute-names All --output json

# 3. List queues that use this DLQ (reverse lookup)
aws sqs list-dead-letter-source-queues \
  --queue-url <dlq-url> --output json

# 4. Consumer Lambda event source mapping (if Lambda-triggered)
aws lambda get-event-source-mapping \
  --function-name <consumer-lambda> --output json 2>/dev/null

# 5. CloudWatch queue metrics (ApproximateNumberOfMessagesVisible,
#    ApproximateAgeOfOldestMessage, NumberOfMessagesSent, Deleted)
aws cloudwatch get-metric-statistics --namespace AWS/SQS \
  --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=<queue-name> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json
```

### Step 2: maxReceiveCount too low

```bash
aws sqs get-queue-attributes \
  --queue-url <source-queue-url> \
  --attribute-names RedrivePolicy VisibilityTimeout --output json
```

Parse the RedrivePolicy:

```bash
aws sqs get-queue-attributes \
  --queue-url <source-queue-url> \
  --attribute-names RedrivePolicy --output json | \
  jq '.Attributes.RedrivePolicy | fromjson'
```

Check `maxReceiveCount`:

| maxReceiveCount | Typical scenario | Diagnosis |
|---|---|---|
| 1 | Every failed processing attempt → DLQ | Almost always too low for transient failures. Should be ≥ 3. |
| 3 | Default for many configurations | Reasonable for idempotent consumers. Check if failure rate is higher than expected. |
| 5 | Moderate resilience | Good for consumers with occasional transient failures. |
| 10+ | High resilience | Rarely the cause of premature DLQ migration. Look at processing failures instead. |

Inspect DLQ messages for their `ApproximateReceiveCount`:

```bash
aws sqs receive-message \
  --queue-url <dlq-url> \
  --max-number-of-messages 5 \
  --message-attribute-names All \
  --attribute-names All --output json | \
  jq '.Messages[] | {
    ApproximateReceiveCount: .Attributes.ApproximateReceiveCount,
    SentTimestamp: .Attributes.SentTimestamp
  }'
```

If `ApproximateReceiveCount` equals maxReceiveCount for all inspected
messages, the messages exhausted their retries legitimately. The issue
is the consumer failing to process, not maxReceiveCount being too low.

If `ApproximateReceiveCount` is much lower than expected (e.g., 1 or 2
when maxReceiveCount is 5), check for a misconfigured redrive policy or
a DLQ that is receiving messages from a different source.

### Step 3: Lambda concurrency throttling

```bash
# Event source mapping configuration
aws lambda get-event-source-mapping \
  --function-name <consumer-lambda> --output json | \
  jq '{BatchSize, MaximumBatchingWindowInSeconds, VisibilityTimeout,
       FunctionArn, State}'

# Lambda concurrency metrics
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Throttles \
  --dimensions Name=FunctionName,Value=<consumer-lambda> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json

aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name ConcurrentExecutions \
  --dimensions Name=FunctionName,Value=<consumer-lambda> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Maximum --output json
```

Check reserved concurrency:

```bash
aws lambda get-function-concurrency \
  --function-name <consumer-lambda> --output json
```

If `Throttles > 0` in the same window as DLQ growth, the Lambda is being
throttled. Messages are not processed within the visibility timeout,
the receive count increments, and messages move to the DLQ.

**Common throttle causes:**

| Pattern | Cause |
|---|---|
| Account-level concurrent executions at 1000 (default) | Account-level concurrency limit reached. Request a quota increase or optimize the consumer. |
| Reserved concurrency set to a low value (e.g., 10) | Intentionally low reserved concurrency. Raise it if the consumer can handle more. |
| Reserved concurrency set to 0 | The function is disabled for concurrent execution. This is a common mistake. |
| Another function in the account consuming all concurrency | A "noisy neighbor" function. Set reserved concurrency on the SQS consumer to guarantee floor. |

### Step 4: Visibility timeout exceeded

```bash
# Queue visibility timeout
aws sqs get-queue-attributes \
  --queue-url <source-queue-url> \
  --attribute-names VisibilityTimeout --output json

# Event source mapping visibility timeout (overrides queue for Lambda)
aws lambda get-event-source-mapping \
  --function-name <consumer-lambda> --output json | \
  jq '.VisibilityTimeout'
```

Compare against the consumer's processing time:

```bash
# Lambda consumer Duration
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=<consumer-lambda> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum,p99 --output json
```

If Lambda Duration p99 > VisibilityTimeout, the consumer is processing
messages that become visible again before completion. This causes:

1. Duplicate delivery (another consumer instance receives the same
   message).
2. Accelerated receive-count increment (each duplicate receive counts).
3. Premature DLQ migration (messages that would have succeeded if given
   more time).

**Rule of thumb:** VisibilityTimeout should be ≥ 6x the expected
processing time. This accounts for retries within the Lambda timeout and
batch processing overhead.

For Lambda consumers, set the visibility timeout on the event source
mapping:

```bash
aws lambda update-event-source-mapping \
  --uuid <mapping-uuid> \
  --visibility-timeout <seconds>
```

### Step 5: FIFO poison message — group stuck

```bash
# Check if the source queue is FIFO
aws sqs get-queue-attributes \
  --queue-url <source-queue-url> \
  --attribute-names FifoQueue --output json

# Inspect DLQ messages for a common MessageGroupId
aws sqs receive-message \
  --queue-url <dlq-url> \
  --max-number-of-messages 10 \
  --message-attribute-names All \
  --attribute-names All --output json | \
  jq '.Messages[] | {
    MessageId: .MessageId,
    MessageGroupId: .Attributes.MessageGroupId,
    ApproximateReceiveCount: .Attributes.ApproximateReceiveCount,
    Body: .Body[0:200]
  }'
```

If all DLQ messages share the same MessageGroupId, that group is the
stuck partition. The poison message (the one that first failed) is
likely in the DLQ or at the head of the source queue for that group.

**FIFO poison message diagnosis:**

1. Identify the stuck MessageGroupId (from DLQ messages or source queue
   inspection).
2. The message with the highest receive count in that group is the
   poison message.
3. If the poison message is in the DLQ: the group is unblocked (FIFO
   moves to the next message). If the group is still stuck, the NEXT
   message is also failing (same code bug).
4. If the poison message is still in the source queue (not yet at
   maxReceiveCount): the group is blocked until this message is
   processed or moved to the DLQ.

### Step 6: Message retention expired

```bash
aws sqs get-queue-attributes \
  --queue-url <source-queue-url> \
  --attribute-names MessageRetentionPeriod --output json
```

`MessageRetentionPeriod` is in seconds. Default: 345,600 (4 days). Max:
1,209,600 (14 days).

Check the age of the oldest message:

```bash
aws cloudwatch get-metric-statistics --namespace AWS/SQS \
  --metric-name ApproximateAgeOfOldestMessage \
  --dimensions Name=QueueName,Value=<queue-name> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Maximum --output json
```

If `ApproximateAgeOfOldestMessage` approaches or exceeds
`MessageRetentionPeriod`, messages are being silently deleted by SQS
before the consumer processes them. They never reach the DLQ because
retention expiry is a queue-level deletion, not a processing failure.

### Step 7: DLQ type mismatch

```bash
# Source queue type
aws sqs get-queue-attributes \
  --queue-url <source-queue-url> \
  --attribute-names FifoQueue --output json

# DLQ type
aws sqs get-queue-attributes \
  --queue-url <dlq-url> \
  --attribute-names FifoQueue --output json
```

| Source Queue | DLQ | Result |
|---|---|---|
| Standard | Standard | Correct |
| FIFO | FIFO (.fifo) | Correct |
| FIFO | Standard | WRONG — DLQ must be FIFO for a FIFO source |
| Standard | FIFO | WRONG — DLQ should be standard for a standard source |

A FIFO source queue with a standard DLQ causes:
- Message ordering loss (standard DLQ does not preserve FIFO order).
- StartMessageMoveTask failures when redriving (type mismatch between
  DLQ and source).
- Redrive policy validation errors in some configurations.

### Step 8: Redrive misconfigured

```bash
# Start a message move task
aws sqs start-message-move-task \
  --source-arn <dlq-arn> \
  --max-number-of-messages-per-second 50 \
  --output json

# Check task status (using the TaskHandle)
aws sqs describe-message-move-task \
  --task-handle <task-handle> --output json
```

Common redrive failures:

| `describe-message-move-task` status | Cause |
|---|---|
| `RUNNING` with `MessagesMoved: 0` | Destination queue is empty in the DLQ, OR the DLQ redrive-allow-policy does not permit the source queue. |
| `FAILED` | DLQ type mismatch, destination queue deleted, or permissions issue. |
| `COMPLETED` with `MessagesMoved` < expected | Some messages were deleted from the DLQ between task start and completion (retention expiry, manual purge). |
| `TaskHandle` not found | The task already completed or was cancelled. |

Check the DLQ's redrive-allow-policy:

```bash
aws sqs get-queue-attributes \
  --queue-url <dlq-url> \
  --attribute-names RedriveAllowPolicy --output json
```

The `RedriveAllowPolicy` controls which source queues can redrive from
this DLQ. If it is set to `allowAll: false` and does not list the source
queue ARN, redrive is blocked.

### Step 9: Visibility timeout reset — duplicate processing

Each `ReceiveMessage` call resets the visibility timeout for the
received message. If a consumer receives a message, processes it slowly,
and the visibility timeout expires, the message becomes visible again.
Another `ReceiveMessage` (from the same consumer or a different one)
resets the timer — but the first consumer may still be processing.

```bash
# Check for duplicate processing in Lambda logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/<consumer-lambda> \
  --start-time $(date -d '-1 hour' +%s)000 \
  --filter-pattern '"DUPLICATE" OR "already processed"' \
  --output json

# Check ApproximateReceiveCount on source queue messages
aws sqs receive-message \
  --queue-url <source-queue-url> \
  --max-number-of-messages 5 \
  --attribute-names ApproximateReceiveCount --output json | \
  jq '.Messages[] | {
    MessageId: .MessageId,
    ReceiveCount: .Attributes.ApproximateReceiveCount
  }'
```

A high `ApproximateReceiveCount` (3+) on source queue messages indicates
they have been received multiple times — the visibility timeout is
expiring before processing completes.

### Step 10: Message size limit

```bash
# Check message body size on DLQ messages
aws sqs receive-message \
  --queue-url <dlq-url> \
  --max-number-of-messages 5 \
  --attribute-names All --output json | \
  jq '.Messages[] | {
    MessageId: .MessageId,
    BodySize: (.Body | length)
  }'
```

SQS message body limit: 256 KB (262,144 bytes).

If messages approach or exceed this limit:
- Messages > 256 KB are rejected by `SendMessage` (they never enter the
  queue). If they are in the queue/DLQ, they were sent via the Extended
  Client Library (S3-backed).
- If the consumer does not use the Extended Client Library, it receives
  only the S3 pointer and cannot process the payload.

### Step 11: Batch receive failures

```bash
aws lambda get-event-source-mapping \
  --function-name <consumer-lambda> --output json | \
  jq '{BatchSize, FunctionResponseTypes, MaximumBatchingWindowInSeconds}'
```

For Lambda SQS triggers:
- `BatchSize`: 1-10,000 (default 10).
- `FunctionResponseTypes`: should include `ReportBatchItemFailures` for
  partial batch failure handling.
- Without `ReportBatchItemFailures`, a single bad record in a batch
  causes the ENTIRE batch to retry — all 10 messages increment their
  receive count.

If the consumer does not implement `ReportBatchItemFailures`:
- One poison message in a batch of 10 causes all 10 messages to retry.
- The receive count for all 10 increments on each batch retry.
- 9 perfectly good messages reach the DLQ alongside the 1 poison
  message.

