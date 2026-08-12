---
description: Diagnoses CloudFormation stack rollback failures (UPDATE_ROLLBACK_FAILED, custom resource timeout, nested stack cascade, IAM replacement, drift, stack policy blocking, dependent resources, RDS snapshot) through a rollback-focused diagnostic tree. Emits ROOT_CAUSE_IDENTIFIED with the specific blocking resource and layer.
nl_triggers:
  - "CloudFormation UPDATE_ROLLBACK_FAILED"
  - "CloudFormation rollback failed"
  - "stack stuck UPDATE_ROLLBACK_FAILED"
  - "ContinueUpdateRollback"
  - "custom resource Lambda timeout CloudFormation"
  - "custom resource no response CloudFormation"
  - "nested stack rollback cascade"
  - "CloudFormation rollback cascade"
  - "IAM replacement rollback CloudFormation"
  - "drift blocking rollback CloudFormation"
  - "stack policy preventing rollback"
  - "dependent resources cannot delete CloudFormation"
  - "RDS snapshot rollback CloudFormation"
  - "Aurora snapshot rollback"
  - "DisableRollback CloudFormation"
  - "ChangeSet rollback preview"
  - "rollback vs update CloudFormation"
  - "stack delete vs rollback"
  - "diagnose CloudFormation rollback"
  - "CloudFormation stuck rollback"
routes_to: cloudformation-stack-rollback-troubleshooter
---

# /aws:troubleshoot-cloudformation-rollback

Activate the `cloudformation-stack-rollback-troubleshooter` skill and
diagnose an AWS CloudFormation stack rollback failure through the
rollback-focused diagnostic tree.

## What it does

Reads a rollback failure symptom description (stack status, error event
from `describe-stack-events`, StackName/StackId) plus the stack
configuration, then walks the rollback-focused diagnostic tree to the
specific blocking resource and root cause:

1. **Pre-flight** — stack status (`describe-stacks`), failed events
   (`describe-stack-events`), stack policy (`get-stack-policy`), drift
   detection (`describe-stack-resource-drifts`), template summary
   (`get-template-summary` for Replacement: True on IAM resources).
2. **Symptom entry** — map the rollback failure pattern to one of:
   UPDATE_ROLLBACK_FAILED (identify the blocking resource), CUSTOM_RESOURCE_TIMEOUT
   (provider Lambda timed out — the #1 blocker), NESTED_STACK_CASCADE (child stack
   stuck), IAM_REPLACEMENT (old IAM resource can't be deleted), DRIFT_DETECTION
   (manual changes block rollback), STACK_POLICY_BLOCKING (Deny rules),
   DEPENDENT_RESOURCE_IN_USE (resource can't be deleted — has dependents),
   RDS_SNAPSHOT_REQUIRED (final snapshot needed), DISABLE_ROLLBACK_PARTIAL
   (no rollback occurred), CHANGESET_REJECTED (validation error).
3. **Layer-specific probes** —
   - Custom resource: Lambda logs (`filter-log-events` on the provider
     Lambda), Lambda Timeout config, cfnresponse protocol analysis.
   - Nested stack: child stack status (`describe-stacks` on the child
     ARN), child's own failed events.
   - IAM replacement: `get-template-summary` for Replacement: True,
     `iam list-attached-role-policies`, `iam list-instance-profiles-for-role`.
   - Drift: `detect-stack-drift`, `describe-stack-resource-drifts`.
   - Stack policy: `get-stack-policy`, action analysis (Deny on
     Update:Replace / Update:Delete).
   - Dependent resources: `describe-stack-resources`, identify reverse
     dependencies.
   - RDS snapshot: `rds describe-db-snapshots`, DeletionPolicy in
     template.
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with the specific blocking
   resource and failing probe) or INSUFFICIENT_DATA (needs operator
   input).

Emits a deterministic diagnostic block per target:

```text
TARGET: <stack-name or StackId>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <UPDATE_ROLLBACK_FAILED | CUSTOM_RESOURCE_TIMEOUT |
        NESTED_STACK_CASCADE | IAM_REPLACEMENT | DRIFT_DETECTION |
        STACK_POLICY_BLOCKING | DEPENDENT_RESOURCE_IN_USE |
        RDS_SNAPSHOT_REQUIRED | DISABLE_ROLLBACK_PARTIAL |
        CHANGESET_REJECTED | UNKNOWN>
EVIDENCE:
  - <observed symptom — stack status and error event>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
```

## When to invoke

Paste a rollback failure symptom and ask any of:

- "CloudFormation stack stuck in UPDATE_ROLLBACK_FAILED"
- "custom resource Lambda timed out during rollback"
- "nested stack rollback cascade — parent can't roll back"
- "IAM role deletion failed during CloudFormation rollback"
- "drift is blocking my CloudFormation rollback"
- "stack policy prevents rollback update"
- "RDS instance can't be deleted during rollback"
- "DisableRollback left my stack half-deployed"
- "ChangeSet rejected during rollback"

A bare stack name + any rollback status verb ("stack stuck", "rollback
failed", "UPDATE_ROLLBACK_FAILED") also routes here via the orchestrator.

## Inputs

- Symptom description: stack status, StackId, the specific error event
  from `describe-stack-events`, whether `continue-update-rollback` has
  been attempted.
- Stack configuration: StackName, StackStatus, DisableRollback,
  StackPolicyBody, DriftInformation, NestedStack resources.
- For live-account diagnosis: the specific resource that failed to
  roll back (LogicalResourceId, ResourceType, ResourceStatusReason).
  The skill uses `describe-stacks`, `describe-stack-events`,
  `describe-stack-resources`, `get-template-summary`, `get-stack-policy`,
  `describe-stack-resource-drifts`, `detect-stack-drift`,
  `describe-change-set`, `continue-update-rollback`, and `lambda
  get-function-configuration` (for custom resource provider diagnosis).

## Outputs

- One diagnostic block per target stack.
- Layer-specific LAYER value from the enumerated set.
- The specific blocking resource (LogicalResourceId) named in the
  evidence.
- Specific remediation: `continue-update-rollback --resources-to-skip`,
  provider Lambda fix, nested stack child fix, IAM dependency removal,
  drift re-sync, temporary stack policy override, manual RDS snapshot,
  or AWS Support escalation.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for CloudFormation rollback
  failures).
- `/aws:troubleshoot-cloudformation-stack` for initial deployment
  failures (not rollback failures).
- `/aws:troubleshoot-cloudformation-drift` for steady-state drift
  posture audits (not rollback-blocking drift).
- `/aws:troubleshoot-lambda-invocation` for diagnosing the custom
  resource provider Lambda when the rollback failure is a Lambda
  timeout or crash.
