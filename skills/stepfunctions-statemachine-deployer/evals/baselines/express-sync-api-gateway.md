# Baseline (no-skill) response: express-sync-api-gateway

This file captures what a generic assistant produces WITHOUT the
stepfunctions-statemachine-deployer skill loaded — the contrast that
proves the skill surfaces Express-specific concerns (idempotency,
mandatory logging, no X-Ray, no `.waitForTaskToken`).

---

Sure. Here's an Express state machine that backs your API Gateway
endpoint.

```json
{
  "StartAt": "ValidateCart",
  "States": {
    "ValidateCart": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": { "FunctionName": "ValidateCartFn" },
      "Next": "ChargePayment"
    },
    "ChargePayment": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": { "FunctionName": "ChargePaymentFn" },
      "Next": "UpdateOrderRecord"
    },
    "UpdateOrderRecord": {
      "Type": "Task",
      "Resource": "arn:aws:states:::aws-sdk:dynamodb:updateItem",
      "Parameters": { "TableName": "OrdersTable" },
      "Next": "Done"
    },
    "Done": { "Type": "Succeed" }
  }
}
```

Deploy:

```
aws stepfunctions create-state-machine --name checkout-express \
  --definition file://def.json --type EXPRESS \
  --role-arn arn:aws:iam::111111111111:role/checkout-sfn-role \
  --tracing-configuration enabled=true
```

You can enable X-Ray for tracing if you want distributed visibility.
