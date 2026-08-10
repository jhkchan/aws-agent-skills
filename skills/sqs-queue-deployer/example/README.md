# End-to-End Example: SQS Queue Deployment

A walkthrough showing how to use the `sqs-queue-deployer` skill from
invocation through verification. Mirrors the structured-eval pattern of
shipping a concrete worked example per skill.

---

## Scenario

You are deploying a production SQS queue that receives S3 Event
Notifications when orders are uploaded, processes them with a Lambda
function, and needs a dead-letter queue for poison-pill messages. The
queue requires:

- Standard queue type (at-least-once delivery, unlimited throughput)
- Dead-letter queue (DLQ) with maxReceiveCount=5 and 14-day retention
- Visibility timeout tuned for the Lambda consumer (p99 ~8 seconds)
- Long polling (20 seconds) to reduce empty receives
- SSE-SQS encryption (free, FIPS-validated)
- S3 Event Notification access policy (Principal:* + aws:SourceArn)
- Lambda partial batch responses (ReportBatchItemFailures)

Queue name: `order-events`
Region: `us-east-1`
Account: `111111111111`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-sqs-queue
```

Then paste the queue requirements.

### Option B: Natural language

```
You: "Deploy a production SQS queue named order-events in us-east-1.
      It receives messages from S3 bucket order-uploads via S3 Event
      Notification. Lambda function order-processor consumes it (p99 ~8s).
      DLQ order-events-dlq with maxReceiveCount=5, 14-day retention.
      SSE-SQS encryption. Long polling. Account: 111111111111."
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

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

---

## Step 3 — Deployment commands

The skill generates the CLI sequence (from
`references/deployment-cli-commands.md`):

```bash
# Step 1: Create the DLQ (14-day retention, SSE-SQS)
aws sqs create-queue \
  --queue-name order-events-dlq \
  --attributes MessageRetentionPeriod=1209600,SqsManagedSseEnabled=true

DLQ_URL=$(aws sqs get-queue-url --queue-name order-events-dlq --output text)
DLQ_ARN=$(aws sqs get-queue-attributes \
  --queue-url "$DLQ_URL" \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' --output text)

# Step 2: Create the source queue with redrive policy + SSE-SQS + long polling
aws sqs create-queue \
  --queue-name order-events \
  --attributes \
    VisibilityTimeout=60,\
    MessageRetentionPeriod=345600,\
    ReceiveMessageWaitTimeSeconds=20,\
    SqsManagedSseEnabled=true,\
    RedrivePolicy="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"5\"}"

QUEUE_URL=$(aws sqs get-queue-url --queue-name order-events --output text)

# Step 3: S3 Event Notification access policy (Principal:* + aws:SourceArn)
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
        "ArnEquals": { "aws:SourceArn": "arn:aws:s3:::order-uploads" }
      }
    }]
  }'

# Step 4: Lambda event source mapping with partial batch responses
aws lambda create-event-source-mapping \
  --function-name order-processor \
  --event-source-arn arn:aws:sqs:us-east-1:111111111111:order-events \
  --batch-size 10 \
  --maximum-batching-window-in-seconds 5 \
  --visibility-timeout 300 \
  --function-response-types ReportBatchItemFailures

# Step 5: S3 Event Notification to SQS
aws s3api put-bucket-notification-configuration \
  --bucket order-uploads \
  --notification-configuration '{
    "QueueConfigurations": [{
      "QueueArn": "arn:aws:sqs:us-east-1:111111111111:order-events",
      "Events": ["s3:ObjectCreated:*"]
    }]
  }'
```

---

## Step 4 — Post-deployment verification

```bash
# All queue attributes
aws sqs get-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attribute-names All --output json

# Verify redrive policy (DLQ ARN + maxReceiveCount)
aws sqs get-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attribute-names RedrivePolicy --output text

# Verify encryption
aws sqs get-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attribute-names SqsManagedSseEnabled --output text

# Test send + receive
aws sqs send-message \
  --queue-url "$QUEUE_URL" \
  --message-body '{"test": true}'
aws sqs receive-message \
  --queue-url "$QUEUE_URL" \
  --wait-time-seconds 5
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| DLQ retention | Default 4 days | 14 days (1209600) | Operations needs time to analyse and replay failed messages. 4 days misses weekends. |
| Visibility timeout | Default 30s | 60s (>= Lambda p99) | If visibility timeout < consumer p99, messages return before processing completes, causing duplicate processing. |
| Long polling | Default 0s (short) | 20 seconds | Short polling returns immediately on empty queues — each empty ReceiveMessage is billed. Long polling reduces cost ~95%. |
| SSE-SQS encryption | Not set | SqsManagedSseEnabled=true | SSE-SQS is free, FIPS-validated, satisfies SOC2/PCI-DSS/HIPAA. No reason to run unencrypted. |
| S3 access policy | Missing aws:SourceArn | Principal:* + aws:SourceArn | Without the condition, any account can send messages (data poisoning). aws:SourceArn is set by the S3 service layer and cannot be forged. |
| Lambda partial batch | Not configured | ReportBatchItemFailures | Without partial batch responses, if one message in a batch fails, the entire batch is retried — causing reprocessing of successfully handled messages. |
| DLQ type check | N/A | Verified Standard DLQ for Standard queue | A Standard DLQ for a FIFO source silently drops redriven messages. The type MUST match. |

---

## Related artifacts

- **Skill definition:** `skills/sqs-queue-deployer/SKILL.md`
- **Configuration guide:** `skills/sqs-queue-deployer/references/queue-configuration-guide.md`
- **Deployment CLI commands:** `skills/sqs-queue-deployer/references/deployment-cli-commands.md`
- **Slash command:** `commands/aws/deploy-sqs-queue.md`
- **Eval suite:** `skills/sqs-queue-deployer/evals/evals.json`
- **Legacy test cases:** `skills/sqs-queue-deployer/eval/test-cases.yaml`
