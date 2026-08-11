# Eval prompt: oversized-ra3-rightsize-reserved-node

Optimise the following Amazon Redshift cluster and emit the standard
optimisation block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

Cluster: analytics-prod-cluster-oversized-ra3-rightsize-reserved-node
Region: us-east-1
NodeType: ra3.4xlarge
NumberOfNodes: 4
Pricing: On-Demand (no Reserved Nodes)
ClusterStatus: available

```json
{
  "Cluster": {
    "ClusterIdentifier": "analytics-prod-cluster-oversized-ra3-rightsize-reserved-node",
    "NodeType": "ra3.4xlarge",
    "NumberOfNodes": 4,
    "ClusterStatus": "available",
    "ClusterVersion": "1.0",
    "Region": "us-east-1"
  },
  "CloudWatch": {
    "CPUUtilization": {"avg": 15.0, "max": 30.0},
    "QueryQueueLength": {"avg": 0.0, "max": 2.0},
    "DatabaseConnections": {"avg": 20, "max": 50},
    "ObservationWindowDays": 30
  },
  "WLM": {
    "Mode": "auto",
    "ShortQueryAcceleration": true,
    "Queues": [
      {"Name": "BI", "Concurrency": 5, "Priority": "High"},
      {"Name": "ETL", "Concurrency": 10, "Priority": "Low"}
    ]
  },
  "ConcurrencyScaling": "off",
  "Storage": {
    "Type": "managed",
    "UsedTB": 12
  },
  "Pricing": "On-Demand",
  "ReservedNodes": []
}
```
