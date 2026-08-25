# Worked Examples (load on demand) — DynamoDB Global Tables Operator

Secondary worked examples moved verbatim from SKILL.md; the primary add-replica (READY) example remains inline in SKILL.md. Loaded on demand.

---

## Worked example — remove replica blocked by active traffic (moved from SKILL.md)

```text
OPERATION: remove-replica
VERDICT: BLOCKED
TARGET: orders-prod global table, removing replica in us-west-2
PRE_CHECKS:
  - [PASS] Global table orders-prod exists
  - [PASS] All current replicas ACTIVE
  - [PASS] No replica in CREATING or DELETING state
  - [PASS] us-west-2 has an ACTIVE replica
  - [FAIL] us-west-2 is receiving active application traffic —
    CloudWatch ConsumedReadCapacityUnits averages 5,000/min and
    ConsumedWriteCapacityUnits averages 2,000/min. Removing the region
    will cause application failures if traffic is not redirected first.
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
REPLICA_STATUS:
  - us-east-1: ACTIVE
  - us-west-2: ACTIVE (BLOCKED from removal — active traffic)
NOTES:
  - Redirect application traffic from us-west-2 to another region
    BEFORE removing the replica.
  - Verify CloudWatch ConsumedReadCapacityUnits and
    ConsumedWriteCapacityUnits in us-west-2 drop to near-zero.
  - Then re-run this operation.
```

---

## Worked example — regional failover (COMPLETED) (moved from SKILL.md)

```text
OPERATION: failover
VERDICT: COMPLETED
TARGET: orders-prod global table, application failover from us-east-1
  to us-west-2
PRE_CHECKS:
  - [PASS] us-west-2 replica is ACTIVE
  - [PASS] ReplicationLatency us-east-1 -> us-west-2: 0.3s average
  - [PASS] Application SDK configured with RegionSwitchingRetryPolicy
  - [PASS] us-west-2 PITR is ENABLED
STEPS:
  1. Application SDK failover triggered (Route 53 health check detected
    us-east-1 degradation at 2026-08-09T10:15Z)
  2. Application now writing to us-west-2 endpoint:
     arn:aws:dynamodb:us-west-2:111111111111:table/orders-prod
  3. Verified write success: test item inserted at 2026-08-09T10:17Z
  4. Verified replication to us-east-1 will resume when region recovers
POST_VERIFY:
  - [PASS] Application writes succeeding in us-west-2
  - [PASS] Application reads succeeding in us-west-2
  - [PASS] ReplicationLatency from us-west-2 to eu-west-1: 0.8s
  - [PASS] No data loss detected (LWW conflicts monitored)
REPLICA_STATUS:
  - us-east-1: ACTIVE (degraded — AWS Health Dashboard confirms
    regional service degradation)
  - us-west-2: ACTIVE (now the application's primary write region)
  - eu-west-1: ACTIVE
NOTES:
  - Failover is application-level. DynamoDB Global Tables does NOT
    automatically redirect traffic. The application SDK's
    RegionSwitchingRetryPolicy detected the failure and switched.
  - When us-east-1 recovers, replication resumes automatically. Writes
    that occurred during the outage in us-west-2 will replicate back
    to us-east-1.
  - LWW conflict risk: if the application wrote to us-east-1 during
    the degradation window AND to us-west-2 after failover, the
    us-west-2 writes win (later timestamp). Audit conflicting items
    post-recovery.
  - Do NOT remove the us-east-1 replica during the outage. It will
    recover and resume replication automatically.
```
