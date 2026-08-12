# Eval prompt: parameter-group-mismatch-standby

Diagnose the Multi-AZ failover issue for the following scenario. Walk
the diagnostic decision tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, ROOT_CAUSE, EVIDENCE, REMEDIATION).

Symptom: Multi-AZ RDS PostgreSQL instance `prod-postgres` failed over.
The standby instance started promotion but failed health checks during
the promotion phase. The RDS event log shows "DB instance has
configuration mismatch with primary." The standby's DB parameter group
differs from the primary's.

```text
DBInstanceIdentifier: prod-postgres
Engine: postgres
EngineVersion: 16.2
MultiAZ: true
DBInstanceClass: db.r6i.4xlarge

Primary DBParameterGroups:
  - prod-pg-params-v2 (status: applied)
    max_connections=500, shared_buffers=12GB, work_mem=64MB

Standby DBParameterGroups:
  - default.postgres16 (status: applied)
    max_connections=200 (default), shared_buffers=256MB (default),
    work_mem=4MB (default)

RDS events:
  09:10:00 — RDS-EVENT-0049: Multi-AZ failover started
  09:11:30 — Configuration mismatch detected during promotion
  09:12:00 — RDS-EVENT-0006: DB instance failover failed
    (reason: parameter group mismatch)

CloudWatch metrics:
  DatabaseConnections: dropped to 0 at failover start
  No recovery after 10 minutes

DBInstanceStatus: available (reverted to primary; standby unhealthy)
```

A parameter group mismatch between primary and standby can prevent
the standby from passing health checks during promotion. Verify the
parameter group configuration and recommend the fix.
