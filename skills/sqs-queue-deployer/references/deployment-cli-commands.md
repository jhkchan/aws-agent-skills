# Deployment CLI Commands — SQS Queue Deployer

Full copy-pasteable CLI command sequence for all 10 deployment steps.
Variables to substitute: `<name>`, `<region>`, `<account-id>`,
`<queue-type>`, `<dlq-name>`, `<kms-key-id>`, `<bucket-arn>`.

## Step 0: Prerequisites check

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

# Confirm queue name is available
aws sqs get-queue-url --queue-name <name> 2>&1 || echo "Name is available"
```

## Step 1: Create the queue

```bash
# Standard queue
aws sqs create-queue \
  --queue-name order-events \
  --attributes file://attributes-standard.json

# FIFO queue (name MUST end in .fifo)
aws sqs create-queue \
  --queue-name order-events.fifo \
  --attributes file://attributes-fifo.json
```

**attributes-standard.json:**

```json
{
  "VisibilityTimeout": "60",
  "MessageRetentionPeriod": "345600",
  "ReceiveMessageWaitTimeSeconds": "20",
  "SqsManagedSseEnabled": "true"
}
```

**attributes-fifo.json:**

```json
{
  "FifoQueue": "true",
  "ContentBasedDeduplication": "true",
  "VisibilityTimeout": "120",
  "MessageRetentionPeriod": "604800",
  "ReceiveMessageWaitTimeSeconds": "20",
  "SqsManagedSseEnabled": "true"
}
```

## Step 2: Create the DLQ

```bash
# Standard DLQ
aws sqs create-queue \
  --queue-name order-events-dlq \
  --attributes MessageRetentionPeriod=1209600,SqsManagedSseEnabled=true

# FIFO DLQ (for FIFO source queue)
aws sqs create-queue \
  --queue-name order-events-dlq.fifo \
  --attributes FifoQueue=true,MessageRetentionPeriod=1209600,SqsManagedSseEnabled=true
```

## Step 3: Set the redrive policy

```bash
DLQ_URL=$(aws sqs get-queue-url --queue-name order-events-dlq --output text)
DLQ_ARN=$(aws sqs get-queue-attributes \
  --queue-url "$DLQ_URL" \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' --output text)

QUEUE_URL=$(aws sqs get-queue-url --queue-name order-events --output text)

aws sqs set-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attributes RedrivePolicy="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"5\"}"
```

## Step 4: Configure encryption

```bash
# SSE-SQS (free, recommended default)
aws sqs set-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attributes SqsManagedSseEnabled=true

# SSE-KMS (customer-managed key)
aws sqs set-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attributes KmsMasterKeyId=alias/my-sqs-key,KmsDataKeyReusePeriodSeconds=300
```

## Step 5: Set the access policy (if cross-service or cross-account)

### S3 Event Notification pattern

```bash
aws sqs set-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attributes Policy='{
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
  }'
```

### SNS subscription pattern

```bash
aws sqs set-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attributes Policy='{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": "*",
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:us-east-1:111111111111:order-events",
      "Condition": {
        "ArnEquals": { "aws:SourceArn": "arn:aws:sns:us-east-1:111111111111:my-topic" }
      }
    }]
  }'
```

### Cross-account producer

```bash
aws sqs set-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attributes Policy='{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::222222222222:root" },
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:us-east-1:111111111111:order-events"
    }]
  }'
```

## Step 6: Configure Lambda event source mapping (if Lambda consumer)

### With partial batch responses

```bash
aws lambda create-event-source-mapping \
  --function-name order-processor \
  --event-source-arn arn:aws:sqs:us-east-1:111111111111:order-events \
  --batch-size 10 \
  --maximum-batching-window-in-seconds 5 \
  --visibility-timeout 300 \
  --function-response-types ReportBatchItemFailures
```

### Without partial batch responses (legacy)

```bash
aws lambda create-event-source-mapping \
  --function-name order-processor \
  --event-source-arn arn:aws:sqs:us-east-1:111111111111:order-events \
  --batch-size 10 \
  --maximum-batching-window-in-seconds 5 \
  --visibility-timeout 300
```

## Step 7: High-throughput FIFO (optional)

```bash
aws sqs create-queue \
  --queue-name ht-orders.fifo \
  --attributes \
    FifoQueue=true,\
    ContentBasedDeduplication=true,\
    FifoThroughputLimit=perMessageGroupId,\
    DeduplicationScope=messageGroup,\
    VisibilityTimeout=300,\
    ReceiveMessageWaitTimeSeconds=20,\
    SqsManagedSseEnabled=true
```

## Step 8: Verification

```bash
# All attributes
aws sqs get-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attribute-names All --output json

# Redrive policy
aws sqs get-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attribute-names RedrivePolicy --output text

# Encryption
aws sqs get-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attribute-names SqsManagedSseEnabled,KmsMasterKeyId --output json

# Access policy
aws sqs get-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attribute-names Policy --output json

# Test send + receive (standard)
aws sqs send-message \
  --queue-url "$QUEUE_URL" \
  --message-body '{"test": true}'
aws sqs receive-message \
  --queue-url "$QUEUE_URL" \
  --wait-time-seconds 5

# Test send (FIFO — requires MessageGroupId)
aws sqs send-message \
  --queue-url "$FIFO_QUEUE_URL" \
  --message-body '{"test": true}' \
  --message-group-id "test-group"
```

## Step 9: Redrive from DLQ (when needed)

```bash
# Move messages from DLQ back to source queue (async, rate-limited)
aws sqs start-message-move-task \
  --source-arn arn:aws:sqs:us-east-1:111111111111:order-events-dlq \
  --destination-arn arn:aws:sqs:us-east-1:111111111111:order-events

# Check task status
aws sqs list-message-move-tasks \
  --source-arn arn:aws:sqs:us-east-1:111111111111:order-events-dlq
```

## CloudWatch alarms (recommended post-deployment)

```bash
QUEUE_URL=$(aws sqs get-queue-url --queue-name order-events --output text)
DLQ_URL=$(aws sqs get-queue-url --queue-name order-events-dlq --output text)

# Alarm: messages in DLQ (poison pill detected)
aws cloudwatch put-metric-alarm \
  --alarm-name "sqs-order-events-dlq-messages" \
  --metric-name ApproximateNumberOfMessagesVisible \
  --namespace AWS/SQS \
  --statistic Sum \
  --period 300 \
  --threshold 0 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=QueueName,Value=order-events-dlq \
  --evaluation-periods 1 \
  --alarm-actions <sns-topic-arn>

# Alarm: oldest message too old (consumer lag)
aws cloudwatch put-metric-alarm \
  --alarm-name "sqs-order-events-old-messages" \
  --metric-name ApproximateAgeOfOldestMessage \
  --namespace AWS/SQS \
  --statistic Maximum \
  --period 300 \
  --threshold 3600 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=QueueName,Value=order-events \
  --evaluation-periods 2 \
  --alarm-actions <sns-topic-arn>
```
