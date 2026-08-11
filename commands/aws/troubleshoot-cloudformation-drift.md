---
name: troubleshoot-cloudformation-drift
description: >-
  Slash command for the cloudformation-drift-troubleshooter skill.
  Diagnoses CloudFormation stack drift — resources whose actual
  configuration diverged from the template because they were
  changed, deleted, or added outside CloudFormation. Walks
  detect-stack-drift, describe-stack-drift-detection-status, and
  describe-stack-resource-drifts to classify each drift as
  MODIFIED (property changed outside CFN), DELETED (resource
  deleted outside CFN), or ADDITION (new resource not in stack).
  Forensic walk via CloudTrail + AWS Config identifies the
  out-of-band actor and change time. Recommends a resolution
  strategy: IMPORT existing resources (resource import /
  import-resources), drift reset (update template to match
  drift), revert resource to match template, or remove from
  template. Cross-references the immutable-property table to
  warn when an update would trigger Replacement. Covers drift
  prevention via IAM policy with aws:CalledViaFirst,
  CloudFormation Hooks, and Conformance Packs. Handles nested
  stack drift and CDK drift. Emits ROOT_CAUSE_FOUND |
  NEED_MORE_INFO | ESCALATE with the specific drift type,
  offending resource, and resolution strategy.
skill: cloudformation-drift-troubleshooter
family: DevTools
task_type: troubleshoot
verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
allowed-tools: Read, Bash, Grep, Glob
---

# /aws:troubleshoot-cloudformation-drift

Invoke the `cloudformation-drift-troubleshooter` skill to diagnose a
CloudFormation stack drift report.

Read the skill at
`skills/cloudformation-drift-troubleshooter/SKILL.md` and follow its
diagnostic procedure to identify the root cause and resolution.

## When to use

- A stack reports `StackDriftStatus: DRIFTED` and you need to know
  which resources drifted, who changed them, and how to resolve.
- A stack `UPDATE_FAILED` and the cause cites drift (out-of-band
  changes conflict with the proposed update).
- A resource was modified or deleted outside CloudFormation
  (console / SDK / CLI) and you need to align stack and reality.
- A new resource exists in the account that should be brought under
  stack management via `import-resources`.
- A `MODIFIED` drift is on an immutable property and you need to
  avoid triggering Replacement on the next stack update.
- A nested stack reports drift and you need to drill into the child.
- A CDK stack reports drift via `cdk drift` and you need
  resource-level detail.
- A compliance pack reports stack drift and you need to triage.

## Invocation

```
/aws:troubleshoot-cloudformation-drift <stack name / ARN / drift symptom>
```

The skill will:

1. Capture the drift signal (stack name/ARN, region, StackDriftStatus,
   last detection time).
2. Refresh drift detection (`detect-stack-drift` →
   `describe-stack-drift-detection-status`).
3. Read `describe-stack-resource-drifts` and classify each drift
   (MODIFIED / DELETED / ADDITION / NOT_CHECKED).
4. Run the forensic walk via CloudTrail (`lookup-events`) and AWS
   Config (`get-resource-config-history`) to identify the out-of-band
   actor and change time.
5. Probe update impact via a no-op ChangeSet to detect immutable
   properties that would trigger Replacement.
6. Choose a resolution: IMPORT, RESET_TO_DRIFT, REVERT_TO_TEMPLATE,
   REMOVE_FROM_TEMPLATE, or ESCALATE_TO_OWNER.
7. Validate via ChangeSet (or `--change-set-type IMPORT`) before
   applying.
8. Recommend a prevention mechanism: IAM policy with
   `aws:CalledViaFirst`, CloudFormation Hook, or Conformance Pack.
9. Emit the standard VERDICT block.

## Output shape

```text
INCIDENT: <stack name or ARN> in <region> — StackDriftStatus <status>, <N> drifted resource(s)
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <MODIFIED | DELETED | ADDITION> on <LogicalResourceId (PhysicalResourceId)> — <actor and trigger>
EVIDENCE:
  - describe-stacks: <StackStatus, StackDriftStatus, LastDriftDetectionDateTime>
  - describe-stack-resource-drifts: <ResourceDriftStatus + PropertyDifferences per resource>
  - CloudTrail: <eventName, eventSource, eventTime, userIdentityarn>
  - Config timeline: <configurationItem captureTime + diff>
  - describe-change-set: <Action + Replacement for the proposed fix>
ROOT_CAUSE_CATALOG: #<N>
RESOLUTION: <IMPORT | RESET_TO_DRIFT | REVERT_TO_TEMPLATE | REMOVE_FROM_TEMPLATE | ESCALATE_TO_OWNER>
REMEDIATION: <exact CLI sequence + verification + prevention>
```

## Pre-flight

The skill requires the stack name (or ARN) and the region. If only a
partial name is provided, the skill will run
`aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE
UPDATE_COMPLETE UPDATE_ROLLBACK_COMPLETE IMPORT_COMPLETE
IMPORT_ROLLBACK_COMPLETE` to surface candidate stacks. If the user
provides only a vague symptom with no stack name, the skill emits
`NEED_MORE_INFO`.

## References

- Skill: `skills/cloudformation-drift-troubleshooter/SKILL.md`
- Reference: `skills/cloudformation-drift-troubleshooter/references/drift-types-and-resolution.md`
- Reference: `skills/cloudformation-drift-troubleshooter/references/diagnostic-commands.md`
- AWS docs: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html
