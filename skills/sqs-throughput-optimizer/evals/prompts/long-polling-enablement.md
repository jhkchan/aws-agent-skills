# Eval prompt: long-polling-enablement

Optimise the following SQS queue for throughput and cost. Walk the
polling/batch/visibility decision framework and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

QueueName: q-long-polling-enablement
QueueType: Standard
Region: us-east-1
Attributes:
  ReceiveMessageWaitTimeSeconds: 0
  VisibilityTimeout: 30
  MessageRetentionPeriod: 345600 (4 days)
  DelaySeconds: 0
  RedrivePolicy: {"deadLetterTargetArn":"arn:aws:sqs:us-east-1:123456789012:q-long-polling-enablement-dlq","maxReceiveCount":"3"}

Consumer config:
  Type: EC2 (t3.medium) running Node.js poller
  Uses ReceiveMessage directly (not Lambda ESM)
  Poller count: 4 threads

Metrics (last 30 days):
  - NumberOfEmptyReceives: 85,000,000/month
  - NumberOfMessagesReceived: 15,000,000/month
  - NumberOfMessagesSent: 15,200,000/month
  - NumberOfMessagesDeleted: 14,800,000/month
  - ApproximateNumberOfMessagesVisible: 1,500 avg
  - ApproximateAgeOfOldestMessage: 12 seconds avg
  - Empty receive ratio: 85%

Cost data:
  - SQS API requests (last 30 days): 100,000,000
  - Monthly cost: $40.00

Workload context: order events from e-commerce checkout. 4 EC2 poller
threads calling ReceiveMessage in a tight loop. Traffic is bursty
(spikes during business hours, low at night).
