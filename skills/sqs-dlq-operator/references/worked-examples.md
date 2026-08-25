# Worked examples - SQS DLQ Operator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Worked example — replay via StartMessageMoveTask (COMPLETED)

```text
OPERATION: replay
VERDICT: COMPLETED
TARGET: prod-orders-dlq -> prod-orders (replay)
PRE_CHECKS:
  - [PASS] DLQ prod-orders-dlq exists, depth was 1247 messages
  - [PASS] Source prod-orders exists, listed via list-dead-letter-source-queues
  - [PASS] Source has active Lambda consumer (mapping uuid a1b2c3d4, BatchSize=10)
  - [PASS] Root cause fixed: consumer patched to handle malformed-JSON payload gracefully (deploy v1.4.2)
  - [PASS] VisibilityTimeout 60s >= Lambda p99 8s — no race
  - [PASS] ReportBatchItemFailures enabled on mapping
STEPS:
  1. Snapshot: aws cloudwatch get-metric-statistics (DLQ depth before replay: 1247)
  2. aws sqs start-message-move-task --source-arn arn:aws:sqs:us-east-1:111111111111:prod-orders-dlq --destination-arn arn:aws:sqs:us-east-1:111111111111:prod-orders --max-number-of-messages-per-second 100
  3. Poll: aws sqs list-message-move-tasks --source-arn arn:aws:sqs:us-east-1:111111111111:prod-orders-dlq
POST_VERIFY:
  - [PASS] list-message-move-tasks Status: COMPLETED, FilesMoved: 1247, FilesFailed: 0
  - [PASS] DLQ depth returned to 0 (ApproximateNumberOfMessagesVisible: 0)
  - [PASS] Source queue NumberOfMessagesReceived increased by ~1247 over replay window
  - [PASS] Consumer logs show no errors on replayed messages (patch confirmed working)
STATE: DLQ depth 0, source depth normal, replay task COMPLETED
NOTES:
  - Throttled to 100 msg/s (12.5s total) to avoid overwhelming Lambda concurrency.
  - FIFO dedup did not apply (Standard queue, no MessageDeduplicationId).
  - Monitor DLQ depth over next 24h — if messages re-accumulate, root cause was not fully fixed.
```

