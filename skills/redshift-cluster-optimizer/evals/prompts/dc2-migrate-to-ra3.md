# Eval prompt: dc2-migrate-to-ra3

Optimise the following Amazon Redshift cluster and emit the standard
optimisation block.

Cluster: reporting-dc2-cluster-dc2-migrate-to-ra3
Region: us-east-1
NodeType: dc2.8xlarge
NumberOfNodes: 3
Pricing: On-Demand
ClusterStatus: available

```json
{
  "Cluster": {
    "ClusterIdentifier": "reporting-dc2-cluster-dc2-migrate-to-ra3",
    "NodeType": "dc2.8xlarge",
    "NumberOfNodes": 3,
    "ClusterStatus": "available",
    "Region": "us-east-1"
  },
  "Storage": {
    "Type": "local",
    "LocalDiskPerNodeTB": 2.56,
    "UsedTB": 3.4,
    "UtilisationPct": 44
  },
  "CloudWatch": {
    "CPUUtilization": {"avg": 25.0, "max": 40.0},
    "QueryQueueLength": {"avg": 0.0, "max": 5.0},
    "DatabaseConnections": {"avg": 8, "max": 15},
    "ObservationWindowDays": 30
  },
  "Pricing": "On-Demand",
  "ReservedNodes": []
}
```
