# Eval prompt: remove-replica-blocked-active-traffic

Plan the following DynamoDB Global Tables operation. Run the pre-check
gate and emit the standard VERDICT block (OPERATION, VERDICT, TARGET,
PRE_CHECKS, STEPS, POST_VERIFY, REPLICA_STATUS, NOTES).

## Scenario

We want to remove the `us-west-2` replica from our DynamoDB Global Table
`orders-prod`.

## Known facts

- `describe-global-table` shows:
  - ReplicationGroup: `[{RegionName: us-east-1, ReplicaStatus: ACTIVE}, {RegionName: us-west-2, ReplicaStatus: ACTIVE}, {RegionName: eu-west-1, ReplicaStatus: ACTIVE}]`
- No replica is in `CREATING` or `DELETING` state
- CloudWatch metrics for `us-west-2`:
  - `ConsumedReadCapacityUnits`: averaging 5,000/min over the last hour
  - `ConsumedWriteCapacityUnits`: averaging 2,000/min over the last hour
- The application has NOT been redirected away from us-west-2
- The application's DynamoDB client is configured with us-west-2 as
  one of its active regions
- Table size: approximately 80 GB

## Desired operation

Remove `us-west-2` from the `orders-prod` global table.
