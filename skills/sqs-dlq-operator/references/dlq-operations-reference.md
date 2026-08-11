# SQS DLQ Operations Reference

Load this reference when planning or executing any SQS dead-letter queue
operation. The procedures below are the canonical sequences for each DLQ
operation archetype, with pre-checks, command sequence, post-verification,
and rollback notes.

## Operation decision tree

| Scenario | Operation | Why |
|---|---|---|
| Source queue has no DLQ | create | Production queue without DLQ loses poison-pill messages silently |
| DLQ filling too fast (false positives) | tune (maxReceiveCount up) OR fix visibility timeout | maxReceiveCount too low OR visibility-timeout race |
| DLQ filling too slowly (real poison pills) | analyze + selective delete | Genuine consumer failures — fix consumer, remove poison pills |
| DLQ has 1000+ messages, consumer patched | replay (StartMessageMoveTask) | Bulk replay after root-cause fix |
| DLQ has 10 messages, all poison pills | analyze + selective receive+delete | Small count, manual triage |
| DLQ depth alarm firing | monitor + analyze | Investigate spike before replaying |
| Cross-account source needs redrive | create + RedriveAllowPolicy | Default deny blocks cross-account redrive |

## Create DLQ procedure

**Pre-checks:**
1. Source queue exists (`get-queue-url`).
2. DLQ name available (no existing queue with that name).
3. DLQ type matches source (`FifoQueue` attribute).
4. DLQ retention will be 14 days (1209600s).
5. maxReceiveCount >= 3.

**Command sequence:**

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

# 3. Verify
aws sqs get-queue-attributes --queue-url "$SOURCE_URL" \
  --attribute-names RedrivePolicy --output json
```

**For FIFO source:**

```bash
aws sqs create-queue \
  --queue-name prod-orders-dlq.fifo \
  --attributes FifoQueue=true,MessageRetentionPeriod=1209600,SqsManagedSseEnabled=true

# VERIFY the DLQ ARN ends in .fifo before wiring
DLQ_ARN=$(aws sqs get-queue-attributes --queue-url "$DLQ_URL" \
  --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)
# Must be: arn:aws:sqs:us-east-1:111111111111:prod-orders-dlq.fifo
```

## Tune maxReceiveCount procedure

```bash
# Snapshot first
aws sqs get-queue-attributes --queue-url "$SOURCE_URL" \
  --attribute-names RedrivePolicy --output json > /tmp/source-redrive-backup-$(date +%s).json

# Update (preserve DLQ ARN, change maxReceiveCount)
aws sqs set-queue-attributes \
  --queue-url "$SOURCE_URL" \
  --attributes RedrivePolicy="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"10\"}"
```

**maxReceiveCount tuning matrix:**

| Workload | Recommended | Rationale |
|---|---|---|
| Standard queue, transient failures common | 5-10 | Tolerate Lambda throttle, cold start, SDK retry |
| Standard queue, idempotent consumer | 3-5 | Failures are real, move to DLQ faster |
| FIFO queue | 5-15 | Poison pill blocks entire message group — move faster |
| Lambda event source mapping (no partial batch) | 10-20 | Each batch retry burns count on ALL messages |
| Lambda event source mapping (with ReportBatchItemFailures) | 5-10 | Only failed messages retry — count burns slower |
| High-throughput batch consumer | 10-20 | Multiple consumers contend; fewer effective retries |

## Analyze DLQ procedure

**Goal:** determine whether DLQ entries are genuine poison pills or
false positives from a configuration race.

```bash
# 1. Check DLQ depth
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=prod-orders-dlq \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average Sum

# 2. Receive messages for inspection (DO NOT delete)
aws sqs receive-message \
  --queue-url "$DLQ_URL" \
  --max-number-of-messages 10 \
  --visibility-timeout 300 \
  --attribute-names All \
  --message-attribute-names All \
  --output json

# 3. Check consumer logs for errors around the redrive timestamp
aws logs filter-log-events \
  --log-group-name /aws/lambda/order-processor \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --filter-pattern '"ERROR"' \
  --limit 50

# 4. Check Lambda event source mapping for partial-batch config
aws lambda list-event-source-mappings \
  --event-source-arn "$SOURCE_ARN" \
  --query 'EventSourceMappings[0].{Uuid:UUID,BatchSize:BatchSize,VisibilityTimeout:VisibilityTimeout,ResponseTypes:FunctionResponseTypes}'
```

**Diagnostic interpretation:**

| Observation | Conclusion |
|---|---|
| Body is valid JSON, consumer should succeed, no errors in logs | Visibility-timeout race (false positive) |
| Body malformed or missing required field | Poison pill (genuine) |
| `ApproximateReceiveCount` on DLQ msg < maxReceiveCount | Anomalous (partial-batch gap or manual move) |
| Consumer logs show `TimeoutException` | Visibility timeout too short OR Lambda timeout too short |
| Consumer logs show `AccessDenied` | IAM policy gap on consumer role |
| Consumer logs show `ConditionalCheckFailed` | DynamoDB condition — idempotency conflict |
| All DLQ messages share one `MessageGroupId` (FIFO) | Head-of-line block on poison-pill group |

## Replay via StartMessageMoveTask procedure

**Pre-checks:**
1. Source queue exists and is the correct destination.
2. Source has an active consumer.
3. Root cause of original DLQ entry is FIXED (consumer patched, config
   adjusted, poison-pill schema handled).
4. Pre-replay DLQ depth captured for progress measurement.
5. `MaxNumberOfMessagesPerSecond` chosen to match consumer capacity.

```bash
# 1. Pre-replay snapshot
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=prod-orders-dlq \
  --start-time $(date -u -d '5 min ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Average

# 2. Start the move task (asynchronous)
TASK_HANDLE=$(aws sqs start-message-move-task \
  --source-arn "$DLQ_ARN" \
  --destination-arn "$SOURCE_ARN" \
  --max-number-of-messages-per-second 100 \
  --query 'TaskHandle' --output text)

# 3. Poll task status
aws sqs list-message-move-tasks \
  --source-arn "$DLQ_ARN" \
  --max-results 5

# 4. Post-replay verify (DLQ depth should be 0, source receiving)
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=prod-orders-dlq \
  --start-time $(date -u -d '15 min ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Average

aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS --metric-name NumberOfMessagesReceived \
  --dimensions Name=QueueName,Value=prod-orders \
  --start-time $(date -u -d '15 min ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum
```

**Task status values:**
- `RUNNING` — task in progress (large DLQ).
- `COMPLETED` — all messages moved successfully.
- `FAILED` — task failed (check `FailureReason`).
- `CANCELLING` / `CANCELLED` — operator cancelled via
  `cancel-message-move-task`.

**Replay throttle guidance:**

| Consumer type | MaxNumberOfMessagesPerSecond | Rationale |
|---|---|---|
| Lambda (50 concurrent) | 100-500 | Each msg triggers invocation; respect concurrency |
| Lambda (500 concurrent) | 1000-5000 | Higher concurrency sustains faster replay |
| EC2/ECS worker (10 pods) | 50-200 | Poll-based; depends on poll rate |
| Unknown | Start at 100, increase if DLQ drains and consumer keeps up | |

## Enable partial batch responses (prevent false-positive DLQ)

```bash
# Find the mapping UUID
aws lambda list-event-source-mappings \
  --event-source-arn "$SOURCE_ARN" \
  --query 'EventSourceMappings[0].UUID' --output text

# Update to report per-message failures
aws lambda update-event-source-mapping \
  --uuid <mapping-uuid> \
  --function-response-types ReportBatchItemFailures

# Verify
aws lambda get-event-source-mapping \
  --uuid <mapping-uuid> \
  --query 'FunctionResponseTypes'
# Should return: ["ReportBatchItemFailures"]
```

Without this, a single failed message in a batch of 10 causes all 10
to retry — burning maxReceiveCount on healthy messages and causing
duplicate processing.

## Cross-account DLQ with RedriveAllowPolicy

```bash
# On the DLQ (owned by account 111111111111), allow source from account 222222222222
aws sqs set-queue-attributes \
  --queue-url "$DLQ_URL" \
  --attributes RedriveAllowPolicy='{"redrivePermission":"allowList","sourceQueueArns":["arn:aws:sqs:us-east-1:222222222222:cross-account-source"]}'
```

**RedriveAllowPolicy options:**
- `{"redrivePermission":"allowAll"}` — any account can redrive (NOT
  recommended — security risk).
- `{"redrivePermission":"denyAll"}` — no cross-account redrive (default).
- `{"redrivePermission":"allowList","sourceQueueArns":[...]}` — allowlist
  specific source queues (recommended for cross-account).

## Selective poison-pill removal (small DLQ)

For DLQs with <100 messages where most are poison pills (not worth
bulk replay), remove selectively:

```bash
# Receive and inspect (one at a time)
aws sqs receive-message \
  --queue-url "$DLQ_URL" \
  --max-number-of-messages 1 \
  --visibility-timeout 30 \
  --attribute-names All

# If poison pill, delete:
aws sqs delete-message \
  --queue-url "$DLQ_URL" \
  --receipt-handle <handle>

# If valid (worth replaying), let visibility timeout expire (returns to DLQ)
# OR collect for batch replay later
```

## Cost reference (2026, us-east-1)

- SQS API: $0.40 per million requests (Standard), $0.50 (FIFO).
- `StartMessageMoveTask`: billed as standard SQS requests on the
  destination (one ReceiveMessage + one SendMessage per redriven message).
- DLQ storage: free (messages retained up to 14 days).
- CloudWatch metrics: free for SQS namespace.
- 1M message replay = ~$0.40 in SQS API costs (replay side).

## Worked example — create DLQ (READY)

```text
OPERATION: create
VERDICT: READY
TARGET: prod-orders (source) -> prod-orders-dlq (new DLQ)
PRE_CHECKS:
  - [PASS] Source queue prod-orders exists (Standard, VisibilityTimeout=60)
  - [PASS] DLQ name prod-orders-dlq available
  - [PASS] DLQ type matches source: Standard (FifoQueue=false)
  - [PASS] DLQ retention will be 14 days (1209600s)
  - [PASS] maxReceiveCount=5 >= 3
  - [PASS] VisibilityTimeout 60s >= Lambda p99 of 8s
  - [PASS] Lambda mapping has ReportBatchItemFailures enabled
STEPS:
  1. CONFIRM: About to create prod-orders-dlq and wire redrive on prod-orders. Proceed? (yes/no)
  2. aws sqs create-queue --queue-name prod-orders-dlq --attributes MessageRetentionPeriod=1209600,SqsManagedSseEnabled=true
  3. aws sqs set-queue-attributes --queue-url <source-url> --attributes RedrivePolicy='{"deadLetterTargetArn":"<dlq-arn>","maxReceiveCount":"5"}'
POST_VERIFY:
  - (pending execution)
  - get-queue-attributes on prod-orders returns RedrivePolicy with DLQ ARN and maxReceiveCount=5
STATE: pending — DLQ empty until messages exhaust maxReceiveCount on source
NOTES:
  - Type match verified. VisibilityTimeout >= 6x p99. ReportBatchItemFailures enabled.
```

## Worked example — analyze DLQ (BLOCKED, root cause found)

```text
OPERATION: analyze
VERDICT: BLOCKED
TARGET: prod-orders-dlq (depth: 1247)
PRE_CHECKS:
  - [PASS] DLQ prod-orders-dlq exists, ApproximateNumberOfMessagesVisible: 1247
  - [PASS] Received 10 sample messages for inspection
  - [PASS] Lambda event source mapping inspected
  - [FAIL] Lambda event source mapping does NOT have ReportBatchItemFailures enabled. A single failed message causes the entire batch of 10 to retry, burning maxReceiveCount on healthy messages.
  - [FAIL] VisibilityTimeout 30s < Lambda p99 Duration 52s. Messages return to the queue before processing completes; receive count increments on every redelivery — the #1 false-positive DLQ cause.
STEPS: (none — pre-checks failed; this is a diagnosis)
POST_VERIFY: (none)
STATE: DLQ depth 1247, all sampled messages have valid payloads (no poison pills)
NOTES:
  - Root cause: configuration race, not poison pill. Two issues:
    1. Enable ReportBatchItemFailures on the Lambda event source mapping.
    2. Increase VisibilityTimeout to >= 312s (6x p99 of 52s) on BOTH the queue AND the event source mapping (mapping overrides queue).
  - After fixing config, replay the 1247 messages via StartMessageMoveTask — they are valid payloads, not poison pills.
  - Remediation:
    aws lambda update-event-source-mapping --uuid <uuid> --function-response-types ReportBatchItemFailures --visibility-timeout 312
    aws sqs set-queue-attributes --queue-url <source-url> --attributes VisibilityTimeout=312
    aws sqs start-message-move-task --source-arn <dlq-arn> --destination-arn <source-arn> --max-number-of-messages-per-second 100
```
