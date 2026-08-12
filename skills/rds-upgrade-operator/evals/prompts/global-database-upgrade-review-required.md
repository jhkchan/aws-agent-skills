# Eval prompt: global-database-upgrade-review-required

Plan the following global Aurora MySQL cluster major version upgrade (5.7
to 8.0) and emit the standard VERDICT block (OPERATION, VERDICT, TARGET,
PRE_CHECKS, STEPS, POST_VERIFY, NOTES).

Operation: global-upgrade
Global cluster: global-payments-cluster
Target engine version: 8.0.mysql_aurora.3.04.0

```json
{
  "GlobalClusterMetadata": {
    "GlobalClusterIdentifier": "global-payments-cluster",
    "Engine": "aurora-mysql",
    "EngineVersion": "5.7.mysql_aurora.2.11.4",
    "Primary": {"Region": "us-east-1", "Cluster": "prod-payments-cluster"},
    "Secondaries": [
      {"Region": "eu-west-1", "Cluster": "prod-payments-eu"},
      {"Region": "ap-southeast-1", "Cluster": "prod-payments-apac"}
    ]
  },
  "AllClustersStatus": "available",
  "SupportsGlobalDatabasesForTarget": true,
  "TargetParameterGroups": "aurora-mysql8.0-global-payments exists in all three Regions",
  "DataSizePerRegion": "~500 GB"
}
```
