# Error handling - SQS DLQ Policy Auditor

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Remediation guidance

### For PUBLIC_ACCESS — Principal:"*" with no condition (Step 1)

1. **Immediately** remove the wildcard principal or add a STRONG condition
   (`aws:SourceArn`, `aws:SourceAccount`). Back up the policy first.
2. If the queue receives messages from a known S3 bucket or SNS topic,
   replace `Principal: "*"` with `Principal: "*"` + `Condition:
   ArnEquals: {aws:SourceArn: "<bucket/topic-arn>"}`.
3. If only specific accounts should access the queue, replace
   `Principal: "*"` with `Principal: {"AWS": "<account-role-arn>"}`.
4. **Assume breach.** Audit CloudTrail for `sqs:ReceiveMessage` /
   `sqs:SendMessage` from unexpected principals. Rotate any credentials
   that were in message payloads.

```bash
# Back up current policy
aws sqs get-queue-attributes --queue-url <url> \
  --attribute-names Policy --output json > /tmp/<queue>-policy-backup.json

# Apply scoped policy (add aws:SourceArn condition)
aws sqs set-queue-attributes --queue-url <url> \
  --attributes Policy=<new-scoped-policy-json>
```

### For NO_DLQ — no dead-letter queue configured (Step 2)

1. Create a DLQ (same account, same region, same FIFO type):
   ```bash
   aws sqs create-queue --queue-name <queue-name>-dlq.fifo \
     --attributes FifoQueue=true
   ```
2. Set the RedrivePolicy on the source queue:
   ```bash
   DLQ_ARN=$(aws sqs get-queue-attributes --queue-url <dlq-url> \
     --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)
   aws sqs set-queue-attributes --queue-url <source-url> \
     --attributes RedrivePolicy="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"5\"}"
   ```
3. Set the DLQ's MessageRetentionPeriod to 14 days (1209600 seconds):
   ```bash
   aws sqs set-queue-attributes --queue-url <dlq-url> \
     --attributes MessageRetentionPeriod=1209600
   ```

### For NO_ENCRYPTION — neither SSE-SQS nor SSE-KMS (Step 3)

1. Enable SSE-SQS (free, immediate, no application impact — no re-
   encryption needed because SQS encrypts transparently):
   ```bash
   aws sqs set-queue-attributes --queue-url <url> \
     --attributes SqsManagedSseEnabled=true
   ```
2. For customer-managed key control (compliance requirement), use SSE-KMS:
   ```bash
   aws sqs set-queue-attributes --queue-url <url> \
     --attributes KmsMasterKeyId=alias/my-sqs-key,KmsDataKeyReusePeriodSeconds=300
   ```
3. SSE-KMS requires the key policy to grant `kms:Decrypt` /
   `kms:GenerateDataKey*` to `sqs.<region>.amazonaws.com` service
   principal. Route to kms-key-policy-auditor for the key policy audit.

### For CONFIG_GAP — maxReceiveCount tuning (Steps 4a/44b)

1. Adjust maxReceiveCount (recommended: 5-10 standard, 5-15 FIFO):
   ```bash
   aws sqs set-queue-attributes --queue-url <url> \
     --attributes RedrivePolicy="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"5\"}"
   ```
2. If consumers are Lambda functions, verify the event source mapping's
   `VisibilityTimeout` is >= the function's p99 duration:
   ```bash
   aws lambda list-event-source-mappings --function-name <fn> \
     --query 'EventSourceMappings[].{Arn:EventSourceArn,VT:VisibilityTimeout}'
   ```

### For CONFIG_GAP — DLQ retention too short (Step 4c)

```bash
aws sqs set-queue-attributes --queue-url <dlq-url> \
  --attributes MessageRetentionPeriod=1209600
```

### For CONFIG_GAP — cross-account DLQ (Step 4d)

1. Verify the DLQ's RedriveAllowPolicy grants access to the source queue:
   ```bash
   aws sqs get-queue-attributes --queue-url <dlq-url> \
     --attribute-names RedriveAllowPolicy
   ```
2. If missing, set it:
   ```bash
   aws sqs set-queue-attributes --queue-url <dlq-url> \
     --attributes RedriveAllowPolicy='{"redrivePermission":"byQueue","sourceQueueArns":["arn:aws:sqs:us-east-1:111111111111:source-queue"]}'
   ```

### For OK

1. No remediation required for the current posture.
2. Recommend enabling DLQ CloudWatch alarms (ApproximateNumberOfMessagesDelayed
   > 0) for early poison-pill detection.
3. For FIFO queues, recommend monitoring message-group age via the
   `ApproximateAgeOfOldestMessage` CloudWatch metric.

