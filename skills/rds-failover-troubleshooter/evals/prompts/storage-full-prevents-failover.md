# Eval prompt: storage-full-prevents-failover

Diagnose the Multi-AZ failover issue for the following scenario. Walk
the diagnostic decision tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, ROOT_CAUSE, EVIDENCE, REMEDIATION).

Symptom: Multi-AZ RDS MySQL instance `prod-mysql` failed over
automatically when the primary became unresponsive. The failover
event appeared in RDS events but the standby did not become available.
Error: `FailoverFailed` and `InsufficientStorage`.

```text
DBInstanceIdentifier: prod-mysql
Engine: mysql
EngineVersion: 8.0.35
MultiAZ: true
DBInstanceClass: db.m6i.2xlarge
AllocatedStorage: 500 GB
StorageType: gp3

RDS events (last 2 hours):
  02:15:00 — RDS-EVENT-0065: DB instance has insufficient storage
  02:17:30 — RDS-EVENT-0049: Multi-AZ failover started
  02:18:45 — RDS-EVENT-0006: DB instance failover failed
    (reason: InsufficientStorage)

CloudWatch metrics:
  FreeStorageSpace (last 6 hours): dropped from 50 GB to 0.5 GB
  DiskQueueDepth: spiked to 800 (sustained high I/O wait)
  WriteLatency: increased 10x

DBInstanceStatus: storage-full

Application impact: complete database outage since 02:15 UTC
```

A storage-full instance cannot complete failover because the new
writer cannot write the recovery log. Verify the storage state and
recommend the fix.
