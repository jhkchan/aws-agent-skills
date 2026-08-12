# Eval: missing-target-iam-role

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — target Lambda function does not exist AND caller lacks iam:PassRole

## Prompt

Create an EventBridge Scheduler schedule called my-job that
invokes Lambda function nonexistent-function every 5 minutes.
The function does not exist. Also, the caller does not have
iam:PassRole permission.
