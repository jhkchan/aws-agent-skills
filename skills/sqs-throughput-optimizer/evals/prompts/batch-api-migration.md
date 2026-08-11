# Eval prompt: batch-api-migration

Optimise the following SQS queue for throughput and cost. Walk the
polling/batch/visibility decision framework and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

QueueName: q-batch-api-migration
QueueType: Standard
Region: us-east-1
Attributes:
  ReceiveMessageWaitTimeSeconds: 20
  VisibilityTimeout: 60
  MessageRetentionPeriod: 345600 (4 days)
  RedrivePolicy: {"deadLetterTargetArn":"arn:...","maxReceiveCount":"3"}

Consumer config:
  Type: ECS Fargate task
  Calls DeleteMessage (not DeleteMessageBatch) after processing each message
  Batch size: 1 message per ReceiveMessage call

Producer config:
  Calls SendMessage (not SendMessageBatch) for each message

Metrics (last 30 days):
  - NumberOfEmptyReceives: 500,000/month (low — long polling already enabled)
  - NumberOfMessagesReceived: 10,000,000/month
  - NumberOfMessagesSent: 10,100,000/month
  - NumberOfMessagesDeleted: 9,900,000/month
  - ApproximateNumberOfMessagesVisible: 200 avg
  - ApproximateAgeOfOldestMessage: 5 seconds avg

Cost data:
  - Total SQS API requests: 30,600,000/month (10M send + 10.5M receive + 9.9M delete)
  - Monthly cost: $12.24

Workload context: notification dispatch pipeline. Producer sends
individual notification messages. Consumer processes and deletes one at
a time. Messages are small (2 KB avg). No ordering needed.
