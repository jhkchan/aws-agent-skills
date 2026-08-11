# Example usage: sqs-throughput-optimizer

A walkthrough showing the skill optimizing a Standard SQS queue with
short polling and single-message delete calls, demonstrating the
empty-receive analysis, batch API migration, the dollar savings math,
and the staged attribute change with monitoring.

## Input (user prompt)

> Review this SQS queue before our Q3 FinOps review. It is an order
> events queue and the bill seems high for the volume.

```text
QueueName: order-events-queue
QueueType: Standard
Region: us-east-1
Attributes:
  ReceiveMessageWaitTimeSeconds: 0
  VisibilityTimeout: 30
  MessageRetentionPeriod: 345600 (4 days)
  DelaySeconds: 0
  RedrivePolicy: {"deadLetterTargetArn":"arn:aws:sqs:us-east-1:123456789012:order-events-dlq","maxReceiveCount":"3"}

Consumer config:
  Type: EC2 (t3.medium) running Node.js poller
  Uses ReceiveMessage directly (not Lambda ESM)
  Poller count: 4 threads
  Calls DeleteMessage one-at-a-time

Metrics (last 30 days):
  - NumberOfEmptyReceives: 85,000,000/month
  - NumberOfMessagesReceived: 15,000,000/month
  - NumberOfMessagesSent: 15,200,000/month
  - NumberOfMessagesDeleted: 14,800,000/month
  - ApproximateNumberOfMessagesVisible: 1,500 avg
  - ApproximateAgeOfOldestMessage: 12 seconds avg
  - Empty receive ratio: 85%

Cost data:
  - SQS API requests (last 30 days): 100,000,000
  - Monthly cost: $40.00

Workload context: order events from e-commerce checkout. 4 EC2 poller
threads calling ReceiveMessage in a tight loop. Traffic is bursty
(spikes during business hours, low at night).
```

## Skill output

```text
TARGET: order-events-queue
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Standard queue with ReceiveMessageWaitTimeSeconds=0 generating
  85M empty receives/month (85% of total ReceiveMessage calls, confirmed
  by CloudWatch NumberOfEmptyReceives). Enabling long polling
  (WaitTimeSeconds=20) projects a 90% reduction in empty receives.
  Consumer also uses DeleteMessage one-at-a-time; switching to
  DeleteMessageBatch reduces delete requests 10x.
RECOMMENDATION:
  Current: short polling (WaitTimeSeconds=0), single-message delete, VisibilityTimeout=30s, Standard
  Proposed: long polling (WaitTimeSeconds=20), batch delete, VisibilityTimeout=30s, Standard
  Dimensions changed: polling (Step 1) + batching (Step 2)
  Dimensions checked: polling → (enable long)  batching → (batch delete)
    visibility ✓ (30s > consumer p95 <1s)  retention ✓ (4 days, healthy)
    redrive ✓ (maxReceiveCount=3, DLQ depth not growing)
    queue-type ✓ (Standard, no ordering needed)  fifo-mode ✓ (N/A)
  Confidence: HIGH — CloudWatch NumberOfEmptyReceives directly measured;
    batch delete is a code-level change with no infrastructure risk.
ESTIMATED_SAVINGS:
  Current monthly: $40.00
    requests: 100M / 1M × $0.40 = $40.00
  Projected monthly: $7.60
    requests: 19M / 1M × $0.40 = $7.60
      (8.5M empty @ 90% reduction + 1.48M batch delete + 8.5M receive + 0.52M send)
  Monthly saving: $32.40
    ($40.00 − $7.60 = $32.40 ✓)
  Annual saving: $388.80
MIGRATION_STEPS:
  1. Enable long polling on the queue:
     aws sqs set-queue-attributes --queue-url <url> --attributes ReceiveMessageWaitTimeSeconds=20
  2. Update consumer to use DeleteMessageBatch instead of DeleteMessage:
     aws sqs delete-message-batch --queue-url <url> --entries file://batch.json
  3. Reduce poller thread count from 4 to 2 (long polling replaces tight-loop polling).
  4. Monitor NumberOfEmptyReceives for 7 days post-change:
     aws cloudwatch get-metric-statistics --namespace AWS/SQS --metric-name NumberOfEmptyReceives ...
  5. Verify ApproximateAgeOfOldestMessage stays under 30s (no backlog).
CONFIRM: About to set-queue-attributes on order-events-queue
  (WaitTimeSeconds 0 → 20) and switch consumer to batch delete. Monthly
  saving $32.40 (81% request reduction). Proceed? (yes/no)
```

## What the skill caught that a generic assistant misses

1. **The empty-receive ratio is the primary cost driver.** A generic
   assistant says "enable long polling." The skill cites the exact 85%
   empty-receive ratio from CloudWatch, projects the 90% reduction, and
   quantifies the dollar impact ($30.60 from polling alone).

2. **Batch API migration stacks on top of polling.** The skill stacks two
   savings dimensions: polling (eliminate empty receives) + batching
   (reduce delete requests 10x). A generic assistant captures only
   polling, leaving the delete-request savings on the table.

3. **Poller thread count should decrease after long polling.** The skill
   recommends reducing from 4 to 2 poller threads because long polling
   replaces tight-loop polling. A generic assistant does not address
   consumer concurrency changes.

4. **All seven dimensions are checked and reported.** The skill shows
   `Dimensions checked` with all seven dimensions, each marked. A
   generic assistant focuses on one dimension and ignores the rest.

5. **Cost arithmetic is shown explicitly.** The skill shows the formula
   (`100M / 1M × $0.40 = $40.00`) so the operator can verify. A generic
   assistant says "this should save money" without showing the math.

## Slash-command invocation

```
/aws:optimize-sqs-throughput
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimize our SQS queues for the Q3 FinOps review"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: sqs-throughput-optimizer]` and hands
off to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new configuration:

```bash
# Confirm long polling is enabled
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/<acct>/order-events-queue \
  --attribute-names ReceiveMessageWaitTimeSeconds \
  --profile default --output json

# Monitor NumberOfEmptyReceives for 7 days post-change
aws cloudwatch get-metric-statistics --namespace AWS/SQS \
  --metric-name NumberOfEmptyReceives \
  --dimensions Name=QueueName,Value=order-events-queue \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 86400 --statistics Sum --output json

# Monitor queue depth for backlog
aws cloudwatch get-metric-statistics --namespace AWS/SQS \
  --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=order-events-queue \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 3600 --statistics Average --output json
```

If NumberOfEmptyReceives does not drop by at least 80% within 7 days,
verify the consumer is not still calling ReceiveMessage in a tight loop
(ignoring the queue attribute).

## Fleet-wide extension

For a fleet of N SQS queues, run the skill in batch mode:

1. Pull all queues with `aws sqs list-queues`.
2. For each queue, pull attributes and 30-day CloudWatch metrics.
3. Calculate empty-receive ratio and batch-API adoption per queue.
4. Sort by estimated monthly savings (largest first).
5. Slice into batches of 5 queues.
6. For each batch: emit per-queue MIGRATION_STEPS, then a single CONFIRM
   for the batch.
7. Verify each batch before proceeding to the next.
8. After the polling sweep, evaluate FIFO high-throughput mode for any
   FIFO queues showing backlog growth.
