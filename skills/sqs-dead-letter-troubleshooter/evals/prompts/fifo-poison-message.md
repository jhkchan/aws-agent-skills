# Eval prompt: fifo-poison-message

Diagnose the SQS FIFO queue stall for the following queue. Walk the
symptom-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: FIFO queue `sqs-source-fifo-poison.fifo` throughput dropped to
near-zero for customer "cust-9912" at 14:30 UTC. Other customer groups
continue processing normally. DLQ `sqs-dlq-fifo-poison.fifo` has
accumulated 23 messages in the last hour, all with MessageGroupId
"cust-9912".

```text
SourceQueueURL: https://sqs.us-east-1.amazonaws.com/111111111111/sqs-source-fifo-poison.fifo
DLQArn: arn:aws:sqs:us-east-1:111111111111:sqs-dlq-fifo-poison.fifo
RedrivePolicy:
  deadLetterTargetArn: "arn:aws:sqs:us-east-1:111111111111:sqs-dlq-fifo-poison.fifo"
  maxReceiveCount: "5"
VisibilityTimeout: 120
MessageRetentionPeriod: 1209600
FifoQueue: true

Consumer: Lambda fn-sqs-fifo-consumer
Lambda Timeout: 60
Lambda EventSourceMapping:
  BatchSize: 10
  VisibilityTimeout: 120

DLQ message inspection (10 samples):
  All have Attributes.MessageGroupId = "cust-9912"
  First message (by SentTimestamp):
    ApproximateReceiveCount: 5
    Body: "{bad json: missing closing brace"
  Remaining 9 messages also MessageGroupId "cust-9912"

Lambda logs:
  Repeated "SyntaxError: Unexpected token" for MessageGroupId
    "cust-9912" starting at 14:30 UTC
  No errors for other MessageGroupIds

CloudWatch metrics (last hour):
  - Lambda Throttles: 0
  - Lambda Duration p99: 8s (well within VT of 120s)
  - Source queue ApproximateNumberOfMessages: stable for non-cust-9912
```

The queue is FIFO. Only one MessageGroupId is affected while others
flow normally. Examine the DLQ messages: what is the payload of the
first message in MessageGroupId "cust-9912"? Why does FIFO ordering
make this a group-level problem?
