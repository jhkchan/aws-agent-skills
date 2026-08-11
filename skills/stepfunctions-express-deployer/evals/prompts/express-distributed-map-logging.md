# Eval: express-distributed-map-logging

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Distributed Map + ALL-level logging + includeExecutionData + EventBridge + alarm

## Prompt

Provision an Express Workflow named "order-processor" in
account 123456789012, region us-east-1. The workflow uses a
Distributed Map with an S3 ItemReader (bucket "my-bucket",
key "input.json") and Lambda Task "process-item" per item,
MaxConcurrency 1000. Attach a CloudWatch Logs log group
/aws/states/order-processor at level ALL with
includeExecutionData=true and 30-day retention. The Lambda
handler is idempotent via IdempotencyKey from $$.Execution.Id.
Execution role scoped to lambda:InvokeFunction on the
process-item ARN and s3:GetObject on the input object.
Configure EventBridge to invoke the workflow every 5 minutes
with the EventBridge target role. Add an alarm on
ExecutionsFailed.
