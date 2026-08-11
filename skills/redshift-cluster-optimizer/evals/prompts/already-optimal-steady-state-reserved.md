# Eval prompt: already-optimal-steady-state-reserved

Optimise the following Amazon Redshift cluster and emit the standard
optimisation block.

Cluster: prod-warehouse-already-optimal-steady-state-reserved
Region: us-east-1
NodeType: ra3.16xlarge
NumberOfNodes: 2
Pricing: 3-yr Reserved Node (No Upfront)
ClusterStatus: available

```json
{
  "Cluster": {
    "ClusterIdentifier": "prod-warehouse-already-optimal-steady-state-reserved",
    "NodeType": "ra3.16xlarge",
    "NumberOfNodes": 2,
    "ClusterStatus": "available",
    "Region": "us-east-1"
  },
  "CloudWatch": {
    "CPUUtilization": {"avg": 55.0, "max": 68.0},
    "QueryQueueLength": {"avg": 3.0, "max": 12.0},
    "DatabaseConnections": {"avg": 120, "max": 200},
    "ObservationWindowDays": 30
  },
  "WLM": {
    "Mode": "auto",
    "ShortQueryAcceleration": true,
    "Queues": [
      {"Name": "BI", "Concurrency": 8, "Priority": "High"},
      {"Name": "ETL", "Concurrency": 15, "Priority": "Medium"},
      {"Name": "ad-hoc", "Concurrency": 3, "Priority": "Low"}
    ]
  },
  "ConcurrencyScaling": {"Enabled": true, "AvgHoursPerDay": 0.5},
  "Storage": {
    "Type": "managed",
    "UsedTB": 45,
    "Compression": "AZ64 on all columns",
    "LastVacuum": "2 days ago",
    "LastAnalyze": "current"
  },
  "Pricing": "3-yr Reserved Node (No Upfront)",
  "ReservedNodes": [
    {"NodeType": "ra3.16xlarge", "NodeCount": 2, "Duration": "3yr", "State": "active"}
  ],
  "MaterializedViews": 8
}
```
