# Eval prompt: fifo-high-throughput-mode

Optimise the following SQS queue for throughput and cost. Walk the
polling/batch/visibility/FIFO-mode decision framework and emit the
standard optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

QueueName: q-fifo-high-throughput-mode.fifo
QueueType: FIFO
Region: us-east-1
Attributes:
  ReceiveMessageWaitTimeSeconds: 20
  VisibilityTimeout: 60
  MessageRetentionPeriod: 345600 (4 days)
  DeduplicationScope: (not set — default: queue)
  ThroughputLimit: (not set — default: queue-level 300 TX/s)
  ContentBasedDeduplication: true
  RedrivePolicy: {"deadLetterTargetArn":"arn:...","maxReceiveCount":"5"}

Consumer config:
  Type: Lambda ESM
  ESM BatchSize: 10

Metrics (last 30 days):
  - NumberOfMessagesSent: 1,296,000,000/month (avg 500 TX/s)
  - NumberOfMessagesReceived: 1,280,000,000/month
  - NumberOfMessagesDeleted: 1,275,000,000/month
  - ApproximateNumberOfMessagesVisible: 50,000 avg (backlog growing)
  - ApproximateAgeOfOldestMessage: 120 seconds avg (rising)

Cost data:
  - Monthly cost: ~$516.00

Workload context: financial transaction events requiring strict
per-account ordering. 50,000 unique accounts partitioned across 50
MessageGroupIds. Current throughput is 500 TX/s but queue-level limit
is 300 TX/s — messages are backing up. Workload does NOT need
cross-group deduplication (each group is independent).
