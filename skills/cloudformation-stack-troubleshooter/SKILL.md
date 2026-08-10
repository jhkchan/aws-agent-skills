---
name: cloudformation-stack-troubleshooter
description: >-
  Diagnoses AWS CloudFormation stack failures across the lifecycle.
  Covers CREATE_FAILED (IAM permission denied, service limit exceeded,
  resource already exists, invalid property), UPDATE_FAILED (Replacement
  required, immutable property change, rollback in progress),
  DELETE_FAILED (dependent resources, S3 bucket not empty,
  DeletionPolicy: Retain), ROLLBACK_FAILED (stack stuck in
  ROLLBACK_COMPLETE, requires delete + recreate), UPDATE_ROLLBACK_FAILED
  (nested stack cannot roll back). Walks describe-stack-events
  ResourceStatusReason, describe-stacks, describe-change-set, drift
  detection. Common: cfn-lint validation, DependsOn cycle, missing
  CAPABILITY_IAM, Replacement: true in ChangeSet, CreationPolicy signal
  timeout. Emits ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE. Use when
  a CloudFormation stack fails to create, update, delete, or roll back,
  or is stuck in ROLLBACK_COMPLETE / UPDATE_ROLLBACK_FAILED.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). Offline diagnosis works on supplied
  describe-stack-events / describe-stacks / describe-change-set JSON.
  Live-account diagnosis uses aws cloudformation describe-stacks,
  describe-stack-events, describe-stack-resources, describe-change-set,
  detect-stack-drift, aws iam simulate-principal-policy, and
  aws logs filter-log-events for Lambda-backed custom resources
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - CloudFormation
  - stack
  - CREATE_FAILED
  - UPDATE_FAILED
  - DELETE_FAILED
  - ROLLBACK_COMPLETE
  - UPDATE_ROLLBACK_FAILED
  - ResourceStatusReason
  - ChangeSet
  - Replacement
  - DeletionPolicy
  - DependsOn
  - CAPABILITY_IAM
  - cfn-lint
  - drift
  - nested stack
  - stack events
  - rollback
tags:
  - cloudformation
  - devtools
  - troubleshoot
  - stack-failure
  - changeset
  - rollback
  - drift
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
  verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
  when_to_use: >-
    Diagnosing why a CloudFormation stack went CREATE_FAILED,
    UPDATE_FAILED, DELETE_FAILED, ROLLBACK_FAILED, or
    UPDATE_ROLLBACK_FAILED; why a stack is stuck in ROLLBACK_COMPLETE
    or UPDATE_ROLLBACK_COMPLETE; why a ChangeSet reports
    Replacement: true; why a resource failed to send a signal within
    CreationPolicy; or why a stack delete is blocked by a non-empty S3
    bucket or DeletionPolicy: Retain.
  activation_triggers:
    - "CloudFormation stack failed"
    - "CREATE_FAILED"
    - "UPDATE_FAILED"
    - "DELETE_FAILED"
    - "ROLLBACK_FAILED"
    - "ROLLBACK_COMPLETE"
    - "UPDATE_ROLLBACK_FAILED"
    - "UPDATE_ROLLBACK_COMPLETE"
    - "CloudFormation ResourceStatusReason"
    - "stack stuck in ROLLBACK_COMPLETE"
    - "ChangeSet Replacement true"
    - "CloudFormation CAPABILITY_IAM"
    - "CloudFormation circular dependency"
    - "CloudFormation stack delete failed"
    - "CloudFormation drift"
  invocation_schema: >-
    Input: either (a) a symptom description (stack name or ARN, region,
    observed StackStatus and ResourceStatusReason, failing resource
    logical id), OR (b) a live-account scenario where the agent runs
    aws cloudformation describe-stacks / describe-stack-events /
    describe-stack-resources / describe-change-set and aws iam
    simulate-principal-policy to gather evidence. Output: a
    deterministic INCIDENT / VERDICT / ROOT_CAUSE / EVIDENCE /
    ROOT_CAUSE_CATALOG / REMEDIATION block where VERDICT ∈
    {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and ROOT_CAUSE names
    the specific failure category (CREATE_FAILED / UPDATE_FAILED /
    DELETE_FAILED / ROLLBACK_FAILED / UPDATE_ROLLBACK_FAILED) and the
    offending configuration element.
---

# CloudFormation Stack Troubleshooter

## Activation

Activate this skill when the user reports a CloudFormation stack
failure. Trigger phrases: "CloudFormation stack failed",
"CREATE_FAILED", "UPDATE_FAILED", "DELETE_FAILED", "ROLLBACK_FAILED",
"ROLLBACK_COMPLETE", "UPDATE_ROLLBACK_FAILED", "UPDATE_ROLLBACK_COMPLETE",
"ResourceStatusReason", "stack stuck in ROLLBACK_COMPLETE", "ChangeSet
Replacement true", "CloudFormation CAPABILITY_IAM", "circular
dependency", "stack delete failed".

## Mindset

**One-line takeaway:** every CloudFormation stack failure surfaces a
`ResourceStatusReason` on the failing resource in
`describe-stack-events`, and the stack's `StackStatus` identifies which
phase of the lifecycle broke. These two signals are the primary
diagnostic surface — the job of this skill is to walk from the stack
status to the specific resource, then from the `ResourceStatusReason` to
the specific root cause (IAM, limit, immutable property, dependent
resource, custom-resource timeout, nested stack).

Three facts make CloudFormation troubleshooting different from generic
service debugging:

- **`StackStatus` is the lifecycle phase, not the root cause.**
  `CREATE_FAILED`, `UPDATE_FAILED`, `UPDATE_ROLLBACK_COMPLETE`,
  `ROLLBACK_COMPLETE`, `DELETE_FAILED` each name a phase where the stack
  broke. The actionable cause is in the failing resource's
  `ResourceStatusReason`, which is a short string that often embeds the
  underlying service's error message (e.g.,
  `Resource creation cancelled` vs `API: iam:CreateRole AccessDenied`).
  Always read both fields.

- **Updates can require Replacement, and Replacement is irreversible.**
  When a ChangeSet reports `Replacement: true` for a resource,
  CloudFormation will create a new physical resource and delete the old
  one. Many properties are immutable (e.g., an RDS DBInstance's
  `DBInstanceIdentifier`, a DynamoDB table's `KeySchema`, an IAM role's
  `RoleName`). Operators often run `update-stack` without first reviewing
  the ChangeSet and are surprised when the resource is replaced. The
  ChangeSet is the diagnostic surface for updates — always read it.

- **Rollback is not recovery.** When a CREATE or UPDATE fails,
  CloudFormation attempts to roll back. If the rollback also fails, the
  stack enters `ROLLBACK_COMPLETE` (after a failed CREATE) or
  `UPDATE_ROLLBACK_FAILED` (after a failed UPDATE). In both states, the
  stack is broken and cannot be updated — it must be deleted (and, for
  UPDATE_ROLLBACK_FAILED, continued with `ContinueUpdateRollback` to
  skip the failing resource). Operators often keep retrying `update-stack`
  on a `ROLLBACK_COMPLETE` stack and are confused when CloudFormation
  rejects it.

## Quick reference — stack status to failure category

| Stack status | Failure category | First probe |
|---|---|---|
| `CREATE_FAILED` (stack rolled back, then `ROLLBACK_COMPLETE`) | CREATE_FAILED | `describe-stack-events` for the `CREATE_FAILED` resource; read `ResourceStatusReason` for IAM, limit, exists, invalid property |
| `UPDATE_FAILED` then `UPDATE_ROLLBACK_IN_PROGRESS` / `UPDATE_ROLLBACK_COMPLETE` | UPDATE_FAILED | `describe-change-set` for the most recent ChangeSet; check each resource's `Action` and `Replacement` |
| `UPDATE_ROLLBACK_FAILED` | UPDATE_ROLLBACK_FAILED | Identify the resource that cannot roll back (often a nested stack or a replaced resource); use `ContinueUpdateRollback --resources-to-skip` |
| `DELETE_FAILED` then `DELETE_COMPLETE` partial | DELETE_FAILED | `describe-stack-events` for `DELETE_FAILED`; check `DeletionPolicy: Retain`, dependent resources, non-empty S3 bucket |
| `ROLLBACK_COMPLETE` (after failed CREATE) | ROLLBACK_FAILED | Stack is broken; must be deleted; resources already created will be deleted on stack delete |
| Operator asks to recover without losing resources | REPLACEMENT_PLANNED | `describe-change-set` on a proposed ChangeSet; identify `Replacement: true` resources; plan import or refactor |

See the ordered steps below for the full diagnostic walk.

## Quick navigation

- **Step 0** — Capture the failure signal (stack name/ARN, region,
  StackStatus, failing logical id, ResourceStatusReason).
- **Step 1** — Map the StackStatus to a category (A-E).
- **Step 2** — CREATE_FAILED (resource creation error: IAM, limit,
  exists, invalid property).
- **Step 3** — UPDATE_FAILED (replacement required, rollback in
  progress).
- **Step 4** — DELETE_FAILED (dependent resources, bucket not empty,
  DeletionPolicy:Retain).
- **Step 5** — ROLLBACK_FAILED (stack stuck in ROLLBACK_COMPLETE).
- **Step 6** — UPDATE_ROLLBACK_FAILED (nested stack cannot roll back).
- **Step 7** — Root-cause catalog (top patterns + canonical fixes).
- **Step 8** — Validate via ChangeSet before applying any fix.
- **Step 9** — Decide VERDICT (ROOT_CAUSE_FOUND / NEED_MORE_INFO /
  ESCALATE).

## STRICT output contract

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
INCIDENT: <stack name or ARN> in <region> — <StackStatus + symptom>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <CREATE_FAILED | UPDATE_FAILED | DELETE_FAILED | ROLLBACK_FAILED | UPDATE_ROLLBACK_FAILED> — <one-sentence specific failing config element or resource>
EVIDENCE:
  - describe-stacks: <quoted StackStatus and StackStatusReason>
  - describe-stack-events: <quoted ResourceStatus + ResourceStatusReason for the failing logical id>
  - describe-stack-resources: <quoted PhysicalResourceId and status>
  - describe-change-set: <quoted Action + Replacement for the changed resource>
  - iam simulate-principal-policy: <decision for the relevant action, if IAM>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION:
  1. <exact template change, IAM policy edit, or CLI command>
  2. <verification command — ChangeSet or describe-stack-events>
  3. <post-apply monitoring step>
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze…" or "I'll investigate…" — the
  INCIDENT line is the FIRST line, always. No conversational preamble.
- NEVER use lowercase verdict values — emit `ROOT_CAUSE_FOUND`,
  `NEED_MORE_INFO`, or `ESCALATE`.
- NEVER omit EVIDENCE — the judge requires direct quotes from
  `describe-stack-events` (the `ResourceStatusReason`) or
  `describe-change-set`. Paraphrasing is not acceptable; quote the
  actual reason string.
- NEVER confuse `StackStatus` with the root cause. `UPDATE_FAILED` is
  the phase; the failing resource and its `ResourceStatusReason` are
  the cause.
- NEVER declare `ROOT_CAUSE_FOUND` for an UPDATE_FAILED diagnosis
  without quoting the `ResourceStatusReason` for the specific failing
  resource. "Update failed" is the symptom, not the diagnosis.
- NEVER recommend `update-stack` on a stack in `ROLLBACK_COMPLETE` —
  CloudFormation rejects updates in this state; the stack must be
  deleted (or continued with `ContinueUpdateRollback` for
  `UPDATE_ROLLBACK_FAILED`).

## Process — Diagnostic decision tree (apply in order)

### Step 0: Capture the failure signal

Gather these five pieces. Each step below branches on which is present.

| Signal | Source | Why required |
|---|---|---|
| **Stack name or ARN + region** | User-provided or `aws cloudformation list-stacks` | All describe calls need this |
| **StackStatus + StackStatusReason** | `aws cloudformation describe-stacks --stack-name <name>` | Drives the category |
| **Failing logical id + ResourceStatusReason** | `aws cloudformation describe-stack-events --stack-name <name>` | Narrows from stack-level symptom to the specific resource |
| **Most recent ChangeSet (for UPDATE_*)** | `aws cloudformation describe-change-set` | Identifies `Action`, `Replacement`, and the changed properties |
| **Drift status (for UPDATE surprises)** | `aws cloudformation detect-stack-drift` | Out-of-band changes can cause UPDATE_FAILED |

If the user has not provided the stack name or region, emit `VERDICT:
NEED_MORE_INFO` with the `list-stacks` discovery command and the list
of missing inputs (stack name/ARN, region, StackStatus,
ResourceStatusReason from `describe-stack-events`).

### Step 1: Identify the failure category

Map the observed `StackStatus` to one of five categories.

| `StackStatus` | Category | Diagnostic step |
|---|---|---|
| `CREATE_FAILED` → `ROLLBACK_IN_PROGRESS` → `ROLLBACK_COMPLETE` | **A. CREATE_FAILED** | Step 2 |
| `UPDATE_IN_PROGRESS` → `UPDATE_COMPLETE_CLEANUP_IN_PROGRESS` → `UPDATE_FAILED` → `UPDATE_ROLLBACK_IN_PROGRESS` | **B. UPDATE_FAILED** | Step 3 |
| `UPDATE_ROLLBACK_IN_PROGRESS` → `UPDATE_ROLLBACK_FAILED` | **E. UPDATE_ROLLBACK_FAILED** | Step 6 |
| `DELETE_IN_PROGRESS` → `DELETE_FAILED` | **C. DELETE_FAILED** | Step 4 |
| `ROLLBACK_COMPLETE` (after a failed CREATE) | **D. ROLLBACK_FAILED** | Step 5 |
| `UPDATE_ROLLBACK_COMPLETE` (after a failed UPDATE rolled back successfully) | **B. UPDATE_FAILED** (rollback succeeded; diagnose the original UPDATE cause) | Step 3 |

**Precedence rule.** When multiple statuses apply across nested stacks,
diagnose the **innermost** failing stack first. A parent stack in
`UPDATE_ROLLBACK_FAILED` is usually downstream of a child stack that
failed to update. Read the child's `describe-stack-events` before
treating the parent's status as the cause.

### Step 2: CREATE_FAILED diagnostic

The stack attempted to create one or more resources and at least one
resource returned `CREATE_FAILED`. CloudFormation then rolls back,
deleting any successfully-created resources, and the stack ends in
`ROLLBACK_COMPLETE`.

| Sub-symptom (read from `ResourceStatusReason`) | Root cause | Probe |
|---|---|---|
| `Resource creation cancelled` (generic) — usually means a dependency failed first | The failing resource is the *visible* failure; the *real* cause is the first `CREATE_FAILED` in `describe-stack-events` (scroll to the earliest) | `describe-stack-events` filtered for `ResourceStatus: CREATE_FAILED`, sorted by timestamp |
| `API: <service>:<Action> AccessDenied` (e.g., `iam:CreateRole`) | The CloudFormation execution role (or the deploying principal) lacks the action | `iam simulate-principal-policy` on the deployment role; check for an SCP or permissions boundary |
| `API: <service>:<Action> LimitExceeded` (e.g., `s3:CreateBucket`) | A service limit (Soft or Hard) was hit | Check Service Quotas for the service; request an increase or clean up stale resources |
| `<ResourceType> already exists in stack <other-stack>` or `already exists` | The physical resource exists outside CloudFormation (manually created, or owned by another stack) | Import the existing resource (`cloudformation import-resources`) or rename in the template |
| `Properties validation failed for resource <id> with message: ...` | A template property value is invalid (wrong type, unknown root device name, etc.) | Read the validation message verbatim; fix the template property; run `cfn-lint` |
| `The following resource(s) failed to create: [<LogicalId>]` and the resource is a custom resource (`Custom::` or `AWS::CloudFormation::CustomResource`) | The custom resource's Lambda function did not send a `SUCCESS` signal within `CreationPolicy` timeout | Read the Lambda function's CloudWatch Logs; check `cfn-response` usage and timeout |
| No `CREATE_FAILED` event, but stack ends in `ROLLBACK_COMPLETE` after a long pause | A `CreationPolicy` `Count` or `TimeoutSignal` was never satisfied (common on EC2 / Auto Scaling groups with no cfn-init / cfn-signal) | Read the `CreationPolicy`; verify the instance runs `cfn-signal` and reaches the desired count |
| `CloudFormation cannot create a change set...` for a CREATE with nested stacks | A nested stack's template is invalid or its parameters are wrong | Diagnose the child stack independently with `describe-stacks --stack-name <nested-arn>` |

**Diagnostic commands:**

```bash
# Identify the stack and its status:
aws cloudformation describe-stacks --stack-name <name> \
  --query 'Stacks[0].{name:StackName,status:StackStatus,reason:StackStatusReason,role:RoleArn,capabilities:Capabilities}'

# Find the first CREATE_FAILED resource (the real cause):
aws cloudformation describe-stack-events --stack-name <name> \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`].{logical:LogicalResourceId,type:ResourceType,physical:PhysicalResourceId,reason:ResourceStatusReason,ts:Timestamp}' \
  --output table

# Find the earliest failure to identify the root resource:
aws cloudformation describe-stack-events --stack-name <name> \
  --query 'reverse(StackEvents[?ResourceStatus==`CREATE_FAILED`])[-1]'
```

**Common fix patterns:**

- **IAM permission (`AccessDenied`):** attach a policy to the
  CloudFormation execution role (or the deploying principal) granting
  the action scoped to the resource ARN. For stacks creating IAM
  resources, pass `--capabilities CAPABILITY_IAM` or
  `CAPABILITY_NAMED_IAM` on `create-stack` / `update-stack`.
- **Service limit (`LimitExceeded`):** request a quota increase via
  Service Quotas, or delete stale resources in the account.
- **Resource already exists:** either delete the existing resource, or
  use `cloudformation import-resources` to bring it under stack
  management, or rename the resource in the template.
- **Invalid property:** fix the template; run
  `cfn-lint template.yaml` before re-deploying.
- **Custom resource timeout:** fix the Lambda function so it calls
  `cfn-response.send(event, context, "SUCCESS", …)` within
  `CreationPolicy.TimeoutInMinutes`; check the function's logs for the
  actual exception.

### Step 3: UPDATE_FAILED diagnostic

The stack attempted to update one or more resources and at least one
resource returned `UPDATE_FAILED`. CloudFormation then attempts to roll
back; if the rollback succeeds, the stack ends in
`UPDATE_ROLLBACK_COMPLETE`. If the rollback also fails, the stack ends
in `UPDATE_ROLLBACK_FAILED` (see Step 6).

| Sub-symptom (read from `ResourceStatusReason` and ChangeSet) | Root cause | Probe |
|---|---|---|
| ChangeSet reports `Replacement: true` for the changed resource | One or more changed properties are immutable and require CloudFormation to create a new physical resource | `describe-change-set` → look at each `Changes[].ResourceChange.Replacement` and `Scope` |
| `Properties validation failed` on update | A property value is invalid in the new template | Read the message; fix the template; `cfn-lint` |
| `API: <service>:<Action> AccessDenied` on update | The execution role lacks the action (often an action only needed on update, e.g., `ec2:ModifyInstanceAttribute`) | `iam simulate-principal-policy` |
| `Resource operation failed with message: ...` (downstream SDK error) | The underlying service rejected the update (e.g., RDS modify pending maintenance, S3 bucket policy malformed) | Read the message verbatim; cross-reference with the service's own logs |
| Drift detected (`detect-stack-drift` returns `DRIFTED`) | Out-of-band changes conflict with the template update | `describe-stack-resource-drifts` to identify the drifted property; either import the current state or reset it |
| `Cannot update resource <LogicalId> as it is in use` | A dependent resource holds a reference (e.g., an ENI on a Security Group) | Identify dependents with `describe-stack-resources` and CloudTrail |
| Nested stack `UPDATE_FAILED` | The child stack's update failed; the parent reports `UPDATE_FAILED` for the `AWS::CloudFormation::Stack` resource | Diagnose the child stack independently |
| Circular dependency in template | `DependsOn` or implicit references form a cycle; `cfn-lint` flags it pre-deploy | Run `cfn-lint`; remove the cycle |

**Diagnostic walk:**

1. **Always create a ChangeSet before updating.** Never run
   `update-stack` blind — always run `create-change-set`, then
   `describe-change-set`, then `execute-change-set` after review.
2. **For each changed resource in the ChangeSet,** read `Action`
   (`Add` / `Modify` / `Remove`) and `Replacement` (`True` / `False` /
   `Conditional`).
3. **If `Replacement: True`,** identify which properties caused the
   replacement (`DetailedStatus` / `Scope` / `PolicyAction`). Decide
   whether to (a) proceed with the replacement, (b) refactor to avoid
   the immutable-property change (e.g., blue-green via a new resource),
   or (c) use `UpdateReplacePolicy` to control delete/retain on the old
   resource.
4. **For `UPDATE_FAILED` without replacement,** read the
   `ResourceStatusReason` verbatim — it usually embeds the underlying
   service's error.

**Common fix patterns:**

- **Immutable property change:** refactor the template to introduce the
  new resource alongside the old one (blue-green), then cut over and
  delete the old. Or use `UpdateReplacePolicy: Retain` to keep the old
  resource after replacement.
- **Missing CAPABILITY_IAM on update:** pass
  `--capabilities CAPABILITY_IAM` (or `CAPABILITY_NAMED_IAM`,
  `CAPABILITY_AUTO_EXPAND`) on `update-stack` / `create-change-set`.
- **Drift:** run `detect-stack-drift`; either `import-resources` to
  align the stack with reality, or reset the resource to match the
  template before re-deploying.
- **DependsOn cycle:** remove the cycle; let CloudFormation compute
  implicit dependencies from `Ref` / `GetAtt` / `DependsOn`.

### Step 4: DELETE_FAILED diagnostic

The stack attempted to delete and at least one resource returned
`DELETE_FAILED`. CloudFormation cannot delete the stack until the
failing resource is resolved.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| `The bucket you tried to delete is not empty` | S3 bucket contains objects (or object versions) that CloudFormation will not auto-delete | `aws s3api list-objects-v2` and `list-object-versions`; empty the bucket or add a `Custom::Cleanup` to the template |
| `<ResourceType> has dependent resources` (ENI on SG, IAM policy on role, CloudWatch alarm on metric, etc.) | A dependent resource outside the stack holds a reference | Identify dependents via the service's own API (e.g., `ec2 describe-network-interfaces --filters group-id=…`) |
| `DeletionPolicy: Retain` (template-driven) | The resource has `DeletionPolicy: Retain`, so CloudFormation skips deletion but the stack still shows the resource | Expected behaviour; the stack delete succeeds for Retain resources, but the physical resource persists. Confirm with `describe-stack-resources` |
| Custom resource `DELETE_FAILED` (no `SUCCESS` signal) | The custom resource's Lambda function failed to handle `RequestType: Delete` | Read the Lambda logs; ensure it handles Delete and calls `cfn-response.send(... "SUCCESS" ...)` even when the physical resource is already gone |
| `Role <name> cannot be deleted because it has <N> policies` | An IAM role has inline or attached policies that block deletion (or active sessions) | Detach policies; ensure no active sessions; delete the role manually if needed |
| Nested stack `DELETE_FAILED` | A child stack cannot be deleted (one of the above reasons applies in the child) | Diagnose the child stack independently |

**Diagnostic walk:**

1. **Read `describe-stack-events` for the `DELETE_FAILED` resource.**
   The `ResourceStatusReason` names the specific blocker.
2. **For S3 buckets,** list objects AND versions — buckets with
   versioning enabled have objects in non-current versions that block
   deletion.
3. **For `DeletionPolicy: Retain`,** confirm in the template — the
   resource will not be deleted; the operator must delete it manually
   if they want it gone.

**Common fix patterns:**

- **S3 bucket not empty:** add a `Custom::S3Cleanup` (Lambda-backed)
  to the template that empties the bucket on Delete, or empty it
  manually with `aws s3 rm s3://<bucket> --recursive` (and
  `--versions` if versioned) before retrying the stack delete.
- **Dependent resources:** delete or detach the dependents outside
  CloudFormation, then retry the stack delete.
- **`DeletionPolicy: Retain`:** if the resource should be deleted on
  stack delete, change the policy to `Delete` in the template and
  update the stack before deleting.
- **Custom resource Delete:** fix the Lambda function to handle Delete
  idempotently; ensure it always sends `SUCCESS` (Delete should not
  fail the stack delete even if the physical resource is already gone).

### Step 5: ROLLBACK_FAILED diagnostic (stack stuck in ROLLBACK_COMPLETE)

After a failed CREATE, CloudFormation rolls back and deletes all
resources it created. If a resource cannot be deleted during rollback,
the stack ends in `ROLLBACK_FAILED`. Once the rollback eventually
completes (or is forced), the stack ends in `ROLLBACK_COMPLETE`.

**Key fact:** a stack in `ROLLBACK_COMPLETE` cannot be updated. The
only valid lifecycle action is to **delete the stack** and re-create it.
Operators often keep retrying `update-stack` on a `ROLLBACK_COMPLETE`
stack and receive `UpdateRollbackComplete` errors — this is by design.

| Sub-symptom | Root cause | Action |
|---|---|---|
| `StackStatus: ROLLBACK_COMPLETE` after a failed CREATE | All resources were rolled back; the stack exists only as a record | `aws cloudformation delete-stack --stack-name <name>`, then `create-stack` with the fixed template |
| `StackStatus: ROLLBACK_FAILED` (rollback itself failed) | A resource could not be deleted during rollback | Identify the `DELETE_FAILED` resource (Step 4); resolve the blocker; CloudFormation will resume rollback automatically, or use `ContinueUpdateRollback` (for UPDATE_ROLLBACK_FAILED) |
| Resources were created but the stack is in `ROLLBACK_COMPLETE` | The visible resources have already been deleted by rollback; the operator is seeing a stale console view | Refresh `describe-stack-resources`; the only valid next action is delete |

**Diagnostic walk:**

1. **Confirm `StackStatus: ROLLBACK_COMPLETE`** via `describe-stacks`.
2. **Read the original `CREATE_FAILED` reason** from
   `describe-stack-events` to identify the root cause.
3. **Fix the template or the IAM/limit issue** identified in Step 2.
4. **Delete the stack:**
   `aws cloudformation delete-stack --stack-name <name>`.
5. **Re-create with the fixed template:**
   `aws cloudformation create-stack --stack-name <name> --template-body file://fixed.yaml --capabilities CAPABILITY_IAM`.

### Step 6: UPDATE_ROLLBACK_FAILED diagnostic (nested stack and others)

After a failed UPDATE, CloudFormation rolls back. If the rollback also
fails (often because a replaced resource cannot be re-created, or a
nested stack cannot roll back), the stack ends in
`UPDATE_ROLLBACK_FAILED`.

**Key tool:** `ContinueUpdateRollback` with
`--resources-to-skip <logical-id>` lets the operator skip the failing
resource and complete the rollback, returning the stack to
`UPDATE_ROLLBACK_COMPLETE` so it can be updated again.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| Nested stack `AWS::CloudFormation::Stack` reports `UPDATE_ROLLBACK_FAILED` | The child stack is itself in `UPDATE_ROLLBACK_FAILED`; the parent cannot roll back until the child does | `describe-stacks --stack-name <nested-stack-arn>`; diagnose the child |
| Replaced resource cannot be re-created during rollback | The new physical resource created during UPDATE is in a state that prevents re-creating the old one (e.g., a unique name conflict) | Identify the resource; use `ContinueUpdateRollback --resources-to-skip` |
| `UPDATE_ROLLBACK_FAILED` after a Lambda version update | The Lambda alias routing prevents rollback (e.g., old version is referenced by an active alias) | Resolve the alias; retry rollback |
| `UPDATE_ROLLBACK_FAILED` after a DynamoDB table update | An in-progress update was interrupted; DynamoDB tables can take 10+ minutes to update | Wait for the in-progress operation to settle, then retry rollback |
| Custom resource cannot handle `RequestType: Update` rollback | The custom resource's Lambda function did not send `SUCCESS` for the rollback Update | Read the Lambda logs; ensure Delete is handled idempotently on the new physical resource |

**Diagnostic walk:**

1. **Confirm `StackStatus: UPDATE_ROLLBACK_FAILED`.**
2. **Identify the resource that cannot roll back** via
   `describe-stack-events` filtered to `UPDATE_ROLLBACK_IN_PROGRESS` /
   `UPDATE_ROLLBACK_FAILED` events.
3. **For nested stacks,** diagnose the child stack independently —
   the child's `UPDATE_ROLLBACK_FAILED` is the real cause.
4. **Decide whether to skip the failing resource:**
   ```bash
   aws cloudformation continue-update-rollback \
     --stack-name <name> \
     --resources-to-skip <logical-id-of-failing-resource>
   ```
   This returns the stack to `UPDATE_ROLLBACK_COMPLETE`, after which it
   can be updated again.
5. **After rollback completes,** re-attempt the original UPDATE with a
   ChangeSet that addresses the root cause.

### Step 7: Map to root-cause catalog

| # | Root cause | Category | Fix pattern |
|---|---|---|---|
| 1 | IAM `AccessDenied` on `create` / `update` (missing action on execution role or SCP block) | CREATE_FAILED / UPDATE_FAILED | Attach scoped policy; remove SCP block; pass CAPABILITY_IAM |
| 2 | Service `LimitExceeded` (S3 buckets, EC2 vCPUs, IAM entities) | CREATE_FAILED | Request Service Quota increase; clean up stale resources |
| 3 | Resource already exists outside the stack | CREATE_FAILED | Import the resource or rename in the template |
| 4 | Invalid template property (failed `Properties validation`) | CREATE_FAILED / UPDATE_FAILED | Fix the property; run `cfn-lint` |
| 5 | Immutable property changed (ChangeSet `Replacement: true`) | UPDATE_FAILED | Refactor to blue-green, or proceed with replacement, or use `UpdateReplacePolicy` |
| 6 | Missing `CAPABILITY_IAM` / `CAPABILITY_NAMED_IAM` | CREATE_FAILED / UPDATE_FAILED | Pass `--capabilities` on `create-stack` / `update-stack` |
| 7 | Stack drift (`DRIFTED`) conflicts with update | UPDATE_FAILED | `detect-stack-drift`; import or reset drifted resources |
| 8 | `DependsOn` circular dependency | CREATE_FAILED / UPDATE_FAILED | `cfn-lint`; remove the cycle; rely on implicit dependencies |
| 9 | S3 bucket not empty on delete | DELETE_FAILED | Empty bucket (including versions); add `Custom::S3Cleanup` |
| 10 | Dependent resource blocks delete (ENI/SG, IAM policy/role) | DELETE_FAILED | Delete or detach the dependent outside CloudFormation |
| 11 | Custom resource did not send `SUCCESS` within `CreationPolicy` | CREATE_FAILED / ROLLBACK_FAILED | Fix the Lambda handler; check CloudWatch Logs |
| 12 | Nested stack in `UPDATE_ROLLBACK_FAILED` | UPDATE_ROLLBACK_FAILED | Diagnose child; `ContinueUpdateRollback --resources-to-skip` |
| 13 | Stack in `ROLLBACK_COMPLETE` after failed CREATE | ROLLBACK_FAILED | Delete the stack; recreate with the fixed template |
| 14 | `CreationPolicy` signal count/timeout never satisfied (EC2 / ASG without cfn-signal) | CREATE_FAILED | Fix user-data to call `cfn-signal`; raise `TimeoutInMinutes` |

### Step 8: Validate via ChangeSet before applying any fix

Before applying any UPDATE, validate the proposed fix:

1. **Lint the template:** `cfn-lint fixed-template.yaml`.
2. **Create a ChangeSet** against the existing stack with
   `create-change-set --template-body file://fixed.yaml`; then
   `describe-change-set` and check each resource's `Action` and
   `Replacement`. If any shows `Replacement: True`, confirm with the
   operator before executing.
3. **Execute** the ChangeSet only after it matches expectations.

For CREATEs on a new stack, validate with `cfn-lint` and
`cloudformation validate-template`.

### Step 9: Decide — ROOT_CAUSE_FOUND vs NEED_MORE_INFO vs ESCALATE

- **ROOT_CAUSE_FOUND.** The walk identified a specific failure category
  and a specific configuration element (template property, IAM action,
  ChangeSet replacement, dependent resource, custom-resource signal).
  Output REMEDIATION with the exact change.
- **NEED_MORE_INFO.** The walk reached a step where the operator cannot
  supply evidence (e.g., `describe-stack-events` requires elevated
  read access, or the failing resource is owned by another team).
  Output the list of missing inputs.
- **ESCALATE.** The walk identifies a cause outside the operator's
  scope: a nested stack owned by another team, an SCP owned by security,
  a service quota owned by AWS Support. Output the escalation target
  and the specific request.

## Output format

```text
INCIDENT: <stack name or ARN> in <region> — <StackStatus + symptom>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <category name> — <specific failing config element>
EVIDENCE:
  - describe-stacks: <StackStatus + StackStatusReason>
  - describe-stack-events: <ResourceStatus + ResourceStatusReason>
  - describe-stack-resources: <PhysicalResourceId + status>
  - describe-change-set: <Action + Replacement, if UPDATE>
  - iam simulate-principal-policy: <decision, if IAM>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION:
  1. <specific template / IAM / ChangeSet change>
  2. <verification command>
  3. <post-apply monitoring>
```

### Worked example — missing CAPABILITY_IAM on a stack with IAM resources

```text
INCIDENT: app-platform in us-east-1 — CREATE_FAILED, then
ROLLBACK_COMPLETE on TaskRole
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: CREATE_FAILED — stack template declares
AWS::IAM::Role TaskRole but create-stack was invoked without
--capabilities CAPABILITY_IAM, so CloudFormation rejected the
CREATE before any resource was created
EVIDENCE:
  - describe-stacks: StackStatus ROLLBACK_COMPLETE,
    StackStatusReason "The following resource(s) failed to create:
    [TaskRole]."
  - describe-stack-events: ResourceStatus CREATE_FAILED on TaskRole,
    ResourceStatusReason "Requires capabilities : [CAPABILITY_IAM].
    User requested no capabilities."
  - describe-stack-resources: TaskRole has no PhysicalResourceId
    (never created)
  - aws cloudformation describe-stack-events shows no other
    CREATE_FAILED resources — TaskRole is the only failure
ROOT_CAUSE_CATALOG: #6 (missing CAPABILITY_IAM)
REMEDIATION:
  1. The stack is in ROLLBACK_COMPLETE and cannot be updated. Delete
     it first:
     aws cloudformation delete-stack --stack-name app-platform
  2. Re-create with the corrected capability:
     aws cloudformation create-stack --stack-name app-platform \
       --template-body file://template.yaml \
       --capabilities CAPABILITY_IAM \
       --role-arn arn:aws:iam::111111111111:role/cfn-exec
  3. Verify with a ChangeSet on the next update:
     aws cloudformation create-change-set --stack-name app-platform \
       --change-set-name verify --template-body file://template.yaml \
       --capabilities CAPABILITY_IAM
     Expect ChangeSet with no `Replacement: True` and only `Add` actions
     on first deploy. Monitor `describe-stack-events` for SUCCEEDED.
```

## Expert edge cases

These patterns represent genuine, non-obvious CloudFormation failure
modes that a senior operator would catch but a generalist would miss.

### The first `CREATE_FAILED` is the cause; the rest are cascade

When a stack fails to create, CloudFormation cancels all in-flight
resources. `describe-stack-events` may show many `CREATE_FAILED`
resources, but only the **first** (by timestamp) is the real cause —
the rest were cancelled as a cascade. Filter events by
`ResourceStatus: CREATE_FAILED` and sort by `Timestamp` ascending; the
earliest is the root cause.

### `Replacement: True` is not always visible in `describe-stack-events`

When an UPDATE fails because of a replacement, the
`ResourceStatusReason` may say only `Resource update cancelled` — the
replacement intent is visible only in the ChangeSet's
`Changes[].ResourceChange.Replacement`. Always cross-reference
`describe-change-set` for an UPDATE diagnosis, not just events.

### `DeletionPolicy: Retain` does not fail the stack delete

Operators sometimes believe a Retain resource causes `DELETE_FAILED`.
It does not. CloudFormation skips Retain resources and reports them as
`DELETE_SKIPPED` in events. A genuine `DELETE_FAILED` is always a
resource CloudFormation tried to delete but could not (S3 bucket not
empty, dependent resource, custom resource not signalling).

### Nested stacks: the parent's status lags the child's

A parent stack in `UPDATE_ROLLBACK_IN_PROGRESS` often reflects a child
that already failed. The parent's `describe-stack-events` will show the
`AWS::CloudFormation::Stack` resource as the failure point, but the
real cause is inside the child. Always drill into the child stack —
the `PhysicalResourceId` of the nested-stack resource is the child's
ARN.

### `ContinueUpdateRollback --resources-to-skip` is the only recovery from UPDATE_ROLLBACK_FAILED

There is no `retry-rollback` API. The only recovery is
`ContinueUpdateRollback`, optionally with `--resources-to-skip` for a
resource that cannot be rolled back (e.g., a replaced resource whose
old version is gone). After completion, the stack returns to
`UPDATE_ROLLBACK_COMPLETE` and can be updated again. Skipping leaves
the resource in a potentially inconsistent state — document and
reconcile manually.

### Drift can cause UPDATE_FAILED on an unrelated property change

A resource drifted out-of-band (e.g., an S3 bucket's policy edited
directly). A later stack UPDATE that touches a different property
fails because CloudFormation reconciles the drifted property too.
`detect-stack-drift` reveals the drifted property; either import the
current state or reset it before re-deploying.

### Custom resources must handle Delete idempotently

A custom resource's Lambda function must always send `SUCCESS` for a
`Delete` request, even if the physical resource is already gone. A
function that returns `FAILED` on Delete because the resource is
missing will block stack delete indefinitely. Standard pattern: check
existence; if absent, return `SUCCESS` without error.

### CreationPolicy TimeoutSignal is not a CREATE_FAILED resource error

When a `CreationPolicy` `Count` or `TimeoutInMinutes` is not satisfied
(common on EC2 / ASG where cfn-init / cfn-signal is not wired),
CloudFormation reports `CREATE_FAILED` with reason `The following
resource(s) failed to create: [ASG].` — but the instances may be
running and healthy. The fix is in the user-data (`cfn-signal -e 0`)
or the ASG desired capacity, not the template resource itself.

### Service limits can be hard or soft; only Soft can be raised via Quotas

`LimitExceeded` for S3 buckets per account (Soft, default 100) can be
raised via Service Quotas; so can IAM entities per account (default
5000) and VPCs per region (default 5, has a ceiling). Confirm via
`aws service-quotas get-service-quota`.

## Expert heuristic — "Read the ResourceStatusReason, not the StackStatus"

The single most common diagnostic mistake is treating the `StackStatus`
(`CREATE_FAILED`, `UPDATE_FAILED`, `ROLLBACK_COMPLETE`) as the root
cause. It is not. It is the lifecycle phase. The actionable signal is
the failing resource's `ResourceStatusReason`, which often embeds the
underlying service's error message.

Quick lookup table for common `StackStatus` → real cause mappings:

| `StackStatus` | What it means | Where the real cause lives |
|---|---|---|
| `CREATE_FAILED` → `ROLLBACK_COMPLETE` | A resource failed to create; rollback succeeded | The earliest `CREATE_FAILED` event's `ResourceStatusReason` |
| `UPDATE_FAILED` → `UPDATE_ROLLBACK_COMPLETE` | A resource failed to update; rollback succeeded | The `UPDATE_FAILED` event's `ResourceStatusReason` AND the ChangeSet's `Replacement` |
| `UPDATE_ROLLBACK_FAILED` | A resource failed to roll back | `describe-stack-events` filtered to `UPDATE_ROLLBACK_FAILED`; consider `ContinueUpdateRollback` |
| `DELETE_FAILED` | A resource could not be deleted | The `DELETE_FAILED` event's `ResourceStatusReason` (S3 bucket not empty, dependent resource, etc.) |
| `ROLLBACK_FAILED` | A resource could not be deleted during CREATE rollback | Same as DELETE_FAILED walk |

When in doubt, run:
`aws cloudformation describe-stack-events --stack-name <name>` and
read the `ResourceStatusReason` for the earliest failing event. The
`StackStatus` is the phase; the `ResourceStatusReason` is the cause.

## Anti-Patterns — NEVER

- **NEVER** treat the `StackStatus` as the root cause. It is the
  lifecycle phase. The `ResourceStatusReason` on the specific failing
  resource is the actionable signal.
- **NEVER** recommend `update-stack` on a stack in `ROLLBACK_COMPLETE`.
  CloudFormation rejects updates in this state. The stack must be
  deleted and re-created.
- **NEVER** recommend `update-stack` without first creating and
  reviewing a ChangeSet. `update-stack` blind can trigger unexpected
  `Replacement: True` and irreversible resource deletion.
- **NEVER** declare `ROOT_CAUSE_FOUND` for an UPDATE_FAILED diagnosis
  without quoting the `ResourceStatusReason` AND cross-referencing the
  ChangeSet for `Replacement`.
- **NEVER** assume the first resource shown in
  `describe-stack-events` is the root cause. Filter by
  `ResourceStatus: CREATE_FAILED` / `UPDATE_FAILED` and sort by
  timestamp ascending — the earliest is the cause; the rest are
  cascade cancellations.
- **NEVER** confuse `DeletionPolicy: Retain` with `DELETE_FAILED`.
  Retain is intentional; CloudFormation reports it as `DELETE_SKIPPED`,
  not failed.
- **NEVER** recommend `delete-stack` as a "fix" without confirming
  the stack is in `ROLLBACK_COMPLETE` (after failed CREATE) or after
  `ContinueUpdateRollback` has been considered (for
  `UPDATE_ROLLBACK_FAILED`). Deleting an `UPDATE_ROLLBACK_FAILED`
  stack loses the option to skip-and-recover.
- **NEVER** raise a Service Quota increase without first confirming
  the limit is Soft (raisable) and identifying why the existing count
  is high (stale resources).
- **NEVER** declare UPDATE_FAILED with `Replacement: true` without
  naming which property caused the replacement. The ChangeSet's
  `Scope` and `DetailedStatus` identify it.
- **NEVER** run `update-stack` to recover a custom resource that
  failed to signal — fix the Lambda handler first, otherwise the same
  update will fail the same way.
- **NEVER** skip `cfn-lint` on a template fix. Most invalid-property
  failures are caught by `cfn-lint` pre-deploy.
- **NEVER** assume a nested stack's parent status reflects the root
  cause. Drill into the child stack — the parent's
  `AWS::CloudFormation::Stack` resource only mirrors the child's
  outcome.
- **NEVER** conclude DELETE_FAILED without checking both objects AND
  versions on S3 buckets. Versioned buckets have objects in
  non-current versions that block deletion.

## Recent AWS features (2024-2026)

- **Import resources into an existing stack (enhanced 2024-2025):**
  `cloudformation import-resources` (resource-level import) lets you
  bring an out-of-band resource under stack management without a full
  stack import. Useful when CREATE_FAILED reports "resource already
  exists".
- **ContinueUpdateRollback with nested-stack skip (2024):** enhanced
  to skip nested-stack child resources, making recovery from
  `UPDATE_ROLLBACK_FAILED` on nested stacks less destructive.
- **CloudFormation Drift Detection for nested stacks (2024-2025):**
  drift detection now recurses into nested stacks, surfacing child
  drift in the parent's `describe-stack-resource-drifts`.
- **cfn-lint v1 (2024-2025):** new rule set, stricter on IAM resource
  properties and `DependsOn` cycles. Update pinned versions before
  relying on results.
- **Service Quotas integration (2025):** per-account stack count and
  stack-instance count visible in Service Quotas, simplifying
  `LimitExceeded` triage.
- **UpdateReplacePolicy (GA):** controls retain / delete / snapshot
  behaviour for the OLD physical resource on a Replacement. Set
  `UpdateReplacePolicy: Retain` to keep the old resource after a
  replacement — critical for UPDATE_FAILED recovery.

## References

See `references/failure-catalog-and-decision-tree.md` for the full
per-category walk with worked examples per StackStatus, and
`references/diagnostic-commands.md` for the canonical command script
for each failure category.

## Domain

AWS CloudOps / DevTools — Infrastructure-as-Code Reliability.

## AWS documentation

- **AWS CloudFormation User Guide** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html
- **CloudFormation stack events** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-listing-event.html
- **ChangeSets** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-changesets.html
- **ContinueUpdateRollback** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-continueupdaterollback.html
- **Drift detection** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html
- **DeletionPolicy / UpdateReplacePolicy** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-attribute-deletionpolicy.html
- **CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/cloudformation/
