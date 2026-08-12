# Eval prompt: pause-non-prod-savings-further-optimization

Analyze this App Runner service for cost optimization and emit the
standard optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS, CURRENT_MONTHLY_COST,
PROJECTED_MONTHLY_COST, TRAFFIC_PATTERN, RISK, NOTES).

Service: dev-staging-service
Region: us-east-1

```json
{
  "AutoScalingConfiguration": {
    "MinSize": 1,
    "MaxSize": 5,
    "Concurrency": 50
  },
  "InstanceConfiguration": {
    "Cpu": "1 vCPU",
    "Memory": "2 GB"
  },
  "Metrics": {
    "RequestCount": "50,000/month",
    "AvgInstanceCount": 1.0,
    "TrafficHours": "9am-6pm weekdays only",
    "AfterHoursAndWeekendTraffic": 0
  },
  "Environment": "dev/staging (non-production)",
  "CurrentMonthlyCost": "$720"
}
```
