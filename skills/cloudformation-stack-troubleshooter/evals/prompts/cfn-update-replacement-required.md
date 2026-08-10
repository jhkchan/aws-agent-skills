# Eval prompt: cfn-update-replacement-required

Diagnose the following CloudFormation stack failure. Walk the
UPDATE_FAILED decision tree and emit the standard VERDICT block.

## Scenario

A CloudFormation stack `orders-table` in `us-east-1` failed to update
after a template change that modifies the `KeySchema` of the
`OrdersTable` resource (`AWS::DynamoDB::Table`) from a simple primary
key (`[{AttributeName: id, KeyType: HASH}]`) to a composite key
(`[{AttributeName: id, KeyType: HASH}, {AttributeName: ts,
KeyType: RANGE}]`).

## Known facts

- The operator first created a ChangeSet, then executed it (good
  practice — they did NOT run `update-stack` blind).
- `describe-change-set` for the most recent ChangeSet shows
  `OrdersTable`:
  - `Action: Modify`
  - `Replacement: True`
  - `Scope: ["Properties"]`
  - `DetailedStatus: ...` indicates the `KeySchema` property change
    triggers replacement.
- `describe-stack-events` shows `OrdersTable` with:
  - `ResourceStatus: UPDATE_FAILED`
  - `ResourceStatusReason: "Resource update cancelled"` (cascaded
    from the replacement refusal the operator did not authorise in
    time, plus a downstream IAM-denied `dynamodb:UpdateTable`).
- `describe-stacks` shows:
  - `StackStatus: UPDATE_ROLLBACK_COMPLETE` (rollback succeeded).
- `cfn-lint template.yaml` returns clean (no template error — the
  behaviour is the immutable property, not a syntactic bug).

## Symptom

The operator needs to know why the update failed and how to make the
schema change safely without losing the existing table data.
