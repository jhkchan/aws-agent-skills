# Eval prompt: regional-failover-completed

Report on the following DynamoDB Global Tables failover operation. Verify
the post-failover state and emit the standard VERDICT block.

## Scenario

AWS Health Dashboard confirms a regional service degradation in
`us-east-1` affecting DynamoDB. The application has already failed over
to `us-west-2`.

## Known facts

- `describe-global-table` shows:
  - ReplicationGroup: `[{RegionName: us-east-1, ReplicaStatus: ACTIVE}, {RegionName: us-west-2, ReplicaStatus: ACTIVE}, {RegionName: eu-west-1, ReplicaStatus: ACTIVE}]`
- AWS Health Dashboard: `us-east-1` DynamoDB degradation confirmed
  at 2026-08-09T10:15Z
- Before the degradation, `ReplicationLatency` us-east-1 to us-west-2
  averaged 0.3 seconds
- The application SDK has `RegionSwitchingRetryPolicy` configured
- Route 53 health check detected the degradation and switched the
  application to us-west-2 at 2026-08-09T10:16Z
- Test writes to us-west-2 succeed (confirmed at 2026-08-09T10:17Z)
- PITR status in us-west-2: `ENABLED`
- Current ReplicationLatency us-west-2 to eu-west-1: 0.8s average
- The application is successfully reading and writing in us-west-2

## Desired operation

Verify the failover is complete and emit the COMPLETED verdict with
post-verification and notes.
