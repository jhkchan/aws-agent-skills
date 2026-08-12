# Eval prompt: dlq-type-mismatch-fifo

Diagnose the SQS DLQ redrive failure for the following queue
configuration. Walk the symptom-driven diagnostic tree and emit the
standard diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: Operator attempted to redrive messages from the DLQ back to
the source queue using `StartMessageMoveTask`. The task failed with
"InvalidParameterCombination: The source queue and the destination
queue must have the same type."

```text
SourceQueueURL: https://sqs.us-east-1.amazonaws.com/111111111111/sqs-source-dlq-mismatch.fifo
DLQArn: arn:aws:sqs:us-east-1:111111111111:sqs-dlq-mismatch
RedrivePolicy:
  deadLetterTargetArn: "arn:aws:sqs:us-east-1:111111111111:sqs-dlq-mismatch"
  maxReceiveCount: "5"
VisibilityTimeout: 60
MessageRetentionPeriod: 1209600
FifoQueue: true

DLQ attributes:
  FifoQueue: false (NOT a FIFO queue — standard queue)
  QueueName: sqs-dlq-mismatch (no .fifo suffix)

StartMessageMoveTask error:
  "InvalidParameterCombination: The source queue and the
  destination queue must have the same type."

DLQ currently has 800 messages that need redriving.
```

The source queue is FIFO (.fifo suffix). Examine the DLQ's queue type
— is it also FIFO? What does the error message tell you about the type
compatibility requirement?
