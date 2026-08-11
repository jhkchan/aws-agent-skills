# Eval prompt: visibility-timeout-rightsizing

Optimise the following SQS queue for throughput and cost. Walk the
polling/batch/visibility decision framework and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

QueueName: q-visibility-timeout-rightsizing
QueueType: Standard
Region: us-east-1
Attributes:
  ReceiveMessageWaitTimeSeconds: 20
  VisibilityTimeout: 30
  MessageRetentionPeriod: 345600 (4 days)
  RedrivePolicy: {"deadLetterTargetArn":"arn:...","maxReceiveCount":"3"}

Consumer config:
  Type: Lambda ESM
  ESM BatchSize: 10
  MaximumBatchingWindowInSeconds: 5
  ESM VisibilityTimeout: 30 (inherits queue default)
  FunctionResponseTypes: ["ReportBatchItemFailures"]

Consumer metrics:
  - Duration avg: 38s, p95: 45s
  - Re-delivery rate: 20%

Metrics (last 30 days):
  - NumberOfEmptyReceives: 2,000,000/month
  - NumberOfMessagesReceived: 18,000,000/month (includes 3M re-deliveries)
  - NumberOfMessagesSent: 15,000,000/month
  - NumberOfMessagesDeleted: 14,700,000/month
  - ApproximateNumberOfMessagesVisible: 800 avg
  - ApproximateAgeOfOldestMessage: 35 seconds avg

Cost data:
  - Total SQS API requests: ~33,000,000/month
  - Monthly cost: $13.20

Workload context: PDF generation pipeline. Each message triggers a
Lambda that renders a PDF (35-45s processing time). The 30s visibility
timeout is shorter than processing time, causing phantom re-deliveries.
