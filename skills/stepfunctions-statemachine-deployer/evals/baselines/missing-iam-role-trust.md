# Baseline (no-skill) response: missing-iam-role-trust

This file captures what a generic assistant produces WITHOUT the
stepfunctions-statemachine-deployer skill loaded — the contrast that
proves the skill identifies the missing role/trust policy as a hard
PREREQUISITES_MISSING gate rather than fabricating a role ARN or
silently accepting a non-existent role.

---

Sure, here's a state machine for reporting.

```json
{
  "StartAt": "Task1",
  "States": {
    "Task1": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": { "FunctionName": "Fn1" },
      "Next": "Task2"
    }
    /* ... 4 Lambda Tasks ... */
  }
}
```

You can deploy with:

```
aws stepfunctions create-state-machine --name reporting-workflow \
  --definition file://def.json \
  --role-arn arn:aws:iam::111111111111:role/reporting-sfn-role
```

If the role doesn't exist yet, just create it via the IAM console. You
can use a basic Lambda execution role and add `AmazonStepFunctionsFullAccess`
to make things easier.
