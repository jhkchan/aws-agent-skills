# Step Functions State Machine Auditor - diagnostic and pre-flight commands (load on demand)

> Moved verbatim from SKILL.md during progressive-disclosure restructure. Load on demand.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`UpdateStateMachine`, `DeleteStateMachine`, `StopExecution`), the
  auditor MUST emit:
  `CONFIRM: About to <action> on state machine <arn>. This affects
  <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- **Definition changes are unversioned.** `UpdateStateMachine` replaces
  the entire definition atomically — there is no rollback. Capture the
  current definition first:
  `aws stepfunctions describe-state-machine --state-machine-arn <arn> --output json > /tmp/<name>-backup-$(date +%s).json`

- **Role policy changes affect ALL state machines using that role.** An
  execution role may be shared across multiple state machines. Tightening
  the role for one workflow may break another. List dependents before
  modifying:
  `aws resourcegroupstaggingapi get-resources --resource-type-filters states:stateMachine --query "ResourceTagMappingList[].ResourceARN" --output text`
  then grep for the role ARN in each state machine's `roleArn`.

- **Express workflow logging changes take effect immediately for new
  executions** but do NOT retroactively log in-flight executions. Existing
  Express executions continue without logging until they complete.

- **Enabling X-Ray on a Standard workflow** requires the execution role to
  have `xray:PutTraceSegments` + `xray:PutTelemetryRecords`. Add these
  permissions BEFORE enabling tracing, or the first traced execution fails
  with `AccessDenied`.

- **Validate the ASL definition before pushing:**
  `aws stepfunctions validate-state-machine-definition --definition <file> --type STANDARD`
  This catches structural errors before they reach production. It does NOT
  catch missing-Catch or missing-TimeoutSeconds (the auditor does).

- Prefer additive changes (add a `Catch` block, add a `Retry` block) over
  destructive changes (rewriting the definition) — additive changes are
  reversible and lower-risk.

