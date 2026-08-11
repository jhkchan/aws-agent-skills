# Baseline (no-skill) — express-idempotency-for-at-least-once

> This is the response a model produces **without** the skill definition.
> It provisions the Express workflow with the charge-card Lambda but
> omits the idempotency key persistence — relying on a comment in the
> Lambda handler rather than an explicit pre-charge DynamoDB record.
> On an Express retry (at-least-once), the same input produces a
> second charge with no error signal. Generated for with-skill-vs-
> baseline comparison.

---

To create the Express workflow with the charge-card integration:

1. Create the IAM role with lambda:InvokeFunction on charge-card.

2. Create the state machine:
```bash
aws stepfunctions create-state-machine \
  --name charge-card-flow \
  --definition file://definition.json \
  --role-arn arn:aws:iam::123456789012:role/charge-card-flow-role \
  --type EXPRESS \
  --logging-configuration level=ALL,includeExecutionData=true
```

3. ASL definition:
```json
{
  "StartAt": "ChargeCard",
  "States": {
    "ChargeCard": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789012:function:charge-card",
      "Parameters": { "Amount.$": "$.amount" },
      "End": true
    }
  }
}
```

The Lambda handler is responsible for idempotency.
