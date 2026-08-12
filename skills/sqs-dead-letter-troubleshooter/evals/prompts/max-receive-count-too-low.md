# Eval prompt: max-receive-count-too-low

Diagnose the SQS dead-letter queue accumulation for the following queue.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: SQS DLQ `sqs-dlq-max-receive-count` has accumulated 3,200
messages in the last 2 hours. The source queue drains normally for most
messages, but ~15% end up in the DLQ. The consumer Lambda has transient
downstream API failures (5xx responses from a payment gateway).

```text
SourceQueueURL: https://sqs.us-east-1.amazonaws.com/111111111111/sqs-source-max-receive-count
DLQArn: arn:aws:sqs:us-east-1:111111111111:sqs-dlq-max-receive-count
RedrivePolicy:
  deadLetterTargetArn: "arn:aws:sqs:us-east-1:111111111111:sqs-dlq-max-receive-count"
  maxReceiveCount: "1"
VisibilityTimeout: 60
MessageRetentionPeriod: 1209600
FifoQueue: false

Consumer: Lambda fn-sqs-consumer-max-rc
Lambda Timeout: 30
Lambda EventSourceMapping:
  BatchSize: 10
  VisibilityTimeout: 60
  FunctionResponseTypes: ["ReportBatchItemFailures"]

DLQ message inspection (5 samples):
  All have ApproximateReceiveCount: 1
  Bodies contain valid order data
  Lambda logs show "Payment gateway returned 503" for same MessageIds

CloudWatch metrics (last 2 hours):
  - Lambda Throttles: 0
  - Lambda Duration p99: 2.1s (well within VT of 60s)
  - Lambda Errors: 480 (correlate with 503 responses)
  - DLQ ApproximateNumberOfMessages: growing
```

The consumer has transient downstream failures. Examine the
`maxReceiveCount` value and consider whether it provides any retry
opportunities for transient failures.
