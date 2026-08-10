# End-to-end usage scenario: cloudformation-stack-troubleshooter

A walkthrough showing the skill diagnosing a CloudFormation
`CREATE_FAILED` / `ROLLBACK_COMPLETE` failure caused by a missing
`CAPABILITY_IAM` acknowledgement. This exercises Step 0 (signal
capture), Step 1 (status categorisation), Step 2 (CREATE_FAILED walk),
the root-cause catalog, and the remediation workflow.

## Input (user prompt)

> Our `app-platform` stack in `us-east-1` failed to create and is now
> stuck in `ROLLBACK_COMPLETE`. The events show `TaskRole` (an
> `AWS::IAM::Role`) with `CREATE_FAILED` and reason "Requires
> capabilities : [CAPABILITY_IAM]. User requested no capabilities."
> We ran `create-stack` without `--capabilities`. No other resources
> failed.

## Skill output

```text
INCIDENT: app-platform in us-east-1 — StackStatus ROLLBACK_COMPLETE
 after a failed CREATE on TaskRole (AWS::IAM::Role)
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: CREATE_FAILED — stack template declares AWS::IAM::Role
 TaskRole but create-stack was invoked without
 --capabilities CAPABILITY_IAM, so CloudFormation rejected the
 CREATE before any resource was provisioned
EVIDENCE:
  - describe-stacks: StackStatus ROLLBACK_COMPLETE,
    StackStatusReason "The following resource(s) failed to create:
    [TaskRole]."
  - describe-stack-events: ResourceStatus CREATE_FAILED on TaskRole,
    ResourceStatusReason "Requires capabilities : [CAPABILITY_IAM].
    User requested no capabilities."
  - describe-stack-events: TaskRole is the ONLY CREATE_FAILED event
    (no cascade — root resource identified)
  - describe-stack-resources: TaskRole has no PhysicalResourceId
    (never provisioned; no cleanup needed before re-create)
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
     If any IAM resource uses a custom name, use
     CAPABILITY_NAMED_IAM instead.
  3. Validate the next update via ChangeSet (not blind update-stack):
     aws cloudformation create-change-set --stack-name app-platform \
       --change-set-name verify-$(date +%s) \
       --template-body file://template.yaml \
       --capabilities CAPABILITY_IAM
     Review Replacement column before executing.
  4. Monitor describe-stack-events until StackStatus is CREATE_COMPLETE.
```

## What the skill caught that a generic assistant misses

1. **`ROLLBACK_COMPLETE` cannot be updated.** A generic assistant
   often suggests `update-stack --capabilities CAPABILITY_IAM`. The
   skill recognises that the only valid lifecycle action in
   `ROLLBACK_COMPLETE` is `delete-stack` then `create-stack`.

2. **The single CREATE_FAILED resource is the cause.** A generic
   assistant might suggest checking every resource in the template.
   The skill identifies TaskRole as the only failing resource — there
   is no cascade to chase.

3. **The CAPABILITY level matters.** A generic assistant says "add
   CAPABILITY_IAM." The skill notes that `CAPABILITY_NAMED_IAM` is
   required if any IAM resource has a custom name, and
   `CAPABILITY_AUTO_EXPAND` is required for macros.

4. **The ChangeSet verification step.** A generic assistant typically
   recommends re-running `create-stack`. The skill inserts a
   `create-change-set` verification step on the NEXT update so the
   operator does not repeat a blind-deploy mistake.

## Slash-command invocation

```
/aws:troubleshoot-cloudformation-stack
```

Or via the orchestrator:

```
/aws:pipeline
You: "app-platform stuck in ROLLBACK_COMPLETE, TaskRole CREATE_FAILED"
```

The orchestrator emits `[Phase: Troubleshoot | Skills routed:
cloudformation-stack-troubleshooter]` and hands off to this skill
for the VERDICT.

## Live-account diagnostic flow (requires AWS CLI)

When the operator has credentials for the failing account:

```bash
# Identify the failing stack and its status.
aws cloudformation describe-stacks --stack-name app-platform \
  --query 'Stacks[0].{name:StackName,status:StackStatus,reason:StackStatusReason,role:RoleArn,capabilities:Capabilities}'

# Find the first CREATE_FAILED resource (the real cause).
aws cloudformation describe-stack-events --stack-name app-platform \
  --query 'reverse(StackEvents[?ResourceStatus==`CREATE_FAILED`])[-1].{logical:LogicalResourceId,type:ResourceType,reason:ResourceStatusReason,ts:Timestamp}' \
  --output table

# Find ALL CREATE_FAILED resources to confirm the cascade (if any).
aws cloudformation describe-stack-events --stack-name app-platform \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`].{logical:LogicalResourceId,reason:ResourceStatusReason,ts:Timestamp}' \
  --output table
```

If the only `CREATE_FAILED` resource is TaskRole and its
`ResourceStatusReason` names `CAPABILITY_IAM`, the diagnosis is
confirmed. The fix is to delete the stack and re-create with
`--capabilities CAPABILITY_IAM` (or `CAPABILITY_NAMED_IAM` if any
IAM resource uses a custom name).

## Related scenarios

The same skill handles:

- **UPDATE_FAILED with `Replacement: true`** — the ChangeSet column
  is the diagnostic surface, not `describe-stack-events` alone.
- **DELETE_FAILED on a non-empty S3 bucket** — empty both objects
  AND versions; add a `Custom::S3Cleanup` for repeatable teardowns.
- **UPDATE_ROLLBACK_FAILED on a nested stack** — drill into the
  child; use `ContinueUpdateRollback --resources-to-skip` to recover.
- **ROLLBACK_FAILED after a CREATE with custom-resource signal
  timeout** — fix the Lambda handler to send `SUCCESS`; do not retry
  `update-stack` blindly.
