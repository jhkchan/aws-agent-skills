# Eval prompt: visibility-timeout-exceeded

Diagnose the SQS dead-letter queue accumulation for the following queue.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: SQS DLQ `sqs-dlq-vis-timeout` has grown from 0 to 5,200
messages in the last 2 hours. The source queue has a consistently high
`ApproximateNumberOfMessagesNotVisible` (30-40 messages in-flight).

```text
SourceQueueURL: https://sqs.us-east-1.amazonaws.com/111111111111/sqs-source-vis-timeout
DLQArn: arn:aws:sqs:us-east-1:111111111111:sqs-dlq-vis-timeout
RedrivePolicy:
  deadLetterTargetArn: "arn:aws:sqs:us-east-1:111111111111:sqs-dlq-vis-timeout"
  maxReceiveCount: "3"
VisibilityTimeout: 30
MessageRetentionPeriod: 1209600
FifoQueue: false

Consumer: Lambda fn-image-processor-vis
Lambda Timeout: 60
Lambda EventSourceMapping:
  BatchSize: 5
  VisibilityTimeout: 30
  FunctionResponseTypes: ["ReportBatchItemFailures"]

CloudWatch metrics (last 2 hours):
  - Lambda Duration p99: 45s, Maximum: 58s
  - Lambda Throttles: 0
  - Lambda Errors: 0 (no processing errors)
  - DLQ ApproximateNumberOfMessages: 5200 and growing
  - Source queue ApproximateNumberOfMessagesNotVisible: 30-40

DLQ message inspection:
  ApproximateReceiveCount: 3 on all inspected messages
  Message bodies are valid image processing jobs
  No consumer errors — messages simply ran out of receives
```

The consumer has zero processing errors, yet messages accumulate in the
DLQ. Compare the Lambda Duration p99 against the VisibilityTimeout. What
happens when processing takes longer than the visibility window?
