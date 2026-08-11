# Eval: sync-apigateway-timeout-alignment

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — sync mode + API Gateway integration timeout 29000ms + alarm on ExecutionsTimedOut

## Prompt

Provision an Express workflow "checkout-api" (account
123456789012, region us-east-1) invoked synchronously from
API Gateway. Workflow p99 is 8 seconds. Attach CloudWatch
Logs at ALL level with includeExecutionData=true. The
execution role is scoped to lambda:InvokeFunction on
function:checkout-handler. Make sure the API Gateway
integration timeout is set correctly so the client does not
receive a 504 while the workflow is still running. Add an
alarm on ExecutionsTimedOut.
