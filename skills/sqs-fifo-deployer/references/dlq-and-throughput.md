# DLQ and Throughput — SQS FIFO Deployer

Deep reference on FIFO DLQ configuration (FIFO DLQ requirement,
redrive policy, maxReceiveCount tuning, StartMessageMoveTask for
redrive), high-throughput FIFO mode (quota caveats, pricing
differences, dedup scope change), and visibility timeout tuning.
Loaded on demand by the skill — kept out of the main SKILL.md
body so the provisioning procedure stays scannable.

## FIFO DLQ configuration

### The FIFO DLQ requirement

The DLQ for a FIFO queue MUST also be a FIFO queue. This is a hard
requirement — the API rejects a redrive policy that points to a
Standard queue when the main queue is FIFO.

```bash
# Create FIFO DLQ first
DLQ_URL=$(aws sqs create-queue \
  --queue-name "order-processing-dlq.fifo" \
  --attributes "FifoQueue=true" \
  --query 'QueueUrl' --output text)

DLQ_ARN=$(aws sqs get-queue-attributes \
  --queue-url "$DLQ_URL" \
  --attribute-names "QueueArn" \
  --query 'Attributes.QueueArn' --output text)
```

### Attaching the redrive policy

```bash
aws sqs set-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attributes "RedrivePolicy={\"deadLetterTargetArn\":\"${DLQ_ARN}\",\"maxReceiveCount\":\"5\"}"
```

### maxReceiveCount tuning

The `maxReceiveCount` determines how many times a message is
received (and not deleted) before it is moved to the DLQ. This
should be tuned based on the failure mode:

| Failure mode | Recommended maxReceiveCount | Rationale |
|---|---|---|
| Transient errors (network, timeout) | 5-10 | Retry a few times before giving up |
| Poison pill messages (bad format) | 3 | Don't retry too many times — the message will never succeed |
| Unknown / mixed failures | 5 | Balanced default |
| High-throughput with quick failures | 3 | Fail fast to avoid throughput bottleneck |

### Verifying the redrive policy

```bash
aws sqs get-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attribute-names "RedrivePolicy" \
  --query 'Attributes.RedrivePolicy' --output text | jq .
```

### StartMessageMoveTask — modern DLQ redrive

The `StartMessageMoveTask` API moves messages from a DLQ back to
the source queue. It replaces custom Lambda-based redrive patterns.

```bash
# Move all messages from DLQ back to source queue
TASK_HANDLE=$(aws sqs start-message-move-task \
  --source-arn "$DLQ_ARN" \
  --destination-arn "$SOURCE_QUEUE_ARN" \
  --query 'TaskHandle' --output text)

# Check task status
aws sqs describe-message-move-task \
  --source-arn "$DLQ_ARN" \
  --max-number-of-results 1
```

**Key:** `StartMessageMoveTask` preserves message attributes and
metadata. It also supports partial moves (via
`MaxNumberOfMessagesPerSecond` for rate limiting).

## High-throughput FIFO mode

### Enabling high-throughput

High-throughput FIFO requires setting BOTH attributes together:

```bash
aws sqs create-queue \
  --queue-name "high-throughput.fifo" \
  --attributes "FifoQueue=true,DeduplicationScope=messageGroup,ThroughputLimit=messagesPerGroupId"
```

Setting only one attribute results in an API error:
`InvalidAttributeName: You must set both DeduplicationScope and ThroughputLimit.`

### Throughput comparison

```text
Standard FIFO (perQueue):
  Limit: 300 TPS per API action (shared across ALL message groups)
  With batching: up to 3,000 messages/sec (10 messages per batch)
  Scaling: does NOT scale with more message groups

High-throughput FIFO (messagesPerGroupId):
  Limit: 300 TPS per API action PER message group
  With 10 active groups: up to 3,000 TPS (10 × 300)
  With 100 active groups: up to 30,000 TPS
  Scaling: scales linearly with active message group count
```

### Quota caveats

1. **Account-level quota:** high-throughput FIFO queues count
   against a separate quota. The default is 100 high-throughput
   FIFO queues per account (soft limit). Request a quota increase
   via Service Quotas if needed.

2. **Cost difference:** high-throughput FIFO API requests are billed
   at a higher rate than standard FIFO. Monitor costs when switching.
   The pricing difference is approximately 1.5x per million requests
   (check current AWS pricing for exact rates).

3. **Dedup scope change:** deduplication moves from queue-level to
   group-level. The same dedup ID in different groups will NOT be
   deduplicated. Evaluate whether per-group dedup is semantically
   correct for your use case.

4. **No partial migration:** you cannot switch an existing queue
   between standard and high-throughput mode by changing attributes.
   You must create a new queue with the desired attributes and
   migrate producers/consumers.

### When to use high-throughput

| Scenario | Use high-throughput? | Why |
|---|---|---|
| < 300 TPS total | No | Standard FIFO handles this |
| 300-3000 TPS, many groups | Yes | Per-group scaling provides headroom |
| Global ordering required | No | Single group limits to 300 TPS even in high-throughput |
| Cost-sensitive, < 300 TPS | No | High-throughput has higher per-request cost |
| Per-entity ordering, many entities | Yes | Each entity gets its own group and throughput allocation |

## Visibility timeout tuning

### Queue-level visibility timeout

Set at queue creation or via `set-queue-attributes`:

```bash
aws sqs set-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attributes "VisibilityTimeout=120"
```

### Per-message visibility timeout

Adjust on a specific received message using
`change-message-visibility`:

```bash
aws sqs change-message-visibility \
  --queue-url "$QUEUE_URL" \
  --receipt-handle "<receipt-handle>" \
  --visibility-timeout 300
```

### Tuning guidelines

The visibility timeout should be set to at LEAST 2x the expected
consumer processing time. This provides a safety margin.

```text
Consumer processing time → Recommended visibility timeout:
  5 seconds    → 30 seconds (6x — for fast consumers)
  10 seconds   → 60 seconds (6x — for moderate consumers)
  30 seconds   → 120 seconds (4x)
  60 seconds   → 300 seconds (5x — for slow consumers)
  5 minutes    → 600 seconds (2x — for batch consumers)
```

### Visibility timeout too low

If the visibility timeout is too low, the consumer may not finish
processing before the timeout expires. The message becomes visible
again and another consumer picks it up — causing duplicate
processing.

**Symptoms:**
- Messages processed multiple times (duplicate side effects)
- Messages in the DLQ that should have succeeded
- Consumer logs show the same message ID processed by multiple
  consumers

**Fix:** increase the visibility timeout. If the consumer needs more
time for a specific message, use `change-message-visibility` to
extend it dynamically.

### Visibility timeout too high

If the visibility timeout is too high, failed messages take a long
time to become visible again for retry.

**Symptoms:**
- Consumer crashes → message invisible for a long time before retry
- DLQ takes too long to catch poison pill messages

**Fix:** reduce the visibility timeout. Use
`change-message-visibility` to extend for legitimate long-running
processing.

## Terraform examples

```hcl
# High-throughput FIFO queue with DLQ and SSE-KMS
resource "aws_sqs_queue" "dlq" {
  name       = "events-dlq.fifo"
  fifo_queue = true
}

resource "aws_sqs_queue" "main" {
  name                        = "events.fifo"
  fifo_queue                  = true
  deduplication_scope         = "messageGroup"
  throughput_limit            = "messagesPerGroupId"
  visibility_timeout_seconds  = 120
  kms_master_key_id           = aws_kms_key.sqs.arn
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 5
  })

  tags = {
    Environment = "production"
  }
}

# Cross-account access policy
data "aws_iam_policy_document" "queue_policy" {
  statement {
    effect    = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::999999999999:role/ProducerRole"]
    }
    actions   = ["sqs:SendMessage", "sqs:GetQueueUrl"]
    resources = [aws_sqs_queue.main.arn]
  }
}

resource "aws_sqs_queue_policy" "main" {
  queue_url = aws_sqs_queue.main.url
  policy    = data.aws_iam_policy_document.queue_policy.json
}
```
