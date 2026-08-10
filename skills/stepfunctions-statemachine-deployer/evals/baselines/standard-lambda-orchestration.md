# Baseline (no-skill) response: standard-lambda-orchestration

This file captures what a generic assistant produces WITHOUT the
stepfunctions-statemachine-deployer skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, full Checklist,
Retry/Catch shape, scoped IAM policy derivation, ordered deploy commands).

---

Sure, here's a Step Functions state machine for your order pipeline. I'll
use the Standard type since you didn't specify high throughput needs.

```json
{
  "StartAt": "ValidateOrder",
  "States": {
    "ValidateOrder": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": { "FunctionName": "ValidateOrderFn" },
      "Next": "UpdateOrderRecord"
    },
    "UpdateOrderRecord": {
      "Type": "Task",
      "Resource": "arn:aws:states:::dynamodb:updateItem",
      "Parameters": { "TableName": "OrdersTable" },
      "Next": "ChargePayment"
    },
    "ChargePayment": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": { "FunctionName": "ChargePaymentFn" },
      "Retry": [{ "ErrorEquals": ["States.ALL"] }],
      "Next": "Done"
    },
    "Done": { "Type": "Succeed" }
  }
}
```

You can create it with:

```
aws stepfunctions create-state-machine --name order-pipeline \
  --definition file://def.json --role-arn arn:aws:iam::111111111111:role/order-pipeline-sfn-role
```

Make sure the role has lambda and DynamoDB permissions. I'd suggest using
`AmazonStepFunctionsFullAccess` for simplicity.
