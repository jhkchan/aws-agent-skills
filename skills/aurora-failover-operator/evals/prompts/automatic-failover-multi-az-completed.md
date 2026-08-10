# Eval prompt: automatic-failover-multi-az-completed

An automatic Aurora failover has already completed. Emit the standard
VERDICT block with COMPLETED and all post-verification results.

Cluster: prod-inventory-cluster-automatic-failover-multi-az-completed
Region: us-east-1
Operation: automatic (failover already completed)

```json
{
  "Cluster": {
    "DBClusterIdentifier": "prod-inventory-cluster-automatic-failover-multi-az-completed",
    "DBClusterStatus": "available",
    "Engine": "aurora-postgresql",
    "MultiAZ": true
  },
  "Members": [
    {"DBInstanceIdentifier": "prod-inventory-node-2", "IsClusterWriter": true, "AvailabilityZone": "us-east-1b", "PromotedAt": "2026-08-07T10:03:12Z"},
    {"DBInstanceIdentifier": "prod-inventory-node-1", "IsClusterWriter": false, "AvailabilityZone": "us-east-1a", "AuroraReplicaLag": 12},
    {"DBInstanceIdentifier": "prod-inventory-node-3", "IsClusterWriter": false, "AvailabilityZone": "us-east-1c", "AuroraReplicaLag": 8}
  ],
  "FailoverEvent": {
    "Detection": "2026-08-07T10:02:15Z",
    "Promotion": "2026-08-07T10:03:12Z",
    "DurationSeconds": 57
  },
  "RDSProxy": {
    "ProxyName": "prod-inventory-proxy",
    "TargetGroupHealth": "HEALTHY"
  },
  "PostFailoverVerification": {
    "WriterEndpointResolvesToNode2": "PASS",
    "InnodbReadOnlyReturns0": "PASS",
    "ReaderEndpointLoadBalancesNode1AndNode3": "PASS",
    "ReplicaLagUnder100ms": "PASS"
  }
}
```
