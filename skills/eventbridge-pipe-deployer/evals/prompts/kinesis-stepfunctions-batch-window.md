# Eval prompt: kinesis-stepfunctions-batch-window

Design a deployment plan for a production EventBridge Pipe. Emit the
standard VERDICT block.

Requirements:

- Pipe name: prod-events-orchestration
- Source: Kinesis arn:aws:kinesis:us-east-1:111111111111:stream/events-stream
  (StreamStatus=ACTIVE)
- Filter: none
- Enrichment: none
- Target: Step Functions
  arn:aws:states:us-east-1:111111111111:stateMachine:EventsOrchestration
  (status=ACTIVE, type=STANDARD)
- Batch: window 30s, size 100, retry 5, record age 7200s,
  OnPartialBatchItemFailure=AUTOMATIC_BISECT
- DLQ: arn:aws:sqs:us-east-1:111111111111:prod-pipe-dlq
- IAM: pipe role has kinesis:DescribeStream, kinesis:GetRecords,
  kinesis:GetShardIterator, states:StartExecution on the state
  machine, sqs:SendMessage on the DLQ. Trust policy scoped to
  SourceAccount=111111111111 and SourceArn for prod-events-orchestration.

Existing-account context: the Kinesis stream is ACTIVE and ingestion
volume averages 500 records/sec. The Step Functions state machine is
a Standard workflow running order orchestration. The pipe role was
pre-created with the streaming source permissions.
