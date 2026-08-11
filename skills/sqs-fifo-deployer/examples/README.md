# End-to-End Example: SQS FIFO Queue Deployment

A walkthrough showing how to use the `sqs-fifo-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an SQS FIFO queue for order processing with
content-based deduplication, a FIFO DLQ with redrive policy, SSE-KMS
encryption, and cross-account delivery. The queue needs:

- Queue name: order-processing.fifo
- Deduplication: content-based
- Message group strategy: per-entity (customer ID)
- Visibility timeout: 120 seconds (consumer processing ~60s)
- DLQ: order-processing-dlq.fifo (maxReceiveCount=5)
- SSE-KMS: customer-managed key
- Cross-account delivery: producer account 999999999999
- Tags: Environment=production, Application=order-service

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-sqs-fifo
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create an SQS FIFO queue for order processing with
      content-based deduplication, a DLQ with maxReceiveCount 5,
      SSE-KMS encryption, and cross-account delivery from
      account 999999999999."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create an sqs fifo queue"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
SQS_FIFO: order-processing.fifo (https://sqs.us-east-1.amazonaws.com/123456789012/order-processing.fifo)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Queue name: order-processing.fifo
  [✓] FifoQueue: true (immutable)
  [✓] ContentBasedDeduplication: true
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

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the FIFO DLQ first
DLQ_URL=$(aws sqs create-queue \
  --queue-name "order-processing-dlq.fifo" \
  --attributes "FifoQueue=true" \
  --query 'QueueUrl' --output text)

DLQ_ARN=$(aws sqs get-queue-attributes \
  --queue-url "$DLQ_URL" \
  --attribute-names "QueueArn" \
  --query 'Attributes.QueueArn' --output text)

# Step 2: Create the main FIFO queue with dedup, SSE-KMS, and redrive
QUEUE_URL=$(aws sqs create-queue \
  --queue-name "order-processing.fifo" \
  --attributes "FifoQueue=true,ContentBasedDeduplication=true,VisibilityTimeout=120,KmsMasterKeyId=arn:aws:kms:us-east-1:123456789012:key/abc123,RedrivePolicy={\"deadLetterTargetArn\":\"${DLQ_ARN}\",\"maxReceiveCount\":\"5\"}" \
  --query 'QueueUrl' --output text)

# Step 3: Set cross-account access policy
QUEUE_ARN=$(aws sqs get-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attribute-names "QueueArn" \
  --query 'Attributes.QueueArn' --output text)

POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::999999999999:role/OrderProducerRole"
      },
      "Action": ["sqs:SendMessage", "sqs:GetQueueUrl"],
      "Resource": "${QUEUE_ARN}"
    }
  ]
}
EOF
)

aws sqs set-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attributes "Policy=$(echo $POLICY | jq -sR .)"
```

---

## Step 4 — Post-deployment verification

```bash
# Verify main queue attributes
aws sqs get-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attribute-names "QueueArn,FifoQueue,ContentBasedDeduplication,VisibilityTimeout,RedrivePolicy,KmsMasterKeyId,Policy"

# Verify DLQ attributes
aws sqs get-queue-attributes \
  --queue-url "$DLQ_URL" \
  --attribute-names "QueueArn,FifoQueue"

# Test cross-account send (from producer account)
aws sqs send-message \
  --queue-url "$QUEUE_URL" \
  --message-body '{"orderId": "test-001"}' \
  --message-group-id "customer-123"
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Queue name suffix | Missing .fifo suffix | .fifo suffix enforced | FIFO queues MUST have .fifo suffix |
| DLQ type | Standard DLQ attached | FIFO DLQ attached | Standard DLQ rejected for FIFO queues |
| Message group strategy | Single group ("all") | Per-entity (customer ID) | Single group serializes everything |
| Visibility timeout | Default 30s | 120s (2x processing time) | Too low causes duplicate processing |
| Cross-account access | Missing access policy | Access policy + KMS key policy | Both sides must be configured |
| Deduplication | No dedup method | Content-based or explicit dedup ID | FIFO queues require dedup |

---

## Related artifacts

- **Skill definition:** `skills/sqs-fifo-deployer/SKILL.md`
- **Deduplication and ordering guide:** `skills/sqs-fifo-deployer/references/deduplication-and-ordering.md`
- **DLQ and throughput guide:** `skills/sqs-fifo-deployer/references/dlq-and-throughput.md`
- **Slash command:** `commands/aws/deploy-sqs-fifo.md`
- **Eval suite:** `skills/sqs-fifo-deployer/evals/evals.json`
- **Legacy test cases:** `skills/sqs-fifo-deployer/eval/test-cases.yaml`
