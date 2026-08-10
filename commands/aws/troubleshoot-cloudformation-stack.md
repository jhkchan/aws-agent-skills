---
name: troubleshoot-cloudformation-stack
description: >-
  Slash command for the cloudformation-stack-troubleshooter skill.
  Diagnoses AWS CloudFormation stack failures across the lifecycle —
  CREATE_FAILED (IAM permission, service limit, resource already
  exists, invalid property, CAPABILITY_IAM missing), UPDATE_FAILED
  (Replacement required, immutable property, drift), DELETE_FAILED
  (S3 bucket not empty, dependent resources, DeletionPolicy:Retain),
  ROLLBACK_FAILED (stack stuck in ROLLBACK_COMPLETE), and
  UPDATE_ROLLBACK_FAILED (nested stack cannot roll back). Walks
  describe-stack-events ResourceStatusReason, describe-stacks,
  describe-change-set, and drift detection. Emits
  ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE with the specific
  failure category and offending config element.
skill: cloudformation-stack-troubleshooter
family: DevTools
task_type: troubleshoot
verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
allowed-tools: Read, Bash, Grep, Glob
---

# /aws:troubleshoot-cloudformation-stack

Invoke the `cloudformation-stack-troubleshooter` skill to diagnose a
CloudFormation stack failure.

Read the skill at
`skills/cloudformation-stack-troubleshooter/SKILL.md` and follow its
diagnostic procedure to identify the root cause.

## When to use

- A stack's `create-stack` failed and the stack is in
  `ROLLBACK_COMPLETE`.
- A stack's `update-stack` failed and the stack is in
  `UPDATE_FAILED` / `UPDATE_ROLLBACK_COMPLETE` /
  `UPDATE_ROLLBACK_FAILED`.
- A stack's `delete-stack` failed with `DELETE_FAILED` on an S3
  bucket, a dependent resource, or a custom resource.
- A ChangeSet reports `Replacement: true` on a critical resource and
  you need to plan a safe path forward.
- A stack is stuck in `ROLLBACK_COMPLETE` and you cannot update it.
- A nested stack cannot roll back and the parent is in
  `UPDATE_ROLLBACK_FAILED`.
- A `CreationPolicy` signal was never satisfied (EC2 / ASG without
  cfn-signal).
- You need to recover via `ContinueUpdateRollback` or
  `import-resources`.

## Invocation

```
/aws:troubleshoot-cloudformation-stack <stack name / ARN / symptom description>
```

The skill will:

1. Identify the failure category (CREATE_FAILED, UPDATE_FAILED,
   DELETE_FAILED, ROLLBACK_FAILED, UPDATE_ROLLBACK_FAILED).
2. Request the stack name, region, StackStatus, and
   `describe-stack-events` output for the failing resource.
3. Walk the category-specific diagnostic tree.
4. Cross-reference the ChangeSet (`Replacement`, `Scope`), the
   execution role via `iam simulate-principal-policy`, drift
   detection, and the Lambda logs for custom resources as required.
5. Map to the common root-cause catalog (14 patterns covering the
   most common CloudFormation failures).
6. Validate the proposed fix via a ChangeSet before applying.
7. Emit the standard VERDICT block.

## Output shape

```text
INCIDENT: <stack name or ARN> in <region>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <category name> — <specific failing config element>
EVIDENCE:
  - describe-stacks: <StackStatus + StackStatusReason>
  - describe-stack-events: <ResourceStatus + ResourceStatusReason>
  - describe-change-set: <Action + Replacement, if UPDATE>
  - iam simulate-principal-policy: <decision, if IAM>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION: <specific template / IAM / ChangeSet change + verification>
```

## Pre-flight

The skill requires the stack name (or ARN) and the region. If only a
partial name is provided, the skill will run
`aws cloudformation list-stacks --stack-status-filter CREATE_FAILED
UPDATE_FAILED UPDATE_ROLLBACK_FAILED DELETE_FAILED ROLLBACK_COMPLETE
UPDATE_ROLLBACK_COMPLETE` to surface recently-failing stacks. If the
user provides only a vague symptom with no stack name, the skill emits
`NEED_MORE_INFO`.

## References

- Skill: `skills/cloudformation-stack-troubleshooter/SKILL.md`
- Reference: `skills/cloudformation-stack-troubleshooter/references/failure-catalog-and-decision-tree.md`
- Reference: `skills/cloudformation-stack-troubleshooter/references/diagnostic-commands.md`
- AWS docs: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html
