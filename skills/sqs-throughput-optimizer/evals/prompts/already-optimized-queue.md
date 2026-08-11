# Eval prompt: already-optimized-queue

Optimise the following SQS queue for throughput and cost. Walk the
polling/batch/visibility decision framework and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

QueueName: q-already-optimized-queue
QueueType: Standard
Region: us-east-1
Attributes:
  ReceiveMessageWaitTimeSeconds: 20
  VisibilityTimeout: 120
  MessageRetentionPeriod: 345600 (4 days)
  RedrivePolicy: {"deadLetterTargetArn":"arn:...","maxReceiveCount":"3"}

Consumer config:
  Type: Lambda ESM
  ESM BatchSize: 10
  MaximumBatchingWindowInSeconds: 5
  ESM VisibilityTimeout: 120
  FunctionResponseTypes: ["ReportBatchItemFailures"]
  Consumer uses DeleteMessageBatch internally via ESM auto-delete

Producer config:
  Uses SendMessageBatch (10 messages per call)

Metrics (last 30 days):
  - NumberOfEmptyReceives: 100,000/month (0.5% — long polling effective)
  - NumberOfMessagesReceived: 20,000,000/month
  - NumberOfMessagesSent: 20,100,000/month (via SendMessageBatch)
  - NumberOfMessagesDeleted: 19,900,000/month
  - ApproximateNumberOfMessagesVisible: 300 avg
  - ApproximateAgeOfOldestMessage: 3 seconds avg

Consumer metrics:
  - Duration avg: 800ms, p95: 1,200ms
  - Re-delivery rate: 0.1%

DLQ metrics:
  - ApproximateNumberOfMessagesVisible: 12 (healthy)
  - ApproximateAgeOfOldestMessage: 30 minutes

Cost data:
  - Total SQS API requests: ~22,100,000/month
  - Monthly cost: $8.84

Workload context: event ingestion pipeline. Already uses long polling,
batch APIs, right-sized visibility timeout. DLQ is healthy. No further
optimization expected.
