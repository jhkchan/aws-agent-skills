# Eval prompt: standard-lambda-orchestration

Design a deployment plan for an AWS Step Functions Standard state machine.
Emit the standard VERDICT block (STATE_MACHINE_SPEC, VERDICT, ARCHITECTURE,
CHECKLIST, FINDINGS, DEPLOY_COMMANDS).

## Requirements

- Name: `order-pipeline`
- Region: us-east-1
- Account: 111111111111
- Type: STANDARD
- Workflow:
  1. `ValidateOrder` — Lambda invoke (function `ValidateOrderFn`, timeout 30s)
  2. `UpdateOrderRecord` — DynamoDB UpdateItem on `OrdersTable`
  3. `ChargePayment` — Lambda invoke (function `ChargePaymentFn`, timeout 60s)
  4. Terminal: Succeed
- Error handling:
  - `ChargePayment` needs Retry on `Lambda.ServiceException`,
    `Lambda.TooManyRequestsException` (3 attempts, 2s interval, 2.0 backoff)
    AND a Catch on `States.ALL` routing to `PaymentErrorHandler` with
    `ResultPath: "$.error"`.
  - `UpdateOrderRecord` needs Retry on
    `DynamoDB.ProvisionedThroughputExceededException` (5 attempts, 5s, 2.0
    backoff).
  - Every Task has an explicit `TimeoutSeconds`.
- Execution role: `order-pipeline-sfn-role` exists with a verified trust
  policy for `states.amazonaws.com`. Identity policy must scope to the
  Lambda and DynamoDB ARNs actually used.

Output the complete deployment plan including IAM identity policy
derivation and ordered deploy commands.
