# Eval prompt: lambda-reserved-concurrency-zero-review-required

Audit the Spot interruption pipeline health and emit the standard VERDICT
block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS, POST_VERIFY, NOTES).

Operation: audit-pipeline-health
ASG: prod-api-asg

```json
{
  "EventBridgeRule": {
    "Name": "spot-interruption-warning",
    "State": "ENABLED",
    "Target": "SQS queue spot-interruption-queue"
  },
  "SQSQueueHealth": {
    "ApproximateNumberOfMessagesVisible": "14 (climbing)",
    "ApproximateAgeOfOldestMessage": "340 seconds (stale — past 2-min window)",
    "DLQ": "spot-interruption-dlq (3 messages)"
  },
  "Lambda": {
    "FunctionName": "prod-spot-graceful-shutdown",
    "State": "Active",
    "Timeout": 90,
    "Runtime": "python3.12"
  },
  "LambdaConcurrency": {
    "ReservedConcurrentExecutions": 0
  },
  "LambdaCloudWatchMetrics": {
    "Throttles": "42 spikes (correlating with interruption events)",
    "Errors": 0,
    "Invocations": 0
  },
  "ALBTargetGroup": {
    "DeregistrationDelay": "300 (default — NOT tuned for Spot)"
  },
  "ASGLifecycleHook": "none configured"
}
```
