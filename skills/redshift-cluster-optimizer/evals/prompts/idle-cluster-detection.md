# Eval prompt: idle-cluster-detection

Optimise the following Amazon Redshift cluster and emit the standard
optimisation block.

Cluster: dev-sandbox-cluster-idle-cluster-detection
Region: us-east-1
NodeType: ra3.4xlarge
NumberOfNodes: 2
Pricing: On-Demand
ClusterStatus: available

```json
{
  "Cluster": {
    "ClusterIdentifier": "dev-sandbox-cluster-idle-cluster-detection",
    "NodeType": "ra3.4xlarge",
    "NumberOfNodes": 2,
    "ClusterStatus": "available",
    "Region": "us-east-1"
  },
  "CloudWatch": {
    "CPUUtilization": {"avg": 0.2, "max": 1.1},
    "QueryQueueLength": {"avg": 0, "max": 0},
    "DatabaseConnections": {"avg": 0, "max": 0, "ConsecutiveZeroDays": 22},
    "ObservationWindowDays": 30
  },
  "LastQuery": "22 days ago (ad-hoc SELECT by data scientist)",
  "DataSharing": {
    "Role": "consumer",
    "Producer": "prod-warehouse-cluster"
  },
  "Pricing": "On-Demand"
}
```
