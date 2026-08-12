# Eval prompt: major-upgrade-blue-green-review-required

Plan the following Aurora MySQL major version upgrade via blue/green
deployment and emit the standard VERDICT block (OPERATION, VERDICT, TARGET,
PRE_CHECKS, STEPS, POST_VERIFY, NOTES).

Operation: blue-green-upgrade
Cluster: prod-payments-cluster
Target engine version: 8.0.mysql_aurora.3.04.0

```json
{
  "ClusterMetadata": {
    "DBClusterIdentifier": "prod-payments-cluster",
    "Status": "available",
    "Engine": "aurora-mysql",
    "EngineVersion": "5.7.mysql_aurora.2.11.4",
    "DBClusterParameterGroup": "aurora-mysql5.7-payments-custom"
  },
  "TargetParameterGroup": "aurora-mysql8.0-payments-custom (exists, diffed — 12 custom params reproduced)",
  "TargetOptionGroup": "aurora-mysql8.0-payments-opts (exists; MEMCACHED option removed — not supported in 8.0)",
  "PreUpgradeSnapshot": "prod-payments-pre-8-0 (available)",
  "ApplicationDriver": "MySQL Connector/J 5.1.49",
  "BlueGreenTarget": "aurora-mysql 8.0.mysql_aurora.3.04.0"
}
```
