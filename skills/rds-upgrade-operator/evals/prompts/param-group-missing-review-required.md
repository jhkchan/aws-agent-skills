# Eval prompt: param-group-missing-review-required

Plan the following Aurora PostgreSQL major version upgrade (13 to 14) and
emit the standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, NOTES).

Operation: major-upgrade
Cluster: prod-analytics-cluster
Target engine version: 14.9

```json
{
  "ClusterMetadata": {
    "DBClusterIdentifier": "prod-analytics-cluster",
    "Status": "available",
    "Engine": "aurora-postgresql",
    "EngineVersion": "13.8",
    "DBClusterParameterGroup": "aurora-postgresql13-analytics-custom (15 custom parameters: shared_preload_libraries, max_connections, work_mem, etc.)"
  },
  "ParameterGroupCheck": {
    "NoCustomAuroraPostgresql14Group": true,
    "OnlyDefault": "default.aurora-postgresql14 (cannot reproduce 15 custom parameters)"
  },
  "OptionGroup": "default.aurora-postgresql14 (compatible)",
  "PreUpgradeSnapshot": "prod-analytics-pre-14 (available)",
  "ApplicationDriver": "psycopg2 2.9.9 (supports PG 14)"
}
```
