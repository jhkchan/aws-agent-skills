# Eval prompt: cfn-drift-deleted-iam-role

Diagnose the following CloudFormation drift report. Walk the
diagnostic decision tree and emit the standard VERDICT block
(INCIDENT, VERDICT, ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG,
RESOLUTION, REMEDIATION).

## Scenario

A CloudFormation stack `app-platform` in `us-east-1` reports
`StackDriftStatus: DRIFTED`.

## Known facts

- `describe-stacks` shows `StackStatus: CREATE_COMPLETE`,
  `StackDriftStatus: DRIFTED`.
- `describe-stack-resource-drifts` shows the `TaskRole` resource
  (`AWS::IAM::Role`, physical id `app-platform-TaskRole-abc`) with
  `ResourceDriftStatus: DELETED`.
- The physical IAM role no longer exists —
  `aws iam get-role --role-name app-platform-TaskRole-abc` returns
  `NoSuchEntity`.
- CloudTrail shows a `DeleteRole` event at `2026-08-03T15:22:11Z`
  by `arn:aws:iam::111122223333:user/cleanup-bot`.
- No other resources in the stack reference `TaskRole` via `Ref` or
  `GetAtt` (it is a standalone role assumed by ECS tasks in another
  account).

## Symptom

The operator needs to decide whether to recreate the role via stack
update or remove it from the template.
