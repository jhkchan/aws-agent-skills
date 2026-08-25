# Worked examples - SQS Dead-Letter Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Worked example — Visibility timeout exceeded

```text
TARGET: image-processing-queue → image-processing-dlq
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The queue's VisibilityTimeout is 30 seconds but the consumer
  Lambda fn-image-processor has a Duration p99 of 45 seconds. Messages
  become visible again at T+30s while the Lambda is still processing,
  causing duplicate receives and accelerated receive-count increment.
  Messages that would succeed with more time are moved to the DLQ after
  maxReceiveCount=3 receives (Step 4).
LAYER: VISIBILITY_TIMEOUT_EXCEEDED
EVIDENCE:
  - Symptom: image-processing-dlq has grown from 0 to 5,200 messages in
    the last 2 hours. The source queue's
    ApproximateNumberOfMessagesNotVisible is consistently 30-40
    (messages in-flight).
  - Probe: aws cloudwatch get-metric-statistics on AWS/Lambda Duration
    for fn-image-processor: p99 = 45s, Maximum = 58s. The queue
    VisibilityTimeout is 30s.
  - Probe: aws sqs receive-message on the DLQ shows
    ApproximateReceiveCount = 3 on all inspected messages (they
    exhausted maxReceiveCount=3 in ~90 seconds: 3 receives × 30s VT).
  - Passing: Lambda Throttles = 0 (not a concurrency issue); messages
    are well under 256 KB (not a size issue); queue is standard (not
    FIFO, no poison-message blocking).
REMEDIATION:
  1. Raise the visibility timeout on the queue:
     aws sqs set-queue-attributes \
       --queue-url <image-processing-queue-url> \
       --attributes VisibilityTimeout=300
  2. Raise the visibility timeout on the event source mapping:
     aws lambda update-event-source-mapping \
       --uuid <mapping-uuid> --visibility-timeout 300
  3. Redrive the DLQ messages back to the source queue:
     aws sqs start-message-move-task \
       --source-arn arn:aws:sqs:us-east-1:111111111111:image-processing-dlq
  4. Verify Duration p99 < new VisibilityTimeout / 6 (300/6 = 50s, which
     exceeds the observed p99 of 45s).
CONFIRM: Before updating the visibility timeout, emit and await:
  "CONFIRM: About to raise VisibilityTimeout to 300s on
   image-processing-queue and its event source mapping. Proceed?
   (yes/no)"
```

### Worked example — Lambda concurrency throttling

```text
TARGET: batch-jobs-queue → batch-jobs-dlq
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The consumer Lambda fn-batch-processor has a reserved concurrency
  of 5, but the queue is sustaining 50 messages/second. The Lambda is
  throttled at 5 concurrent executions; the backlog grows faster than
  processing. Messages exceed the visibility timeout while waiting for
  a throttled Lambda slot, incrementing receive count and moving to the
  DLQ (Step 3).
LAYER: LAMBDA_CONCURRENCY_THROTTLE
EVIDENCE:
  - Symptom: batch-jobs-dlq has grown from 0 to 12,000 messages in 3
    hours. The source queue backlog is at 45,000 messages.
  - Probe: aws cloudwatch get-metric-statistics on AWS/Lambda Throttles
    for fn-batch-processor: sustained 200+ throttles per 5-minute
    window.
  - Probe: aws lambda get-function-concurrency returns
    ReservedConcurrentExecutions: 5.
  - Probe: aws cloudwatch ConcurrentExecutions Maximum = 5 (at the
    reserved cap) for the entire 3-hour window.
  - Passing: VisibilityTimeout is 300s (exceeds Duration p99 of 12s);
    messages are under 256 KB; maxReceiveCount is 5 (reasonable);
    ReportBatchItemFailures is configured.
REMEDIATION:
  1. Raise the reserved concurrency on fn-batch-processor:
     aws lambda put-function-concurrency \
       --function-name fn-batch-processor \
       --reserved-concurrent-executions 50
  2. If the account-level concurrency limit is also a bottleneck,
     request a quota increase via the AWS Support Center.
  3. After the backlog drains, redrive the DLQ:
     aws sqs start-message-move-task \
       --source-arn arn:aws:sqs:us-east-1:111111111111:batch-jobs-dlq \
       --max-number-of-messages-per-second 100
  4. Verify Throttles drops to 0 and the source queue backlog drains.
CONFIRM: Before changing concurrency, emit and await:
  "CONFIRM: About to raise fn-batch-processor reserved concurrency from
   5 to 50. Proceed? (yes/no)"
```

