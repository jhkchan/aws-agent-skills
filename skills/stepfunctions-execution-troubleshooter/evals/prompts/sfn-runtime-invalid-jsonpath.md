# Eval prompt: sfn-runtime-invalid-jsonpath

Diagnose the following Step Functions execution failure. Walk the
States.Runtime decision tree and emit the standard VERDICT block
(INCIDENT, VERDICT, ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG,
REMEDIATION).

## Scenario

A Standard Step Functions workflow in `us-east-1` is failing on the
`EnrichOrder` state. State machine ARN:
`arn:aws:states:us-east-1:111111111111:stateMachine:order-pipeline`.

## Known facts

- `describe-execution` for the failing execution shows:
  - `status: FAILED`
  - `error: "States.Runtime"`
  - `cause: "An error occurred while executing the state 'EnrichOrder'."`
- `get-execution-history` for the failing execution shows the
  `StateEntered` event for `EnrichOrder` with `input`:
  ```json
  { "orderId": "ord-123", "customerId": "cust-9" }
  ```
- `describe-state-machine` for the `EnrichOrder` state shows:
  ```json
  {
    "Type": "Task",
    "Resource": "arn:aws:states:::lambda:invoke",
    "Parameters": {
      "OrderId.$": "$.order.orderId",
      "Customer.$": "$.customerId",
      "FunctionName": "enrich-fn"
    },
    "Next": "PersistOrder"
  }
  ```
- The upstream `EmitOrder` state uses `ResultPath: "$"` so its output
  replaces the entire payload — the `EnrichOrder` input shown above IS
  the upstream output.
- The Lambda function `enrich-fn` is healthy; no failures in its
  CloudWatch Logs (it was never invoked).

## Symptom

Every execution of `order-pipeline` fails on `EnrichOrder` with
`States.Runtime`, regardless of input.
