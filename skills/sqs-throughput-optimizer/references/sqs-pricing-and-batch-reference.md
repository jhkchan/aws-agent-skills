# SQS Pricing and Batch API Reference

Supplementary reference for the SQS Throughput Optimizer skill. Loaded on-
demand when detailed pricing math, batch API payload limits, FIFO
high-throughput mode configuration, or KMS cost calculations are needed.

## SQS pricing (us-east-1, 2026, USD)

### Request pricing

| API category | $/1M requests | Notes |
|---|---|---|
| All SQS API requests | $0.40 | SendMessage, ReceiveMessage, DeleteMessage, SendMessageBatch, DeleteMessageBatch, ChangeMessageVisibilityBatch — all cost the same per API call |
| First 1M requests/month | Free | Free tier (applies across all SQS queues in the account) |

### Key pricing insight

A `SendMessageBatch` call with 10 messages costs the same as a single
`SendMessage` call. The batch API is 10x cheaper per message.

### FIFO vs Standard — no price difference

Both queue types charge $0.40/1M requests. FIFO high-throughput mode
does NOT add cost — it is a free configuration change.

### Free tier

- 1,000,000 SQS requests/month free (across all queues in the account,
  Standard and FIFO combined)
- Free tier applies to the first 1M only; all subsequent requests are
  billed at $0.40/1M

## Throughput limits by queue type

### Standard queue

| Dimension | Limit | Notes |
|---|---|---|
| API actions per second (per queue) | 3,000 (default) | Can be raised via quota increase request |
| Maximum in-flight messages | 120,000 | Messages being received but not yet deleted |
| Batch size (ReceiveMessage) | 10 | Hard cap per API call |

### FIFO queue (default mode)

| Dimension | Limit | Notes |
|---|---|---|
| Transactions per second (per queue) | 300 | Applies at the queue level |
| Batch transactions per second | 3,000 | 300 TX/s × 10 messages/batch |
| Per MessageGroupId | 300 TX/s | Groups are throttled independently |

### FIFO queue (high-throughput mode)

| Dimension | Limit | Notes |
|---|---|---|
| Transactions per second (per MessageGroupId) | 300 | Same per-group limit |
| Batch transactions per second (per MessageGroupId) | 9,000 | Raised from 3,000 to 9,000 |
| Queue-level aggregate | Up to 9,000 × number of active MessageGroupIds | Effectively unlimited for well-partitioned workloads |

**Enabling high-throughput mode requires BOTH attributes:**
```
DeduplicationScope=MessageGroup
ThroughputLimit=PerMessageGroupId
```

Setting only one without the other does NOT activate high-throughput mode.

## Batch API payload limits

| Batch API | Max messages | Max total payload | Notes |
|---|---|---|---|
| SendMessageBatch | 10 | 256 KB | Payload includes all message bodies + attributes |
| DeleteMessageBatch | 10 | 256 KB | Payload includes receipt handles |
| ChangeMessageVisibilityBatch | 10 | 256 KB | Payload includes receipt handles + timeout values |
| ReceiveMessage (single call) | 10 | 256 KB per message | Max 10 messages returned per call |

**Payload math:** 10 messages × 25.6 KB each = 256 KB (fits). 10
messages × 30 KB each = 300 KB (EXCEEDS 256 KB cap — batch fails).

## SSE-KMS cost calculation

Each SQS API call on a KMS-encrypted queue triggers one
`kms:GenerateDataKey` call.

| KMS pricing component | Cost | Notes |
|---|---|---|
| GenerateDataKey (customer managed key) | $0.03 / 10,000 calls | Applies per SQS API request |
| KMS key monthly fee | $1.00 / key / month | Per customer managed key |
| AWS managed key (aws/sqs) | $1.00 / key / month | Automatically provisioned |

**KMS cost at scale:**
```
monthly_kms_cost = (total_sqs_requests / 10,000) × $0.03 + $1.00

Example: 10M SQS requests/month
  KMS data key cost: 10,000,000 / 10,000 × $0.03 = $30.00
  KMS key monthly: $1.00
  Total KMS overhead: $31.00/month
  SQS request cost: 10,000,000 / 1,000,000 × $0.40 = $4.00
  KMS cost is 7.75× the SQS cost itself.
```

## Regional pricing multipliers (selected)

| Region | Multiplier | $/1M requests |
|---|---|---|
| us-east-1 (N. Virginia) | 1.00× | $0.40 |
| us-west-2 (Oregon) | 1.00× | $0.40 |
| eu-west-1 (Ireland) | 1.00× | $0.40 |
| ap-southeast-1 (Singapore) | 1.00× | $0.40 |
| ap-northeast-1 (Tokyo) | 1.00× | $0.40 |

SQS pricing is uniform across all commercial regions (unlike S3 or
Lambda, which vary by region). The only price difference is in the KMS
key cost, which may vary slightly by region.

## CloudWatch SQS metrics reference

| Metric | What it measures | Key threshold |
|---|---|---|
| NumberOfEmptyReceives | ReceiveMessage calls returning zero messages | > 50% of total → enable long polling |
| NumberOfMessagesSent | Messages sent to the queue (via any API) | Baseline for cost allocation |
| NumberOfMessagesReceived | Messages retrieved from the queue | Compare to Sent for backlog analysis |
| NumberOfMessagesDeleted | Messages successfully deleted | Should ≈ Received (minus failures) |
| ApproximateNumberOfMessagesVisible | Current queue depth | Sustained > 1000 → consumer bottleneck |
| ApproximateAgeOfOldestMessage | Age of the oldest visible message | Sustained > VisibilityTimeout → re-delivery loop |
| ApproximateNumberOfMessagesNotVisible | Messages in-flight (being processed) | Compare to consumer concurrency |

### Empty receive ratio calculation

```
total_receive_calls = NumberOfEmptyReceives + NumberOfMessagesReceived
empty_receive_ratio = NumberOfEmptyReceives / total_receive_calls

Note: NumberOfMessagesReceived counts individual messages, while
NumberOfEmptyReceives counts API calls. If using batch receive
(MaxNumberOfMessages=10), one receive call returns up to 10 messages.
Adjust the ratio accordingly:

empty_receive_ratio =
  NumberOfEmptyReceives /
  (NumberOfEmptyReceives + ceil(NumberOfMessagesReceived / avg_batch_size))
```

## Cost calculation worked examples

### Example 1: Long polling enablement

```
Current state:
  Total API requests: 100M/month (85M empty receives + 15M non-empty)
  Monthly cost: 100M / 1M × $0.40 = $40.00

Projected state (WaitTimeSeconds=20):
  Empty receives drop 90%: 85M → 8.5M
  Total API requests: 8.5M + 15M = 23.5M
  Monthly cost: 23.5M / 1M × $0.40 = $9.40

Monthly saving: $40.00 − $9.40 = $30.60
Annual saving: $367.20
```

### Example 2: Batch API migration

```
Current state:
  Send: 10M SendMessage calls
  Receive: 10.5M ReceiveMessage calls
  Delete: 9.9M DeleteMessage calls
  Total: 30.4M/month
  Monthly cost: 30.4M / 1M × $0.40 = $12.16

Projected state (SendMessageBatch + DeleteMessageBatch):
  Send: 1M SendMessageBatch calls (10M / 10)
  Receive: 10.5M ReceiveMessage calls (unchanged — SQS caps at 10)
  Delete: 0.99M DeleteMessageBatch calls (9.9M / 10)
  Total: 12.49M/month
  Monthly cost: 12.49M / 1M × $0.40 = $5.00

Monthly saving: $12.16 − $5.00 = $7.16
Annual saving: $85.92
```

## AWS CLI quick reference

### Get queue attributes

```bash
aws sqs get-queue-attributes \
  --queue-url <url> \
  --attribute-names All \
  --profile <profile> --region <region>
```

### Get CloudWatch metrics (14-30 day window)

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS \
  --metric-name NumberOfEmptyReceives \
  --dimensions Name=QueueName,Value=<queue-name> \
  --start-time $(date -d '-30 days' +%FT%TZ) \
  --end-time $(date +%FT%TZ) \
  --period 86400 --statistics Sum \
  --profile <profile> --region <region>
```

### Enable long polling

```bash
aws sqs set-queue-attributes \
  --queue-url <url> \
  --attributes ReceiveMessageWaitTimeSeconds=20
```

### Enable FIFO high-throughput mode

```bash
aws sqs set-queue-attributes \
  --queue-url <fifo-url> \
  --attributes DeduplicationScope=MessageGroup,ThroughputLimit=PerMessageGroupId
```

### Start DLQ redrive (v2 API)

```bash
aws sqs start-message-move-task \
  --source-arn arn:aws:sqs:<region>:<acct>:<dlq-name> \
  --destination-arn arn:aws:sqs:<region>:<acct>:<queue-name>
```
