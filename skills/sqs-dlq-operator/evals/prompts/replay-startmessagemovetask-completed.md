# Eval prompt: replay-startmessagemovetask-completed

Verify the DLQ replay via StartMessageMoveTask and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, STATE, NOTES).

Operation: replay (post-verification after execution)
DLQ: prod-orders-dlq -> Source: prod-orders
Region: us-east-1. Account: 111111111111.

Root cause (now fixed): Lambda consumer threw NullReferenceException on
a new optional field "discountCode" added in API v2. Patched in deploy
v1.4.2 to handle null gracefully.

```json
{
  "PreReplay": {
    "DLQDepth": 1247,
    "maxReceiveCount": 5,
    "VisibilityTimeout": 60,
    "LambdaResponseTypes": ["ReportBatchItemFailures"]
  },
  "ExecutedCLI": {
    "command": "aws sqs start-message-move-task --source-arn arn:aws:sqs:us-east-1:111111111111:prod-orders-dlq --destination-arn arn:aws:sqs:us-east-1:111111111111:prod-orders --max-number-of-messages-per-second 100"
  },
  "PostExecutionChecks": {
    "list-message-move-tasks": {
      "Status": "COMPLETED",
      "FilesMoved": 1247,
      "FilesFailed": 0,
      "Duration": "13 seconds"
    },
    "dlq-depth-post-replay": 0,
    "source-received-increase": 1247,
    "lambda-errors-on-replayed": 0
  }
}
```
