# Worked Examples

Blocks moved verbatim from SKILL.md in the agentskills.io progressive-disclosure
restructure. No content changed; load when a SKILL.md pointer stub applies.

## Common patterns (moved from SKILL.md)

- **DynamoDB Streams → Lambda with filter + DLQ.** Filter pattern
  matches `dynamodb.NewImage.status.S = CONFIRMED`. Pipe role reads
  stream and invokes Lambda. DLQ catches records exceeding 3 retries
  or 1-hour age. Most common Pipe pattern.

- **Kinesis → Step Functions with batch windowing.** `MaximumBatchingWindowInSeconds=30`
  collects up to 100 records per invocation. Step Functions Express
  Workflow runs sync; failures retry up to 185 times. Use for
  stream-triggered orchestration.

- **SQS → Lambda without pipe-level DLQ.** Source SQS queue has its
  own DLQ via `RedrivePolicy` with `maxReceiveCount=5`. Pipe-level
  `DeadLetterConfig` ignored. The pipe just connects the queue to
  Lambda with batching.

- **MSK → AWS Batch target.** Kafka consumer group `pipe-batch-consumer`
  reads from `orders-events` topic; pipe submits a Batch job per batch
  for offline processing. Enables event-driven batch processing without
  a separate consumer service.

- **DynamoDB Streams → Lambda enrichment → Step Functions target.**
  Enrichment Lambda joins with customer data, returns transformed
  batch; Step Functions runs orchestration. Two permission grants
  needed: enrichment Lambda + target state machine.

## Output format — PIPE_SPEC template (moved from SKILL.md)

```text
PIPE_SPEC: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  Source: <type> <arn> (region <region>, state <ACTIVE|ENABLED|RUNNING>)
  Filter pattern: <none | JSON pattern>
  Enrichment: <none | Lambda/Step Functions/API Gateway/API Destination arn>
  Target: <type> <arn>
  Batch window: <seconds> seconds (ignored for SQS source)
  Batch size: <records>
  Record age: <seconds> (streaming sources only)
  Retry attempts: <count>
  DLQ: <arn> (pipe-level for streaming / source-queue-level for SQS)
CHECKLIST:
  [x] Source ARN resolves in region matching pipe
  [x] Source state ACTIVE / ENABLED / RUNNING
  [x] Filter pattern valid JSON (if specified)
  [x] Enrichment ARN resolves and grants pipe role invoke (if specified)
  [x] Target ARN resolves and grants pipe role invoke
  [x] Batch window 0-300 (ignored for SQS)
  [x] Batch size within source-specific cap
  [x] Record age 60-86400 (streaming sources only)
  [x] DLQ policy grants pipe role sqs:SendMessage
  [x] IAM role trust policy scoped to pipes.amazonaws.com with SourceAccount/SourceArn condition
FINDINGS:
  - [INFO] Estimated monthly cost: $0.50 base + $0.50 per million invocations + source throughput
  - [WARN] SQS source configured with pipe-level DeadLetterConfig — ignored, configure RedrivePolicy on source queue
DEPLOY_COMMANDS:
  <ordered list of aws pipes create-pipe commands and prerequisite IAM/DLQ setup>
```
