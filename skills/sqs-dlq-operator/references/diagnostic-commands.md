# Diagnostic commands - SQS DLQ Operator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Common DLQ patterns (boilerplate)

### Create Standard DLQ + wire redrive policy

```bash
# 1. Create the DLQ (Standard, 14-day retention, SSE-SQS)
aws sqs create-queue \
  --queue-name prod-orders-dlq \
  --attributes MessageRetentionPeriod=1209600,SqsManagedSseEnabled=true

DLQ_URL=$(aws sqs get-queue-url --queue-name prod-orders-dlq --query 'QueueUrl' --output text)
DLQ_ARN=$(aws sqs get-queue-attributes --queue-url "$DLQ_URL" \
  --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)

# 2. Wire the redrive policy on the SOURCE queue
SOURCE_URL=$(aws sqs get-queue-url --queue-name prod-orders --query 'QueueUrl' --output text)
aws sqs set-queue-attributes \
  --queue-url "$SOURCE_URL" \
  --attributes RedrivePolicy="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"5\"}"
```

### Create FIFO DLQ (for FIFO source)

```bash
# FIFO DLQ — name MUST end in .fifo
aws sqs create-queue \
  --queue-name prod-orders-dlq.fifo \
  --attributes FifoQueue=true,MessageRetentionPeriod=1209600,SqsManagedSseEnabled=true

# Verify the DLQ ARN ends in .fifo before wiring the source
DLQ_ARN=$(aws sqs get-queue-attributes --queue-url "$DLQ_URL" \
  --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)
# DLQ_ARN should be: arn:aws:sqs:us-east-1:111111111111:prod-orders-dlq.fifo
```

### Tune maxReceiveCount

```bash
# Snapshot first
aws sqs get-queue-attributes --queue-url "$SOURCE_URL" \
  --attribute-names RedrivePolicy --output json > /tmp/source-redrive-backup-$(date +%s).json

# Update with new maxReceiveCount (preserving the DLQ ARN)
aws sqs set-queue-attributes \
  --queue-url "$SOURCE_URL" \
  --attributes RedrivePolicy="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"10\"}"
```

### Analyze DLQ messages (receive without deleting)

```bash
# Receive up to 10 messages from the DLQ for inspection (DO NOT delete yet)
aws sqs receive-message \
  --queue-url "$DLQ_URL" \
  --max-number-of-messages 10 \
  --visibility-timeout 300 \
  --attribute-names All \
  --message-attribute-names All \
  --output json

# Key attributes to inspect:
# - ApproximateReceiveCount: how many times the source redelivered before DLQ
# - ApproximateFirstReceiveTimestamp: when the message first entered the DLQ
# - MessageDeduplicationId (FIFO): for dedup analysis
# - Body: parse for poison-pill indicators (malformed JSON, missing fields)
```

### Replay via StartMessageMoveTask (2022+ API)

```bash
# Pre-replay snapshot of DLQ depth
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=prod-orders-dlq \
  --start-time 2026-08-11T00:00:00Z --end-time 2026-08-11T01:00:00Z \
  --period 300 --statistics Average

# Start the move task (asynchronous)
TASK_ID=$(aws sqs start-message-move-task \
  --source-arn "$DLQ_ARN" \
  --destination-arn "$SOURCE_ARN" \
  --max-number-of-messages-per-second 100 \
  --query 'TaskHandle' --output text)

# Poll task status (initial: RUNNING, final: COMPLETED or FAILED)
aws sqs list-message-move-tasks \
  --source-arn "$DLQ_ARN" \
  --max-results 10

# Post-replay: verify DLQ depth returned to zero
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=prod-orders-dlq \
  --start-time $(date -u -d '15 min ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Average
```

**`MaxNumberOfMessagesPerSecond`:** set to a value the consumer can
sustain. Default is unlimited — for a DLQ with 100k messages and a
Lambda consumer with 50 concurrent executions, unlimited replay will
throttle the consumer and re-trigger the original failure mode. Start
with `100` (360k/hour) and increase if the consumer keeps up.

### Enable partial batch responses (prevent false-positive DLQ)

```bash
# Update the Lambda event source mapping to report per-message failures
aws lambda update-event-source-mapping \
  --uuid <mapping-uuid> \
  --function-response-types ReportBatchItemFailures

# Verify
aws lambda get-event-source-mapping \
  --uuid <mapping-uuid> \
  --query 'FunctionResponseTypes'
```

Without `ReportBatchItemFailures`, a single failed message in a batch
of 10 causes all 10 to retry. With it, only the failed message retries.

