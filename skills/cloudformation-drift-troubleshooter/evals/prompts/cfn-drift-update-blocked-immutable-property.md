# Eval prompt: cfn-drift-update-blocked-immutable-property

Diagnose the following CloudFormation drift report. Walk the
diagnostic decision tree and emit the standard VERDICT block
(INCIDENT, VERDICT, ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG,
RESOLUTION, REMEDIATION).

## Scenario

A CloudFormation stack `orders-db-stack` in `us-east-1` reports
`StackDriftStatus: DRIFTED`. The operator attempted an unrelated
stack update, which surfaced the drift.

## Known facts

- `describe-stacks` shows `StackStatus: CREATE_COMPLETE`,
  `StackDriftStatus: DRIFTED`.
- `describe-stack-resource-drifts` shows the `OrdersDB` resource
  (`AWS::RDS::DBInstance`, physical id `orders-db-prod-v2`) with:
  - `ResourceDriftStatus: MODIFIED`
  - one `PropertyDifference` on `PropertyPath: /DBInstanceIdentifier`
  - `ExpectedValue: "orders-db-prod"`
  - `ActualValue: "orders-db-prod-v2"`
  - `DifferenceType: NOT_EQUAL`
- CloudTrail shows a `ModifyDBInstance` event at
  `2026-08-02T10:11:00Z` by
  `arn:aws:iam::111122223333:user/dba-carol` renaming the instance.
- `DBInstanceIdentifier` is immutable — a stack update that touches
  this property triggers `Replacement: True` (delete + recreate).
- The operator does NOT want the database replaced — the rename
  was a mistake and must be reverted.
- RDS supports renaming a DB instance via `modify-db-instance
  --new-db-instance-identifier` without data loss.

## Symptom

The operator needs to clear the drift safely without triggering
RDS instance replacement.
