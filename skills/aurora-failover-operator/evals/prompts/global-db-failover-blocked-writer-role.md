# Eval prompt: global-db-failover-blocked-writer-role

The operator requests a standalone failover-db-cluster on an Aurora cluster
that is the WRITER in a Global Database. Evaluate and emit the standard
VERDICT block.

Cluster: prod-global-primary-global-db-failover-blocked-writer-role
Region: us-east-1
Operation: planned-failover (operator requests
  failover-db-cluster targeting prod-global-node-2)

```json
{
  "Cluster": {
    "DBClusterIdentifier": "prod-global-primary-global-db-failover-blocked-writer-role",
    "DBClusterStatus": "available",
    "Engine": "aurora-mysql"
  },
  "Members": [
    {"DBInstanceIdentifier": "prod-global-node-1", "IsClusterWriter": true, "AvailabilityZone": "us-east-1a"},
    {"DBInstanceIdentifier": "prod-global-node-2", "IsClusterWriter": false, "AvailabilityZone": "us-east-1b", "DBInstanceStatus": "available", "AuroraReplicaLag": 5}
  ],
  "GlobalCluster": {
    "GlobalClusterIdentifier": "prod-global-cluster",
    "PrimaryRegion": "us-east-1",
    "Members": [
      {"Region": "us-east-1", "Role": "WRITER", "DBClusterIdentifier": "prod-global-primary-global-db-failover-blocked-writer-role"},
      {"Region": "eu-west-1", "Role": "READER", "DBClusterIdentifier": "prod-global-secondary"}
    ],
    "ReplicationLagSeconds": 0.4
  }
}
```

The operator wants to failover within us-east-1 to promote
prod-global-node-2. Evaluate whether this is safe.
