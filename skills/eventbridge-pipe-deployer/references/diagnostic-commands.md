# Diagnostic Commands

Blocks moved verbatim from SKILL.md in the agentskills.io progressive-disclosure
restructure. No content changed; load when a SKILL.md pointer stub applies.

## Live-account pre-flight checks (moved from SKILL.md)

**Live-account pre-flight checks (skip if doing offline architecture plan):**

1. Verify IAM permissions: `pipes:CreatePipe`, `StartPipe`,
   `UpdatePipe`, `DescribePipe`, plus source/target/enrichment rights
   (e.g., `dynamodbstreams:GetRecords`, `lambda:InvokeFunction`,
   `sqs:ReceiveMessage`, `kafka-cluster:ReadData`).
2. Verify source ARN resolves and region matches Pipe region:
   - DynamoDB Streams: `aws dynamodbstreams describe-stream --stream-arn <arn>` returns `StreamStatus=ENABLED`.
   - Kinesis: `aws kinesis describe-stream --stream-arn <arn>` returns `StreamStatus=ACTIVE`.
   - SQS: `aws sqs get-queue-attributes --queue-url <url>` returns `QueueArn`.
   - MSK: `aws kafka describe-cluster --cluster-arn <arn>` returns `State=ACTIVE`.
   - Amazon MQ: `aws mq describe-broker --broker-id <id>` returns `BrokerState=RUNNING`.
3. Verify target ARN resolves and resource policy grants invoke to
   `pipes.amazonaws.com` (Lambda, Step Functions, API Gateway) or the
   pipe role ARN (SQS, SNS, ECS task).
4. Verify DLQ (if configured): SQS queue exists in same region, queue
   policy allows the pipe role to `sqs:SendMessage`.
5. Verify enrichment (if configured): Lambda function state `Active`,
   Step Functions state machine state `ACTIVE`, API Gateway stage
   deployed, API Destination with active connection.
6. For MSK / self-managed Kafka: verify `AuthType` (`SASL_SCRAM_512_AUTH`,
   `SASL_SCRAM_256_AUTH`, `IAM`, `MTLS`, `NONE` — `NONE` rejected for
   non-local clusters) and `ConsumerGroupID` is unique.
7. For Amazon MQ: verify `Credentials` secret in Secrets Manager with
   `username`/`password` keys, broker state `RUNNING`.
