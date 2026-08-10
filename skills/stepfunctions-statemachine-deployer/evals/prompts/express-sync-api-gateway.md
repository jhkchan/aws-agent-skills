# Eval prompt: express-sync-api-gateway

Design a deployment plan for an AWS Step Functions Express state machine
that backs an API Gateway synchronous endpoint. Emit the standard VERDICT
block (STATE_MACHINE_SPEC, VERDICT, ARCHITECTURE, CHECKLIST, FINDINGS,
DEPLOY_COMMANDS).

## Requirements

- Name: `checkout-express`
- Region: us-east-1
- Account: 111111111111
- Type: EXPRESS, Synchronous (RequestResponse) — invoked via API Gateway
- Workflow:
  1. `ValidateCart` — Lambda invoke (`ValidateCartFn`, timeout 30s)
  2. `ChargePayment` — Lambda invoke (`ChargePaymentFn`, timeout 60s)
  3. `UpdateOrderRecord` — `arn:aws:states:::aws-sdk:dynamodb:updateItem`
     on `OrdersTable` (timeout 30s)
  4. Terminal: Succeed
- Error handling:
  - `ChargePayment` needs Retry on `Lambda.ServiceException`,
    `Lambda.TooManyRequestsException` (3 attempts, 2s, 2.0 backoff) AND
    Catch on `States.ALL` → `PaymentErrorHandler`.
  - `UpdateOrderRecord` needs Retry on
    `DynamoDB.ProvisionedThroughputExceededException` (5 attempts, 5s, 2.0
    backoff).
- Total expected runtime: < 30 seconds (well within API Gateway's 29s
  timeout and Express's 5-min cap).
- Execution role: `checkout-sfn-role` exists with trust policy for
  `states.amazonaws.com`. Identity policy must scope to the Lambda ARNs,
  the DynamoDB table ARN, and the CloudWatch Logs log group ARN.
- Logging: `level=ALL`, `includeExecutionData=true` to CloudWatch Logs
  log group `/aws/states/checkout-express`.

Output the complete deployment plan. Note any idempotency considerations
specifically tied to the chosen workflow type.
