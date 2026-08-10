# Eval prompt: missing-iam-role-trust

Design a deployment plan for an AWS Step Functions state machine. Emit the
standard VERDICT block (STATE_MACHINE_SPEC, VERDICT, ARCHITECTURE,
CHECKLIST, FINDINGS, DEPLOY_COMMANDS).

## Requirements

- Name: `reporting-workflow`
- Region: us-east-1
- Account: 111111111111
- Type: STANDARD
- Workflow: 4 Lambda Tasks, each with Retry on
  `Lambda.ServiceException` (3 attempts, 2s, 2.0 backoff), Catch on
  `States.ALL` → `ErrorHandler`, and explicit `TimeoutSeconds`.
- Execution role: the operator mentions a role NAME
  `reporting-sfn-role` but cannot provide a role ARN. They have not
  created the role and have not configured a trust policy.

Output the appropriate deployment plan for this scenario. Do not invent a
role ARN; do not silently proceed with `create-state-machine` against a
non-existent role.
