# Eval prompt: planned-failover-promote-replica-ready

Plan the following Aurora planned failover operation and emit the standard
VERDICT block.

Cluster: prod-orders-cluster-planned-failover-promote-replica-ready
Region: us-east-1
Operation: planned-failover
Target replica to promote: prod-orders-node-2

```json
{
  "Cluster": {
    "DBClusterIdentifier": "prod-orders-cluster-planned-failover-promote-replica-ready",
    "DBClusterStatus": "available",
    "Engine": "aurora-mysql",
    "MultiAZ": true,
    "GlobalClusterIdentifier": null,
    "ActivityStreamStatus": "stopped",
    "StorageEncrypted": true
  },
  "Members": [
    {"DBInstanceIdentifier": "prod-orders-node-1", "IsClusterWriter": true, "AvailabilityZone": "us-east-1a"},
    {"DBInstanceIdentifier": "prod-orders-node-2", "IsClusterWriter": false, "AvailabilityZone": "us-east-1b", "DBInstanceStatus": "available", "AuroraReplicaLag": 8},
    {"DBInstanceIdentifier": "prod-orders-node-3", "IsClusterWriter": false, "AvailabilityZone": "us-east-1c", "DBInstanceStatus": "available", "AuroraReplicaLag": 12}
  ],
  "RDSProxy": {
    "ProxyName": "prod-orders-proxy",
    "TargetGroupHealth": "HEALTHY"
  }
}
```
