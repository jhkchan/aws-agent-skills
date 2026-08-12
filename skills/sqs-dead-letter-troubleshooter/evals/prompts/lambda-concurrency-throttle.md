# Eval prompt: lambda-concurrency-throttle

Diagnose the SQS dead-letter queue accumulation for the following queue.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: SQS DLQ `sqs-dlq-lambda-throttle` has grown from 0 to 12,000
messages in 3 hours. The source queue backlog is at 45,000 messages and
growing. The consumer Lambda has a reserved concurrency of 5.

```text
SourceQueueURL: https://sqs.us-east-1.amazonaws.com/111111111111/sqs-source-lambda-throttle
DLQArn: arn:aws:sqs:us-east-1:111111111111:sqs-dlq-lambda-throttle
RedrivePolicy:
  deadLetterTargetArn: "arn:aws:sqs:us-east-1:111111111111:sqs-dlq-lambda-throttle"
  maxReceiveCount: "5"
VisibilityTimeout: 300
MessageRetentionPeriod: 1209600
FifoQueue: false

Consumer: Lambda fn-batch-processor-throttle
Lambda Timeout: 60
Lambda EventSourceMapping:
  BatchSize: 10
  VisibilityTimeout: 300
  FunctionResponseTypes: ["ReportBatchItemFailures"]

Lambda concurrency:
  ReservedConcurrentExecutions: 5

CloudWatch metrics (last 3 hours):
  - Lambda Throttles: sustained 200+ per 5-minute window
  - Lambda ConcurrentExecutions: Maximum = 5 (at the cap)
  - Lambda Duration p99: 12s (within VT of 300s)
  - Lambda Errors: 0
  - Source queue ApproximateNumberOfMessages: 45,000 and growing
  - DLQ ApproximateNumberOfMessages: 12,000 and growing
```

The consumer has no processing errors and the visibility timeout is
generous (300s vs 12s p99). Yet the backlog grows and the DLQ fills.
Check the Lambda concurrency metrics against the reserved concurrency
limit.
