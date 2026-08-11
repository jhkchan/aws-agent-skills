# Eval prompt: serverless-base-rpu-too-high

Optimise the following Redshift Serverless workgroup and emit the standard
optimisation block.

Workgroup: analytics-serverless-serverless-base-rpu-too-high
Region: us-east-1
Type: Redshift Serverless

```json
{
  "Workgroup": {
    "WorkgroupName": "analytics-serverless-serverless-base-rpu-too-high",
    "WorkgroupType": "serverless",
    "BaseCapacityRPU": 32,
    "MaxRPU": 128,
    "Region": "us-east-1"
  },
  "CloudWatch": {
    "RPUUsage": {"avg": 8, "max": 20, "p95": 16},
    "QueryCount": {"avgPerDay": 5000},
    "ActiveHours": "09:00-17:00",
    "ObservationWindowDays": 30
  }
}
```
