# Baseline (no-skill) response: express-timeout-exceeds-cap

This file captures what a generic assistant produces WITHOUT the
stepfunctions-statemachine-deployer skill loaded — the contrast that
proves the skill catches the Express 5-minute cap violation that a
generic assistant happily accepts.

---

Sure, here's your Express state machine.

```json
{
  "StartAt": "PrepareJob",
  "States": {
    "PrepareJob": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": { "FunctionName": "PrepareJobFn" },
      "Next": "RunBatch"
    },
    "RunBatch": {
      "Type": "Task",
      "Resource": "arn:aws:states:::ecs:runTask.sync",
      "Parameters": { /* ECS config */ },
      "TimeoutSeconds": 600,
      "Next": "Done"
    },
    "Done": { "Type": "Succeed" }
  }
}
```

Deploy:

```
aws stepfunctions create-state-machine --name long-running-express \
  --definition file://def.json --type EXPRESS \
  --role-arn arn:aws:iam::111111111111:role/long-running-express-sfn-role
```

Express is a great cost choice here. Let me know if you want to add
tracing.
