# Eval prompt: create-rds-dashboard-completed

Plan the following CloudWatch dashboard creation and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: create-dashboard
Dashboard name: prod-rds-overview
Service: RDS
Widgets: 8 (CPU, memory, connections, storage, query throughput,
replica lag, alarm, error logs)

```json
{
  "NamespaceCheck": {
    "Namespace": "AWS/RDS",
    "MetricsFound": 42,
    "SampleMetrics": ["CPUUtilization", "DatabaseConnections", "FreeableMemory", "FreeStorageSpace", "ReadIOPS", "WriteIOPS"]
  },
  "DimensionCheck": {
    "DBInstanceIdentifier": "prod-orders-db",
    "Exists": true,
    "Status": "available"
  },
  "AlarmCheck": {
    "AlarmName": "rds-cpu-high",
    "Exists": true,
    "Threshold": "80% for 5 min"
  },
  "DashboardExistence": {
    "DashboardName": "prod-rds-overview",
    "AlreadyExists": false
  },
  "BodySize": "12 KB"
}
```
