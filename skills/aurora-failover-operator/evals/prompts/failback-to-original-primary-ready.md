# Eval prompt: failback-to-original-primary-ready

Plan the following Aurora failback operation (promote the original writer
back after a planned failover) and emit the standard VERDICT block.

Cluster: prod-orders-cluster-failback-to-original-primary-ready
Region: us-east-1
Operation: failback (promote original writer prod-orders-node-1 back)

```json
{
  "Cluster": {
    "DBClusterIdentifier": "prod-orders-cluster-failback-to-original-primary-ready",
    "DBClusterStatus": "available",
    "Engine": "aurora-mysql",
    "MultiAZ": true,
    "GlobalClusterIdentifier": null,
    "ActivityStreamStatus": "stopped"
  },
  "Members": [
    {"DBInstanceIdentifier": "prod-orders-node-2", "IsClusterWriter": true, "AvailabilityZone": "us-east-1b", "DBInstanceStatus": "available", "Note": "promoted during planned failover 2h ago"},
    {"DBInstanceIdentifier": "prod-orders-node-1", "IsClusterWriter": false, "AvailabilityZone": "us-east-1a", "DBInstanceStatus": "available", "AuroraReplicaLag": 10, "Note": "original writer, now reader"},
    {"DBInstanceIdentifier": "prod-orders-node-3", "IsClusterWriter": false, "AvailabilityZone": "us-east-1c", "DBInstanceStatus": "available", "AuroraReplicaLag": 8}
  ],
  "RDSProxy": {
    "ProxyName": "prod-orders-proxy",
    "TargetGroupHealth": "HEALTHY"
  },
  "FailbackReason": "AZ maintenance completed; prefer node-1 in us-east-1a as writer for latency optimization."
}
```
