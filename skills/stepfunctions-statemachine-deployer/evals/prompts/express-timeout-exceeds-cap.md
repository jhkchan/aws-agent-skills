# Eval prompt: express-timeout-exceeds-cap

Design a deployment plan for an AWS Step Functions state machine. Emit the
standard VERDICT block (STATE_MACHINE_SPEC, VERDICT, ARCHITECTURE,
CHECKLIST, FINDINGS, DEPLOY_COMMANDS).

## Requirements

- Name: `long-running-express`
- Region: us-east-1
- Account: 111111111111
- Type: EXPRESS (operator explicitly chose Express for cost reasons)
- Workflow:
  1. `PrepareJob` — Lambda invoke, timeout 30s
  2. `RunBatch` — `arn:aws:states:::ecs:runTask.sync` with
     `TimeoutSeconds: 600` (10 minutes) to wait for a long batch task
  3. Terminal: Succeed
- The rest of the workflow takes ~30 seconds. Total expected workflow
  runtime ~10.5 minutes.
- Execution role exists with trust for `states.amazonaws.com` and
  appropriate ECS/S3 permissions.

Output the appropriate deployment plan. Verify whether the requested
workflow type is compatible with the requested Task timeout. Do not
silently accept a configuration that cannot succeed at runtime.
