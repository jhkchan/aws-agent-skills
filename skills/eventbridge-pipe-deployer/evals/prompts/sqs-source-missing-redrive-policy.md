# Eval prompt: sqs-source-missing-redrive-policy

Design a deployment plan for a production EventBridge Pipe. Emit the
standard VERDICT block.

Requirements:

- Pipe name: prod-jobs-pipe
- Source: SQS arn:aws:sqs:us-east-1:111111111111:jobs-queue
  (the queue has NO RedrivePolicy configured — verified via
  get-queue-attributes)
- Filter: none
- Enrichment: none
- Target: Lambda
  arn:aws:lambda:us-east-1:111111111111:function:jobs-processor
  (state=Active)
- Batch: size 10
- DLQ: arn:aws:sqs:us-east-1:111111111111:prod-pipe-dlq (configured
  via the pipe's source-parameters DeadLetterConfig field)

The user expects the pipe-level DLQ to catch poison messages that
fail processing past retry limits. They have NOT configured a
RedrivePolicy on the source SQS queue.
