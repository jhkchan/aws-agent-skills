# Error Handling (load on demand) — CloudFormation StackSet Deployer

API error handling deep dives moved verbatim from SKILL.md. Loaded on demand.

---

## Error handling (moved from SKILL.md)

### `StackInstance` status is `INOPERABLE`
- **SELF_MANAGED:** the execution role is missing or has a broken
  trust policy in that target account. Verify the role exists in
  the target account.
- **SERVICE_MANAGED:** an SCP is blocking CloudFormation in that
  account, or the account was removed from the OU. Verify OU
  membership: `aws organizations list-parents --child-id <account>`.

### `InvalidOperationException` on create-stack-set
- **SERVICE_MANAGED:** Organizations trusted access is not enabled.
  Run: `aws organizations enable-aws-service-access --service-principal cloudformation.amazonaws.com`.

### `InsufficientCapabilities` error
- Template creates IAM/macros but `--capabilities` was not passed.
  Add `CAPABILITY_IAM` (or `CAPABILITY_NAMED_IAM`, `CAPABILITY_AUTO_EXPAND`).

### StackSet drift status is `DRIFTED` and not reconciling
- **SERVICE_MANAGED + managed execution:** ensure
  `ManagedExecution.Active=true` and trigger `update-stack-set`.
- **SELF_MANAGED or managed execution off:** run
  `detect-stack-set-drift`, then `update-stack-instances` to reset.
