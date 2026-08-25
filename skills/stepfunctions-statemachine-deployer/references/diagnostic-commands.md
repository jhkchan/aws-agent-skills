# Step Functions State Machine Deployer - diagnostic and verification commands (load on demand)

> Moved verbatim from SKILL.md during progressive-disclosure restructure. Load on demand.

## Verification commands (run after deployment)

```bash
# Verify the state machine was created with correct type
aws stepfunctions describe-state-machine \
  --state-machine-arn arn:aws:states:us-east-1:111111111111:stateMachine:order-checkout-express \
  --query '[name,type,roleArn,loggingConfiguration,tracingConfiguration]' \
  --output json

# Validate the definition (catches structural errors only, NOT missing
# Retry/Catch or missing TimeoutSeconds — those are caught by this skill)
aws stepfunctions validate-state-machine-definition \
  --definition file://definition.json --type EXPRESS

# Start a test execution (Express Sync)
aws stepfunctions start-sync-execution \
  --state-machine-arn arn:aws:states:us-east-1:111111111111:stateMachine:order-checkout-express \
  --input file://test-input.json

# Start a test execution (Standard or Express Async)
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:111111111111:stateMachine:order-pipeline \
  --input file://test-input.json

# Check execution status (Standard — 90 day history)
aws stepfunctions describe-execution --execution-arn <arn>

# For Express Async, find executions in CloudWatch Logs
aws logs filter-log-events \
  --log-group-name /aws/states/order-checkout-express \
  --filter-pattern '"status":"FAILED"'

# List activity workers (if using Activities)
aws stepfunctions get-activity-task --activity-arn <arn>

# Verify the execution role's identity policy scope
aws iam list-attached-role-policies --role-name <role-name>
aws iam list-role-policies --role-name <role-name>
aws iam get-role-policy --role-name <role-name> --policy-name <inline>

# Verify the trust policy includes states.amazonaws.com
aws iam get-role --role-name <role-name> \
  --query 'Role.AssumeRolePolicyDocument.Statement[?Principal.Service==`states.amazonaws.com`]'

# Verify X-Ray tracing is producing traces (Standard only)
aws xray get-trace-summaries --start-time $(date -d '-1 hour' +%s) \
  --end-time $(date +%s) --filter-expression 'service("states")'

# Redrive a failed Standard execution (November 2024+) instead of re-running
aws stepfunctions redrive-execution --execution-arn <arn>
```

## Pre-flight safety checks (run before any deployment CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-state-machine`, `update-state-machine`,
  `delete-state-machine`), the deployer MUST emit:
  `CONFIRM: About to <action> on state machine <name> in account <account>
  region <region>. Estimated monthly cost: <$X>. This is a non-reversible
  deployment. Proceed? (yes/no)`

- **Validate the definition BEFORE `create-state-machine`:**
  `aws stepfunctions validate-state-machine-definition --definition file://def.json --type STANDARD`
  This catches structural errors before they reach production. It does NOT
  catch missing-Catch or missing-TimeoutSeconds — the deployer skill does.

- **Verify the execution role trust policy:**
  `aws iam get-role --role-name <role> --query 'Role.AssumeRolePolicyDocument'`
  Confirm `Principal.Service: states.amazonaws.com` and
  `Action: sts:AssumeRole`.

- **Verify the identity policy scope:**
  `aws iam list-attached-role-policies` + `list-role-policies` +
  `get-role-policy`. Confirm no `Action: "*"` and no
  `Resource: "*"` (except for the few list/describe actions that require
  account-level scope).

- **Definition changes are unversioned.** `UpdateStateMachine` replaces
  the entire definition atomically — there is no rollback. Capture the
  current definition first:
  `aws stepfunctions describe-state-machine --state-machine-arn <arn> --output json > /tmp/<name>-backup-$(date +%s).json`

- **Cost estimate is MANDATORY for Express.** The deployer MUST emit a
  monthly cost estimate before deployment:
  - Express: $1.00 per 1M invocations + $0.00001667 per GB-sec duration
  - Standard: $0.025 per 1,000 state transitions
  - Distributed Map child executions bill separately per above

- **Tag everything at creation.** Use `--tags` on
  `create-state-machine`. Tags are the primary cost-allocation mechanism.
  Required tags: `Name`, `Environment`, `Team`, `CostCenter`.

- **Prefer additive changes** (add a Catch block, add a Retry block) over
  destructive changes (rewriting the definition) — additive changes are
  reversible and lower-risk.

