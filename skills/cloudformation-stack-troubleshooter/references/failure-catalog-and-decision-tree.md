# CloudFormation failure catalog and decision tree

On-demand reference for the `cloudformation-stack-troubleshooter`
skill. Loaded when the skill needs the full per-category walk with
worked examples. The SKILL.md contains the summary table; this file
expands each category with verbatim `ResourceStatusReason` examples,
the diagnostic walk, and the canonical fix.

## How to use this file

1. Identify the `StackStatus` from `describe-stacks`.
2. Jump to the matching section below.
3. Follow the walk; cross-reference evidence with the worked example.

---

## A. CREATE_FAILED — resource creation error

### Signature

```text
StackStatus: CREATE_FAILED → ROLLBACK_IN_PROGRESS → ROLLBACK_COMPLETE
ResourceStatusReason: <one of the sub-causes below>
```

### Decision tree

1. **Find the first `CREATE_FAILED` resource** by timestamp (the rest
   are cascade cancellations):
   ```bash
   aws cloudformation describe-stack-events --stack-name <name> \
     --query 'reverse(StackEvents[?ResourceStatus==`CREATE_FAILED`])[-1]'
   ```
2. **Read the `ResourceStatusReason` verbatim.** Map to a sub-cause.
3. **Cross-reference** with IAM, Service Quotas, the underlying
   service API, and `cfn-lint` as needed.

### Top sub-causes

| Sub-cause | Example `ResourceStatusReason` | Fix |
|---|---|---|
| IAM permission denied | `API: iam:CreateRole AccessDenied` | Attach scoped policy to the execution role; remove SCP block |
| Missing CAPABILITY_IAM | `Requires capabilities : [CAPABILITY_IAM]. User requested no capabilities.` | Pass `--capabilities CAPABILITY_IAM` (or `CAPABILITY_NAMED_IAM`, `CAPABILITY_AUTO_EXPAND`) |
| Service limit exceeded | `API: s3:CreateBucket LimitExceeded` | Request Service Quota increase; clean up stale resources |
| Resource already exists | `bucket-name already exists` or `<type> already exists in stack <other>` | Import via `cloudformation import-resources`, or rename in the template |
| Invalid property value | `Properties validation failed for resource <id> with message: ...` | Fix the property; `cfn-lint template.yaml` |
| Custom resource timeout | `The following resource(s) failed to create: [CustomX]` and no SUCCESS signalled | Fix the Lambda handler to call `cfn-response.send(... "SUCCESS")` within `CreationPolicy.TimeoutInMinutes` |
| CreationPolicy signal not satisfied | `Failed to receive <N> resource signal(s) within the specified duration` | Wire `cfn-signal -e 0` in user-data; raise `TimeoutInMinutes` |

### Worked example

```text
INCIDENT: app-platform in us-east-1 — CREATE_FAILED on TaskRole
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: CREATE_FAILED — template declares AWS::IAM::Role TaskRole
 but create-stack was invoked without --capabilities CAPABILITY_IAM
EVIDENCE:
  - describe-stacks: StackStatus ROLLBACK_COMPLETE
  - describe-stack-events: TaskRole CREATE_FAILED,
    reason "Requires capabilities : [CAPABILITY_IAM]. User requested
    no capabilities."
  - describe-stack-events: TaskRole is the only CREATE_FAILED event
ROOT_CAUSE_CATALOG: #6 (missing CAPABILITY_IAM)
REMEDIATION:
  1. aws cloudformation delete-stack --stack-name app-platform
  2. aws cloudformation create-stack --stack-name app-platform \
       --template-body file://template.yaml \
       --capabilities CAPABILITY_IAM \
       --role-arn arn:aws:iam::111111111111:role/cfn-exec
  3. Verify via create-change-set on the next update.
```

---

## B. UPDATE_FAILED — update cannot proceed

### Signature

```text
StackStatus: UPDATE_IN_PROGRESS → UPDATE_COMPLETE_CLEANUP_IN_PROGRESS
        → UPDATE_ROLLBACK_IN_PROGRESS → UPDATE_ROLLBACK_COMPLETE
        (or UPDATE_ROLLBACK_FAILED if rollback fails — see E)
ResourceStatusReason: <one of the sub-causes below>
```

### Decision tree

1. **Always review the ChangeSet first.** Cross-reference
   `describe-change-set` for each resource's `Action` and
   `Replacement`.
2. **If `Replacement: True`,** identify which property caused it
   (`Scope`, `DetailedStatus`).
3. **Read the `ResourceStatusReason`** on the failing resource.

### Top sub-causes

| Sub-cause | Example `ResourceStatusReason` | Fix |
|---|---|---|
| Immutable property change | ChangeSet reports `Replacement: True` on e.g. DynamoDB `KeySchema`, RDS `DBInstanceIdentifier`, IAM `RoleName` | Refactor to blue-green; use `UpdateReplacePolicy: Retain`; or proceed with the replacement knowingly |
| Properties validation failed | `Properties validation failed for resource <id> with message: ...` | Fix the property; `cfn-lint` |
| IAM AccessDenied on update | `API: ec2:ModifyInstanceAttribute AccessDenied` | Attach scoped policy; check SCP and permissions boundary |
| Downstream service error | `Resource operation failed with message: <service-specific>` | Read the message; cross-reference with the service's logs |
| Drift conflicts with update | `detect-stack-drift` returns `DRIFTED` | `describe-stack-resource-drifts`; import or reset |
| Resource in use | `Cannot update resource <id> as it is in use` | Identify dependents with `describe-stack-resources` and CloudTrail |
| Nested stack UPDATE_FAILED | `Embedded stack <arn> was not successfully updated` | Diagnose the child stack independently |
| DependsOn cycle | `cfn-lint` flags circular dependency | Remove the cycle; rely on implicit Ref/GetAtt deps |

---

## C. DELETE_FAILED — stack cannot be deleted

### Signature

```text
StackStatus: DELETE_IN_PROGRESS → DELETE_FAILED
ResourceStatusReason: <one of the sub-causes below>
```

### Decision tree

1. **Read the `ResourceStatusReason`** on the `DELETE_FAILED` resource.
2. **For S3 buckets,** list both objects AND versions.
3. **For dependent-resource blocks,** identify the dependent outside
   CloudFormation.

### Top sub-causes

| Sub-cause | Example `ResourceStatusReason` | Fix |
|---|---|---|
| S3 bucket not empty | `The bucket you tried to delete is not empty` | Empty current objects AND non-current versions; add a `Custom::S3Cleanup` |
| Dependent resource | `<type> has dependent resources` (ENI on SG, IAM policy on role) | Delete/detach dependents outside CloudFormation |
| DeletionPolicy: Retain (template-driven) | `DELETE_SKIPPED` in events (not a failure) | Expected; physical resource persists — manually delete if needed |
| Custom resource DELETE_FAILED | No SUCCESS signal on Delete | Fix Lambda to handle Delete idempotently; always send SUCCESS |
| IAM role with policies | `Role <name> cannot be deleted because it has <N> policies` | Detach policies; ensure no active sessions |
| Nested stack DELETE_FAILED | Child stack cannot be deleted | Diagnose the child stack |

---

## D. ROLLBACK_FAILED — stack stuck in ROLLBACK_COMPLETE

### Signature

```text
StackStatus: ROLLBACK_COMPLETE (after a failed CREATE)
```

### Decision tree

1. **Confirm `StackStatus: ROLLBACK_COMPLETE`.**
2. **Read the original `CREATE_FAILED` reason** from
   `describe-stack-events`.
3. **Fix the template or IAM/limit issue** identified in Step 2.
4. **Delete the stack**, then re-create with the fixed template.

### Key constraint

A stack in `ROLLBACK_COMPLETE` **cannot be updated**. The only valid
lifecycle action is `delete-stack`. Operators often retry
`update-stack` and receive a `ValidationError` — this is by design.

---

## E. UPDATE_ROLLBACK_FAILED — update rollback cannot complete

### Signature

```text
StackStatus: UPDATE_ROLLBACK_IN_PROGRESS → UPDATE_ROLLBACK_FAILED
```

### Decision tree

1. **Confirm `StackStatus: UPDATE_ROLLBACK_FAILED`.**
2. **Identify the resource that cannot roll back** via
   `describe-stack-events` filtered to `UPDATE_ROLLBACK_FAILED`.
3. **For nested stacks,** diagnose the child stack independently.
4. **Recover with `ContinueUpdateRollback`:**
   ```bash
   aws cloudformation continue-update-rollback \
     --stack-name <name> \
     --resources-to-skip <logical-id-of-failing-resource>
   ```
   This returns the stack to `UPDATE_ROLLBACK_COMPLETE`, after which
   it can be updated again.
5. **Skipped resources are now potentially inconsistent** — document
   and reconcile manually.

### Top sub-causes

| Sub-cause | Fix |
|---|---|
| Nested stack cannot roll back | Diagnose child; `ContinueUpdateRollback --resources-to-skip <nested-logical-id>` |
| Replaced resource cannot be re-created | `ContinueUpdateRollback --resources-to-skip <replaced-logical-id>` |
| Custom resource cannot handle Update rollback | Fix Lambda to handle Update + Delete idempotently on rollback |
| Long-running operation interrupted (e.g., DynamoDB table update) | Wait for the in-progress operation to settle; retry rollback |

### Worked example

```text
INCIDENT: platform-root in us-east-1 — UPDATE_ROLLBACK_FAILED,
 nested NetworkStack cannot roll back
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: UPDATE_ROLLBACK_FAILED — nested child stack
 platform-root-NetworkStack-abc is itself in UPDATE_ROLLBACK_FAILED
 because its VPC resource's CidrBlock (immutable) was changed in the
 attempted update; the parent cannot roll back until the child does
EVIDENCE:
  - describe-stacks parent: StackStatus UPDATE_ROLLBACK_FAILED
  - describe-stack-events parent: NetworkStack
    UPDATE_ROLLBACK_FAILED, reason "Embedded stack <arn> was not
    successfully updated: The following resource(s) failed to
    update: [VPC]."
  - describe-stacks child: StackStatus UPDATE_ROLLBACK_FAILED
ROOT_CAUSE_CATALOG: #12 (nested stack UPDATE_ROLLBACK_FAILED)
REMEDIATION:
  1. Recover the parent by skipping the failing nested-stack resource:
     aws cloudformation continue-update-rollback \
       --stack-name platform-root \
       --resources-to-skip NetworkStack
     The stack returns to UPDATE_ROLLBACK_COMPLETE.
  2. Recover the child similarly, OR diagnose and fix the child's VPC
     CidrBlock change (immutable — must be reverted or done via a new
     VPC).
  3. After both parent and child are UPDATE_ROLLBACK_COMPLETE, re-plan
     the original change as a blue-green VPC swap (new VPC, migrate
     dependencies, cutover, delete old) — CidrBlock changes on an
     existing VPC are never safe in-place.
```

---

## Cross-cutting gotchas

### The first CREATE_FAILED is the cause

`describe-stack-events` may show many `CREATE_FAILED` resources; only
the **earliest by timestamp** is the real cause. The rest are cascade
cancellations. Filter by `ResourceStatus: CREATE_FAILED` and sort by
`Timestamp` ascending.

### `Replacement: True` lives in the ChangeSet, not in events

The `ResourceStatusReason` on an UPDATE_FAILED resource may say only
`Resource update cancelled`. The actual replacement intent is in the
ChangeSet's `Changes[].ResourceChange.Replacement`. Always
cross-reference `describe-change-set` for an UPDATE diagnosis.

### DeletionPolicy: Retain reports DELETE_SKIPPED, not DELETE_FAILED

CloudFormation reports Retain resources as `DELETE_SKIPPED` in events.
A genuine `DELETE_FAILED` is always a resource CloudFormation tried
to delete but could not.

### Nested stack: parent status lags the child

A parent in `UPDATE_ROLLBACK_IN_PROGRESS` often reflects a child that
already failed. The parent's `AWS::CloudFormation::Stack` resource
only mirrors the child's outcome. Always drill into the child via
its `PhysicalResourceId` ARN.

### Service Quotas are Soft or Hard

`LimitExceeded` for S3 buckets per account (Soft, default 100), IAM
entities (Soft, default 5000), and VPCs per region (Soft, default 5
with a ceiling) can be raised via Service Quotas. Hard limits require
architecture changes. Confirm via
`aws service-quotas get-service-quota`.

### cfn-lint catches most property errors pre-deploy

Run `cfn-lint template.yaml` before every `create-stack` /
`update-stack`. Most `Properties validation failed` errors are caught
by `cfn-lint` and never reach CloudFormation.
