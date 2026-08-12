# Eval prompt: failover-priority-tier-wrong-instance

Diagnose the Aurora failover issue for the following scenario. Walk
the diagnostic decision tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, ROOT_CAUSE, EVIDENCE, REMEDIATION).

Symptom: Aurora PostgreSQL cluster `analytics-db-cluster` failed over.
The application expected `instance-reader-large` (db.r6g.2xlarge) to
become the new writer. Instead, `instance-reader-small`
(db.r6g.large) was promoted, causing performance issues because the
smaller instance class cannot handle the write workload.

```text
DBClusterIdentifier: analytics-db-cluster
Engine: aurora-postgresql
EngineVersion: 16.2

DBClusterMembers (before failover):
  - instance-writer: writer, db.r6g.2xlarge, PromotionTier=0
  - instance-reader-large: reader, db.r6g.2xlarge, PromotionTier=15
  - instance-reader-small: reader, db.r6g.large, PromotionTier=0

DBClusterMembers (after failover):
  - instance-reader-small: NOW WRITER, db.r6g.large (PromotionTier=0)
  - instance-reader-large: still reader, db.r6g.2xlarge (PromotionTier=15)
  - instance-writer: now reader, db.r6g.2xlarge (PromotionTier=0)

CloudWatch metrics (post-failover):
  CPUUtilization on instance-reader-small: 95% (overloaded)
  DatabaseConnections to instance-reader-small: 450 (pool exhausted)

RDS events:
  Failover completed; instance-reader-small promoted
```

Aurora failover tier 0 is promoted first. The intended target
(instance-reader-large) has tier 15. Verify the failover priority
configuration and recommend the fix.
