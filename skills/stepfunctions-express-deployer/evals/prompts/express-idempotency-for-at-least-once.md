# Eval: express-idempotency-for-at-least-once

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — DynamoDB idempotency record + Lambda charge-card with IdempotencyKey

## Prompt

Provision an Express workflow "charge-card-flow" (account
123456789012, region us-east-1). The workflow calls Lambda
function "charge-card" which charges a credit card — this
MUST be idempotent because Express is at-least-once. Use
$$.Execution.Id as the idempotency key, persisted in
DynamoDB table "IdempotencyTable" BEFORE the charge. Attach
CloudWatch Logs at ALL level. Execution role scoped to
lambda:InvokeFunction and dynamodb:PutItem/GetItem on the
table. Workflow runs async via start-execution.
