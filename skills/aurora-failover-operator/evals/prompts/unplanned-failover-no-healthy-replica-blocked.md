# Eval prompt: unplanned-failover-no-healthy-replica-blocked

Plan the following Aurora unplanned failover operation and emit the
standard VERDICT block.

Cluster: prod-checkout-cluster-unplanned-failover-no-healthy-replica-blocked
Region: us-east-1
Operation: unplanned-failover

```json
{
  "Cluster": {
    "DBClusterIdentifier": "prod-checkout-cluster-unplanned-failover-no-healthy-replica-blocked",
    "DBClusterStatus": "available",
    "Engine": "aurora-mysql",
    "MultiAZ": false
  },
  "Members": [
    {"DBInstanceIdentifier": "prod-checkout-node-1", "IsClusterWriter": true, "DBInstanceStatus": "available", "HealthCheck": "UNREACHABLE (failing for 60s)"},
    {"DBInstanceIdentifier": "prod-checkout-node-2", "IsClusterWriter": false, "DBInstanceStatus": "creating", "HealthCheck": "N/A (not yet available)"}
  ],
  "OtherReaders": []
}
```

The primary writer (prod-checkout-node-1) is unreachable. The only reader
(prod-checkout-node-2) is in 'creating' status — recently launched and
not yet available for promotion.
