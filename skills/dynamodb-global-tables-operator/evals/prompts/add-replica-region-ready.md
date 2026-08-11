# Eval prompt: add-replica-region-ready

Plan the following DynamoDB Global Tables operation. Run the pre-check
gate and emit the standard VERDICT block (OPERATION, VERDICT, TARGET,
PRE_CHECKS, STEPS, POST_VERIFY, REPLICA_STATUS, NOTES).

## Scenario

We want to add a third replica region (`eu-west-1`) to our DynamoDB
Global Table `orders-prod`.

## Known facts

- `describe-global-table` shows:
  - `GlobalTableName: orders-prod`
  - ReplicationGroup: `[{RegionName: us-east-1, ReplicaStatus: ACTIVE}, {RegionName: us-west-2, ReplicaStatus: ACTIVE}]`
- No replica is in `CREATING` or `DELETING` state
- `describe-table` (both regions): `TableStatus: ACTIVE`, `BillingMode: PAY_PER_REQUEST`
- `eu-west-1` does NOT currently have a replica
- PITR status: `ENABLED` in us-east-1 and us-west-2
- IAM simulation: caller role has `dynamodb:UpdateGlobalTable` and
  `dynamodb:CreateTable` in eu-west-1
- Table size: approximately 50 GB
- The application is ready to route traffic to eu-west-1 after the
  replica becomes ACTIVE

## Desired operation

Add `eu-west-1` as a new replica region to the `orders-prod` global table.
