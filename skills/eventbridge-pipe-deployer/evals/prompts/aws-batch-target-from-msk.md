# Eval prompt: aws-batch-target-from-msk

Design a deployment plan for a production EventBridge Pipe sourcing
from Amazon MSK and targeting AWS Batch. Emit the standard VERDICT
block.

Requirements:

- Pipe name: prod-batch-pipeline
- Source: MSK arn:aws:kafka:us-east-1:111111111111:cluster/prod-msk/abc-uuid
  (State=ACTIVE)
  - Topic: orders-events
  - ConsumerGroupID: pipe-batch-consumer
  - StartingPosition: LATEST
  - AuthType: SASL_SCRAM_512_AUTH (secret
    arn:aws:secretsmanager:us-east-1:111111111111:secret:msk/scram-abc
    associated with the cluster via aws kafka update-security)
- Filter: none
- Enrichment: none
- Target: AWS Batch job queue
  arn:aws:batch:us-east-1:111111111111:job-queue/prod-queue with job
  definition prod-batch-job:5
- Batch: window 60s, size 500, retry 5, record age 7200s
- DLQ: arn:aws:sqs:us-east-1:111111111111:prod-pipe-dlq
- IAM: pipe role has kafka-cluster:Connect, kafka-cluster:ReadData
  on the topic, kafka-cluster:DescribeGroup and AlterGroup on
  pipe-batch-consumer, secretsmanager:GetSecretValue on the SCRAM
  secret, batch:SubmitJob on the queue, iam:PassRole on the Batch
  job role, sqs:SendMessage on the DLQ.

The user is building an event-driven batch processing pipeline:
high-volume Kafka events coalesced into 60s batches, each batch
triggering one Batch job submission.
