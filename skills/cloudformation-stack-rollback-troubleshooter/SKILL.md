---
name: cloudformation-stack-rollback-troubleshooter
description: >-
  Diagnoses AWS CloudFormation stack rollback failures through a
  rollback-focused decision tree: UPDATE_ROLLBACK_FAILED state requiring
  ContinueUpdateRollback, custom resource Lambda timeout (no response to
  CFN signal — the #1 rollback blocker), nested stack rollback cascade,
  IAM policy replacement requiring full resource recreation, drift
  detection blocking clean rollback, stack policy preventing rollback
  update, dependent resources in-use (cannot delete), RDS/Aurora
  snapshot requirement before rollback, DisableRollback after partial
  failure, rollback vs update-with-rollback semantics, stack delete vs
  rollback, and ChangeSet preview before rollback. Walks symptoms to a
  verified root cause with evidence-backed probes; emits
  ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted stack events and describe-stacks output. Live-account diagnosis uses aws cloudformation describe-stacks, describe-stack-events, describe-stack-resources, get-template-summary, describe-stack-resource-drifts, get-stack-policy, create-change-set, execute-change-set, continue-update-rollback, list-change-sets, and aws lambda get-function-configuration for custom resource verification (AWS CLI v2, SSO or key-based credentials).
keywords:
- CloudFormation
- stack rollback
- UPDATE_ROLLBACK_FAILED
- rollback failure
- ContinueUpdateRollback
- custom resource timeout
- custom resource Lambda
- nested stack rollback
- nested stack cascade
- IAM replacement
- drift detection
- stack drift
- stack policy
- dependent resources
- RDS snapshot
- Aurora snapshot
- DisableRollback
- ChangeSet
- rollback vs update
- stack delete
- CloudFormation troubleshooting
tags:
- cloudformation
- devtools
- troubleshooting
- rollback
- update-rollback-failed
- custom-resource
- nested-stack
- drift
- stack-policy
- changeset
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: DevTools
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing a CloudFormation stack rollback failure where the root cause may be custom resource Lambda timeout (no CFN signal — the #1 blocker), UPDATE_ROLLBACK_FAILED state requiring ContinueUpdateRollback, nested stack rollback cascade, IAM policy replacement requiring full recreation, drift detection blocking clean rollback, stack policy Deny preventing rollback update, dependent resources in-use (cannot delete), RDS/Aurora snapshot requirement, DisableRollback after partial failure, or rollback vs update-with-rollback confusion — walking the symptom to the failed resource and layer with verify commands, validating why a stack rollback failed, or triaging a "stack stuck in UPDATE_ROLLBACK_FAILED" page where the root cause is a specific resource that cannot be rolled back, not the stack itself.
  when_not_to_use: Initial CloudFormation deployment failures (use cloudformation-stack-troubleshooter), CloudFormation drift posture audits (use cloudformation-drift-troubleshooter), Terraform or CDK-level debugging (use the IaC tool's own diagnostics), or IAM policy authoring (use iam-least-privilege-advisor). This skill diagnoses rollback failures; it does not author templates or audit steady-state drift posture.
  activation_triggers:
  - CloudFormation UPDATE_ROLLBACK_FAILED
  - CloudFormation rollback failed
  - stack stuck UPDATE_ROLLBACK_FAILED
  - ContinueUpdateRollback
  - custom resource Lambda timeout CloudFormation
  - custom resource no response CloudFormation
  - nested stack rollback cascade
  - CloudFormation rollback cascade
  - IAM replacement rollback CloudFormation
  - drift blocking rollback CloudFormation
  - stack policy preventing rollback
  - dependent resources cannot delete CloudFormation
  - RDS snapshot rollback CloudFormation
  - Aurora snapshot rollback
  - DisableRollback CloudFormation
  - ChangeSet rollback preview
  - rollback vs update CloudFormation
  - stack delete vs rollback
  - diagnose CloudFormation rollback
  invocation_schema: 'Input: either (a) a rollback failure symptom description (stack status, StackId, error event message from describe-stack-events), optionally paired with the stack configuration (describe-stacks output, template summary, recent events), OR (b) a StackName or StackId plus the specific resource that failed to roll back for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {UPDATE_ROLLBACK_FAILED, CUSTOM_RESOURCE_TIMEOUT, NESTED_STACK_CASCADE, IAM_REPLACEMENT, DRIFT_DETECTION, STACK_POLICY_BLOCKING, DEPENDENT_RESOURCE_IN_USE, RDS_SNAPSHOT_REQUIRED, DISABLE_ROLLBACK_PARTIAL, CHANGESET_REJECTED, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline symptom classification):\nSymptom: \"CloudFormation stack prod-infrastructure is stuck in\nUPDATE_ROLLBACK_FAILED after a failed update. The stack event shows\n'CustomResource' timed out waiting for response from the Lambda\nfunction. I need to unblock the rollback.\"\nStackName: prod-infrastructure\nStackStatus: UPDATE_ROLLBACK_FAILED\nStackId: arn:aws:cloudformation:us-east-1:111111111111:stack/prod-infrastructure/abc-123\nFailedResource: Custom::AppConfig (LogicalId: AppConfigCustomResource)\nErrorEvent: \"Custom resource failed: Provider Lambda function timed out\n  (60s) without sending a response to the CloudFormation signal URL\""
---

# CloudFormation Stack Rollback Troubleshooter

## Quick start

- **Symptom → layer map (first plausible match drives the first probe):**
  `UPDATE_ROLLBACK_FAILED` state → UPDATE_ROLLBACK_FAILED (requires
  ContinueUpdateRollback); custom resource timeout in events →
  CUSTOM_RESOURCE_TIMEOUT (the #1 rollback blocker); nested stack in
  events → NESTED_STACK_CASCADE; IAM resource with `Replacement: True`
  → IAM_REPLACEMENT; drift detected → DRIFT_DETECTION; stack policy
  Deny → STACK_POLICY_BLOCKING; "Cannot delete: in use" →
  DEPENDENT_RESOURCE_IN_USE; RDS/Aurora in template →
  RDS_SNAPSHOT_REQUIRED.
- **UPDATE_ROLLBACK_FAILED requires ContinueUpdateRollback.** A stack
  in `UPDATE_ROLLBACK_FAILED` state cannot be updated normally — the
  only forward paths are `continue-update-rollback` (retry the rollback
  optionally skipping specific resources) or deleting the stack.
  Operators who try `update-stack` get a `ValidationError`.
- **Custom resource Lambda timeout is the #1 rollback blocker.** When
  a custom resource's provider Lambda fails to send a SUCCESS/FAILED
  response to the CFN signal URL (timeout, crash, wrong URL),
  CloudFormation waits up to 1 hour, then fails. The rollback then
  fails because CFN can't delete or update the custom resource — it's
  still "waiting." Use `continue-update-rollback --resources-to-skip`
  to bypass the stuck resource.
- **Nested stack rollback cascades.** When a parent stack rolls back,
  each child stack rolls back independently. A child stuck in
  `UPDATE_ROLLBACK_FAILED` blocks the parent. The child must be fixed
  first (ContinueUpdateRollback on the child), then the parent.
- **IAM replacement is irreversible during rollback.** Changing a
  property with `UpdateBehavior: Replacement` on an IAM resource
  creates a new resource and deletes the old. The old resource's
  deletion can fail if it's still attached — the rollback then fails.
- **Drift blocks clean rollback.** If a resource has been modified
  outside CloudFormation, the rollback may fail because the expected
  (template) state doesn't match the actual (drifted) state. Run
  `detect-stack-drift` and review before retrying rollback.

## Mindset

A CloudFormation rollback failure is almost always one specific resource
that cannot be returned to its previous state. The stack is not broken
— one resource is stuck. Senior CloudFormation engineers do not retry
the entire rollback; they identify the specific resource from
`describe-stack-events`, understand why that resource's rollback failed
(custom resource timeout, dependent resource, drift, IAM replacement),
and fix or bypass that resource with `continue-update-rollback
--resources-to-skip`.

## Philosophy

Five behaviours separate a senior CloudFormation engineer from a
generalist on rollback incidents:

- **UPDATE_ROLLBACK_FAILED is a terminal state requiring a specific
  action.** A stack in this state cannot receive normal updates. The
  only forward paths are `continue-update-rollback` (retry, optionally
  skipping specific resources) or deleting the stack.

- **Custom resource timeout is the #1 rollback blocker by frequency.**
  Custom resources (`Custom::` type, `AWS::CloudFormation::CustomResource`)
  rely on a provider Lambda to send SUCCESS/FAILED to a pre-signed S3
  URL. If the Lambda times out, crashes, or sends to the wrong URL,
  CloudFormation waits up to 1 hour, then fails. During rollback, the
  same custom resource must be deleted or updated — and the same
  timeout/crash recurs.

- **Nested stack rollback cascades from child to parent.** When a parent
  update triggers a child update that fails, the parent rolls back. The
  parent's rollback includes rolling back the child. If the child is
  stuck in `UPDATE_ROLLBACK_FAILED`, the parent's rollback also fails.
  Always fix the deepest child first.

- **IAM replacement is irreversible during rollback.** Changing an IAM
  resource property with `Replacement: True` creates a new resource and
  deletes the old. The old resource's deletion fails if any entity
  still assumes it. Always check `get-template-summary` for
  `Replacement: True` on IAM resources before deploying.

- **Stack policy and drift are silent rollback blockers.** A stack
  policy with `Deny` on `Update:Replace` or `Update:Delete` prevents
  CloudFormation from modifying resources during rollback. Drift means
  the expected state doesn't match reality. Both produce generic error
  messages — always check `get-stack-policy` and
  `describe-stack-resource-drifts` proactively.

## Quick reference — rollback triage table

| Stack status / event pattern | Most likely layer | First probe |
|---|---|---|
| `UPDATE_ROLLBACK_FAILED` | UPDATE_ROLLBACK_FAILED | `describe-stack-events` for the blocking resource |
| Custom resource timeout; "timed out waiting for response" | CUSTOM_RESOURCE_TIMEOUT | Lambda logs; Lambda Timeout config |
| `AWS::CloudFormation::Stack` (nested) in failed events | NESTED_STACK_CASCADE | `describe-stacks` on child; child status |
| IAM resource `Replacement: True`; deletion failed | IAM_REPLACEMENT | `get-template-summary`; `iam list-attached-role-policies` |
| "Resource not in expected state" / drift | DRIFT_DETECTION | `describe-stack-resource-drifts` |
| "Action not allowed by stack policy" | STACK_POLICY_BLOCKING | `get-stack-policy` |
| "Cannot delete: in use" / "dependent resources" | DEPENDENT_RESOURCE_IN_USE | `describe-stack-resources` for dependencies |
| RDS/Aurora cluster deletion failed | RDS_SNAPSHOT_REQUIRED | `rds describe-db-snapshots`; `DeletionPolicy` |
| Partial failure; `DisableRollback: true` was set | DISABLE_ROLLBACK_PARTIAL | `describe-stacks` DisableRollback |
| ChangeSet create/execute rejected | CHANGESET_REJECTED | `describe-change-set` |
| None of the above | INSUFFICIENT_DATA → escalate | AWS Health `describe-events` |

## Pre-flight: stack state and gather-info gate

```bash
# 1. Stack status and parameters
aws cloudformation describe-stacks \
  --stack-name <name-or-arn> --output json

# 2. Stack events (the specific resource that failed to roll back)
aws cloudformation describe-stack-events \
  --stack-name <name-or-arn> --output json | \
  jq '.StackEvents[] | select(.ResourceStatus | test("FAILED|ROLLBACK"))'

# 3. Stack policy (Deny rules that block rollback)
aws cloudformation get-stack-policy \
  --stack-name <name-or-arn> --output json

# 4. Drift detection (resources that drifted from template)
aws cloudformation describe-stack-resource-drifts \
  --stack-name <name-or-arn> --output json | \
  jq '.StackResourceDrifts[] | select(.StackResourceDriftStatus != "IN_SYNC")'

# 5. Template summary (resources with Replacement: True)
aws cloudformation get-template-summary \
  --stack-name <name-or-arn> --output json
```

If the input is malformed (missing StackName, absent stack status, no
error events), emit INSUFFICIENT_DATA with the missing pieces
(StackName/StackId, StackStatus, ResourceStatusReason from the most
recent FAILED event).

## Process — Rollback diagnostic decision tree

The tree is symptom-driven. Pick the entry point based on the stack
status and event pattern, then walk the probes in order. **Never emit
ROOT_CAUSE_IDENTIFIED without a failing probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change rollback diagnosis

- **`continue-update-rollback --resources-to-skip` is the canonical fix
  for UPDATE_ROLLBACK_FAILED.** It retries the rollback from the point
  of failure. Resources listed in `--resources-to-skip` are marked as
  successfully rolled back without CloudFormation touching them — they
  become orphaned (still exist physically but CFN no longer tracks them).

- **Custom resources have a 1-hour CloudFormation timeout, separate
  from the Lambda's own Timeout.** If the Lambda times out at 3s,
  CloudFormation still waits the full hour before failing. Always check
  both the Lambda's Timeout and the CFN event timestamp.

- **Nested stacks are independent stacks.** A child in
  `UPDATE_ROLLBACK_FAILED` must be fixed with its own
  `continue-update-rollback` before the parent can retry.

- **`DeletionPolicy: Retain` and `UpdateReplacePolicy` change rollback
  behaviour.** `Retain` prevents resource deletion during rollback
  (resource may be orphaned). `UpdateReplacePolicy` controls what
  happens to the old resource during a replacement-driven update.

- **Drift detection must be initiated manually.** CloudFormation does
  not continuously monitor drift. Always run `detect-stack-drift` then
  `describe-stack-resource-drifts` proactively during rollback diagnosis.

- **ChangeSet is the safe preview before a rollback retry.** Creating a
  ChangeSet with the previous template shows exactly which resources
  will change (Add/Modify/Remove) before executing — especially useful
  for IAM replacement or dependent resource scenarios.

- **`DisableRollback: true` means CloudFormation did NOT roll back.**
  The stack stays post-failure with successfully-created resources in
  place. The operator must manually clean up or fix the stack.

### Step 1: Symptom entry — pick the diagnostic branch

| Symptom | Branch |
|---|---|
| Stack in `UPDATE_ROLLBACK_FAILED`; no specific resource identified | Step 2 |
| Custom resource in failed events; "timed out" or "no response" | Step 3 |
| `AWS::CloudFormation::Stack` (nested) in failed events | Step 4 |
| IAM resource deletion/recreation failed during rollback | Step 5 |
| "Resource not in expected state" or drift in events | Step 6 |
| "Action not allowed by stack policy" in events | Step 7 |
| "Cannot delete" / "in use" / "has dependent" in events | Step 8 |
| RDS/Aurora deletion failed | Step 9 |
| Stack has `DisableRollback: true` | Step 10 |
| ChangeSet was rejected | Step 11 |
| None of the above | Step 12 |

### Step 2: UPDATE_ROLLBACK_FAILED — identify the blocking resource

```bash
aws cloudformation describe-stack-events \
  --stack-name <name-or-arn> --output json | \
  jq '.StackEvents[] | select(.ResourceStatus | test("FAILED")) | \
      {Timestamp, LogicalResourceId, ResourceType, ResourceStatusReason}'
```

The most recent `UPDATE_FAILED` or `DELETE_FAILED` event names the
blocking resource; `ResourceStatusReason` contains the error message.
Jump to the branch matching the resource type and error.

If the operator's goal is to unblock immediately, `continue-update-rollback
--resources-to-skip <LogicalResourceId>` bypasses the stuck resource. But
always diagnose first.

### Step 3: CUSTOM_RESOURCE_TIMEOUT — the #1 rollback blocker

Symptom: stack events show a `Custom::` or
`AWS::CloudFormation::CustomResource` with `UPDATE_FAILED` or
`DELETE_FAILED` and the reason includes "timed out," "no response," or
"Provider returned error."

```bash
# Identify the provider Lambda (ServiceToken)
aws cloudformation describe-stack-resource \
  --stack-name <name> --logical-resource-id <custom-resource-id> \
  --output json | jq '.StackResourceDetail'

# Check the Lambda's logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/<provider-lambda> \
  --start-time $(date -d '-2 hours' +%s)000 \
  --filter-pattern '"Task timed out" OR "ERROR" OR "cfnresponse"' \
  --output json
```

Common custom resource failure patterns:

| Pattern | Cause |
|---|---|
| Lambda timed out (default 3s) | Provider Timeout too low; raise to 30-60s. |
| "No response received" | Lambda sent response to wrong URL, or didn't call `cfnresponse.send`. |
| "Provider function not found" | ServiceToken (Lambda ARN) was deleted or wrong region. |
| Works on CREATE, fails on DELETE | Provider doesn't handle `RequestType: Delete`. |
| Works on UPDATE, fails on ROLLBACK | Provider doesn't handle `RequestType: Update` with old properties. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: CUSTOM_RESOURCE_TIMEOUT`.

Fixes: raise the Lambda Timeout; ensure it handles all `RequestType`
values and calls `cfnresponse.send`; or bypass with
`--resources-to-skip`.

### Step 4: NESTED_STACK_CASCADE — child stack blocks parent

Symptom: stack events show `AWS::CloudFormation::Stack` (nested) with
`UPDATE_FAILED` or `UPDATE_ROLLBACK_FAILED`.

```bash
# Get child stack ARN and status
aws cloudformation describe-stack-resource \
  --stack-name <parent> --logical-resource-id <nested-stack-id> \
  --output json | jq '.StackResourceDetail.PhysicalResourceId'

aws cloudformation describe-stacks --stack-name <child-arn> --output json | \
  jq '.Stacks[0].StackStatus'
```

If the child is `UPDATE_ROLLBACK_FAILED`, fix the child first: diagnose
the child's blocking resource (recurse through Steps 2-11 for the child),
run `continue-update-rollback` on the child, then on the parent.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: NESTED_STACK_CASCADE`.

### Step 5: IAM_REPLACEMENT — replacement can't be rolled back

Symptom: stack events show an IAM resource with `DELETE_FAILED` during
rollback. The error mentions "cannot delete" or "is attached to."

```bash
# Check if old IAM resource is still in use
aws iam list-attached-role-policies --role-name <old-role> --output json
aws iam list-instance-profiles-for-role --role-name <old-role> --output json

# Check for Replacement: True on IAM types
aws cloudformation get-template-summary \
  --stack-name <name> --output json | \
  jq '.ResourceTypes[] | select(.ResourceType | test("IAM"))'
```

The old IAM resource's deletion fails if it has active sessions, is
attached to instance profiles, or the policy is attached to principals.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: IAM_REPLACEMENT`.

Fixes: detach old role from profiles/policies; wait for sessions to
expire; bypass with `--resources-to-skip`. For future: use
`UpdateReplacePolicy: Retain`.

### Step 6: DRIFT_DETECTION — drifted resources block rollback

Symptom: stack events show "Resource not in expected state" or rollback
fails on a manually-modified resource.

```bash
aws cloudformation detect-stack-drift --stack-name <name> --output json
aws cloudformation describe-stack-resource-drifts \
  --stack-name <name> --output json | \
  jq '.StackResourceDrifts[] | select(.StackResourceDriftStatus != "IN_SYNC")'
```

Drifted resources that block rollback include: Security Groups with
manually-added rules, IAM roles with manually-attached policies, S3
buckets with changed settings, DynamoDB tables with changed billing.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: DRIFT_DETECTION`.

Fixes: re-sync the drifted resource (revert to match template, or update
template to match reality); bypass with `--resources-to-skip`.

### Step 7: STACK_POLICY_BLOCKING — Deny rules prevent rollback

Symptom: stack events show "Action not allowed by stack policy."

```bash
aws cloudformation get-stack-policy --stack-name <name> --output json
```

A stack policy with `Deny` on `Update:Replace`, `Update:Delete`, or
`Update:Modify` prevents CloudFormation from modifying those resources
even during rollback.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: STACK_POLICY_BLOCKING`.

Fix: temporarily grant an `Allow` override for the specific resource
during the rollback, then restore the protective policy:

```bash
aws cloudformation set-stack-policy --stack-name <name> \
  --stack-policy-body file://temp-allow-all.json --profile <p>
aws cloudformation continue-update-rollback --stack-name <name> --profile <p>
# After rollback: restore original policy
aws cloudformation set-stack-policy --stack-name <name> \
  --stack-policy-body file://original-policy.json --profile <p>
```

### Step 8: DEPENDENT_RESOURCE_IN_USE — cannot delete in-use resource

Symptom: stack events show `DELETE_FAILED` with "Cannot delete" or
"resource is in use."

```bash
aws cloudformation describe-stack-resources \
  --stack-name <name> --output json | \
  jq '.StackResources[] | {LogicalResourceId, PhysicalResourceId, ResourceType}'
```

Common patterns: Security Groups blocked by ENIs/instances; IAM Roles
blocked by active sessions; S3 Buckets blocked by objects; RDS Subnet
Groups blocked by instances; ALB blocked by listeners/targets.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: DEPENDENT_RESOURCE_IN_USE`.

Fixes: remove the dependency manually (delete ENI, detach role, empty
bucket); bypass with `--resources-to-skip`.

### Step 9: RDS_SNAPSHOT_REQUIRED — RDS/Aurora snapshot before deletion

Symptom: stack events show `DELETE_FAILED` on RDS with "Cannot delete
without final snapshot."

```bash
aws cloudformation get-template --stack-name <name> --output json | \
  jq '.TemplateBody.Resources.<RdsId>.DeletionPolicy // "Delete"'

aws rds describe-db-cluster-snapshots \
  --db-cluster-identifier <id> --output json 2>/dev/null
```

If `DeletionPolicy: Snapshot`, CFN tries to create a final snapshot
before deleting. If the snapshot fails (name conflict, storage full),
deletion fails.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: RDS_SNAPSHOT_REQUIRED`.

Fixes: manually create the final snapshot then retry; or set
`DeletionPolicy: Delete` for non-production; or bypass with
`--resources-to-skip`.

### Step 10: DISABLE_ROLLBACK_PARTIAL — no rollback occurred

Symptom: `describe-stacks` shows `DisableRollback: true` and the stack
status is `CREATE_FAILED` or `UPDATE_FAILED`. Resources created before
the failure still exist.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: DISABLE_ROLLBACK_PARTIAL`.

Fixes: diagnose the original failure resource; fix the template/resource
then `update-stack` to retry; or `delete-stack` to clean up.

### Step 11: CHANGESET_REJECTED — ChangeSet validation failed

```bash
aws cloudformation describe-change-set \
  --stack-name <name> --change-set-name <id> --output json | \
  jq '{Status, StatusReason, Changes[].ResourceChange}'
```

Common causes: template syntax error, circular dependency, resource
limit exceeded (500 per stack), nested child template errors.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: CHANGESET_REJECTED`.

Fix: fix the template error, create a new ChangeSet, review, execute.

### Step 12: INSUFFICIENT_DATA / escalate

If no probe produced a positive match, emit INSUFFICIENT_DATA with the
specific missing pieces, OR escalate to AWS Support if a regional
CloudFormation event is present in `aws health describe-events`.

## Output format

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
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <stack> in <region>. Proceed?
  (yes/no)"
```

### Worked example — Custom resource timeout blocking rollback

```text
TARGET: prod-infrastructure
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The stack is in UPDATE_ROLLBACK_FAILED. The blocking resource is
  Custom::AppConfig (LogicalId: AppConfigCustomResource). The provider
  Lambda function timed out at 3s while processing a Delete request during
  rollback. CloudFormation waited the full hour, then failed. The Lambda's
  logs show "Task timed out after 3.00 seconds" with the last line
  "Processing Delete request for AppConfig."
LAYER: CUSTOM_RESOURCE_TIMEOUT
EVIDENCE:
  - Symptom: stack prod-infrastructure is UPDATE_ROLLBACK_FAILED.
    describe-stack-events shows AppConfigCustomResource with
    DELETE_FAILED: "Custom Resource timed out waiting for provider."
  - Probe: aws logs filter-log-events on the provider Lambda returns
    "Task timed out after 3.00 seconds" — the Lambda started processing
    but didn't finish within 3 seconds.
  - Probe: aws lambda get-function-configuration returns Timeout: 3.
  - Passing: no nested stacks; no IAM Replacement: True; no drift;
    stack policy allows all updates.
REMEDIATION:
  1. Immediate unblock: bypass the stuck custom resource:
     aws cloudformation continue-update-rollback \
       --stack-name prod-infrastructure \
       --resources-to-skip AppConfigCustomResource --profile <p>
  2. Fix the provider Lambda: raise Timeout to 30s and ensure it
     handles RequestType: Delete:
     aws lambda update-function-configuration \
       --function-name appconfig-custom-resource-provider \
       --timeout 30 --profile <p>
CONFIRM: Before running continue-update-rollback, emit and await:
  "CONFIRM: About to continue-update-rollback on prod-infrastructure,
   skipping AppConfigCustomResource. The custom resource may be
   orphaned. Proceed? (yes/no)"
```

Additional worked examples (nested stack cascade, stack policy blocking)
appear in `examples/README.md`.

## Anti-Patterns — NEVER

- NEVER run `continue-update-rollback` without first identifying the
  specific blocking resource from `describe-stack-events`.

- NEVER run `--resources-to-skip` without warning the operator that
  skipped resources become orphaned — they still exist physically and
  may incur charges.

- NEVER try `update-stack` on a stack in `UPDATE_ROLLBACK_FAILED` state.
  Only `continue-update-rollback` and `delete-stack` are valid.

- NEVER delete a nested child stack's resources directly while the parent
  is in `UPDATE_ROLLBACK_FAILED`. Fix the child first, then the parent.

- NEVER assume the custom resource's provider Lambda handles all
  RequestTypes. Create-only providers are the most common rollback
  blocker — they don't handle Delete.

- NEVER change IAM resource properties with `Replacement: True` without
  checking `get-template-summary` first. IAM replacements delete the old
  resource — if it's in use, the rollback fails.

- NEVER set `DeletionPolicy: Delete` on production RDS/Aurora without a
  backup strategy. Use `DeletionPolicy: Snapshot`.

- NEVER ignore drift. A stack with drifted resources may fail rollback
  even if drift hasn't been formally detected. Always run
  `detect-stack-drift` proactively.

- NEVER leave a temporary `Allow` stack policy in place after a rollback.
  Always restore the original protective policy.

- NEVER conflate `delete-stack` with rollback. `delete-stack` removes all
  resources; rollback returns them to the previous template state.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`continue-update-rollback`, `set-stack-policy`, `delete-stack`,
  `execute-change-set`), emit and await operator approval.

- **Read-only first.** Every probe is read-only. Do not perform
  state-changing operations as diagnostic probes.

- **`continue-update-rollback`** is the primary fix. Resources in
  `--resources-to-skip` are marked as rolled back without CFN touching
  them (orphaned).

- **`set-stack-policy`** temporarily overrides protective policies.
  Always restore the original after the rollback.

- **`delete-stack`** is destructive — it removes all resources. Only use
  when the stack is unrecoverable.

- **IAM resource changes** with `Replacement: True` are irreversible
  during rollback. Verify no active dependencies before deploying.

## Domain

AWS CloudOps / CloudFormation Infrastructure as Code, Stack Lifecycle
Management, Rollback Diagnostics, and Nested Stack Orchestration.

## AWS documentation

- **ContinueUpdateRollback** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-continueupdaterollback.html
- **Stack updates** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks.html
- **Custom resources** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-custom-resources.html
- **Nested stacks** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-nested-stacks.html
- **Stack policy** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/protect-stack-resources.html
- **Drift detection** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html
- **DeletionPolicy / UpdateReplacePolicy** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-attribute-deletionpolicy.html
- **ChangeSets** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-changesets.html
- **AWS Health** — https://docs.aws.amazon.com/health/latest/ug/
