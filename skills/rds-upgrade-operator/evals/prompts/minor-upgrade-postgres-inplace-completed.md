# Eval prompt: minor-upgrade-postgres-inplace-completed

Plan the following RDS Aurora PostgreSQL minor version upgrade and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: minor-upgrade
Cluster: prod-orders-cluster
Target engine version: 14.11

```json
{
  "ClusterMetadata": {
    "DBClusterIdentifier": "prod-orders-cluster",
    "Status": "available",
    "Engine": "aurora-postgresql",
    "EngineVersion": "14.10",
    "DBClusterParameterGroup": "default.aurora-postgresql14",
    "MultiAZ": false,
    "StorageEncrypted": true
  },
  "InstanceMetadata": {
    "DBInstanceClass": "db.r6g.large",
    "PerformanceInsightsEnabled": true,
    "AutoMinorVersionUpgrade": false
  },
  "EngineVersionCheck": {
    "aurora-postgresql 14.11 is a valid upgrade target from 14.10": true
  },
  "PendingModifications": "none",
  "PreUpgradeSnapshot": {
    "prod-orders-pre-14-11": "available (taken 2026-08-10 02:50 UTC)"
  },
  "ApplicationDriver": "PostgreSQL JDBC 42.7.2 (supports PG 14.x)"
}
```
