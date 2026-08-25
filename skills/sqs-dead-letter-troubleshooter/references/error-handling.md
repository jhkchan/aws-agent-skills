# Error handling - SQS Dead-Letter Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Remediation guidance

### For MAX_RECEIVE_COUNT_TOO_LOW

```bash
aws sqs set-queue-attributes \
  --queue-url <source-queue-url> \
  --attributes '{"RedrivePolicy":"{\"deadLetterTargetArn\":\"<dlq-arn>\",\"maxReceiveCount\":\"5\"}"}'
```

Raise maxReceiveCount to 3-5 for consumers with transient failures.
Consider higher values (10+) only if failures are genuinely transient
and the consumer is idempotent.

### For VISIBILITY_TIMEOUT_EXCEEDED

```bash
# Queue-level
aws sqs set-queue-attributes \
  --queue-url <source-queue-url> \
  --attributes VisibilityTimeout=300

# Event source mapping (for Lambda consumers)
aws lambda update-event-source-mapping \
  --uuid <mapping-uuid> \
  --visibility-timeout 300
```

Target: VisibilityTimeout ≥ 6x consumer p99 processing time.

### For FIFO_POISON_MESSAGE

1. Identify the poison message in the DLQ or source queue.
2. If in the DLQ: the group is unblocked; fix the consumer to handle the
   payload shape, then optionally redrive.
3. If still in the source queue: let it reach maxReceiveCount and move
   to the DLQ, or manually delete it if the consumer cannot process it.
4. Implement `ReportBatchItemFailures` to isolate bad records in future.

### For DLQ_TYPE_MISMATCH

Create a FIFO DLQ and update the source queue's RedrivePolicy:

```bash
# Create FIFO DLQ
aws sqs create-queue \
  --queue-name <new-dlq>.fifo \
  --attributes FifoQueue=true --output json

# Update RedrivePolicy on the source FIFO queue
aws sqs set-queue-attributes \
  --queue-url <source-fifo-queue-url> \
  --attributes '{"RedrivePolicy":"{\"deadLetterTargetArn\":\"<new-fifo-dlq-arn>\",\"maxReceiveCount\":\"5\"}"}'
```

### For REDRIVE_MISCONFIGURED

```bash
# Redrive from DLQ to source using v2 API
aws sqs start-message-move-task \
  --source-arn <dlq-arn> \
  --destination-arn <source-queue-arn> \
  --max-number-of-messages-per-second 50 \
  --output json

# Check status
aws sqs describe-message-move-task \
  --task-handle <task-handle> --output json
```

### For LAMBDA_CONCURRENCY_THROTTLE

```bash
# Raise reserved concurrency
aws lambda put-function-concurrency \
  --function-name <consumer-lambda> \
  --reserved-concurrent-executions <new-value>
```

Verify the account-level concurrency limit supports the new value.

### For MESSAGE_RETENTION_EXPIRED

```bash
aws sqs set-queue-attributes \
  --queue-url <source-queue-url> \
  --attributes MessageRetentionPeriod=1209600
```

Max: 1,209,600 seconds (14 days). Also scale the consumer to drain the
backlog.

### For BATCH_RECEIVE_FAILURE

Implement `ReportBatchItemFailures` in the Lambda consumer and update
the event source mapping:

```bash
aws lambda update-event-source-mapping \
  --uuid <mapping-uuid> \
  --function-response-types '["ReportBatchItemFailures"]'
```

### For VISIBILITY_TIMEOUT_RESET

Same as VISIBILITY_TIMEOUT_EXCEEDED — raise the timeout on both the
queue and event source mapping. Ensure the consumer is idempotent.

### For MESSAGE_SIZE_LIMIT

Use the SQS Extended Client Library (Java, Python) for payloads > 256
KB, or reduce payload size by offloading large data to S3 and passing a
reference.

