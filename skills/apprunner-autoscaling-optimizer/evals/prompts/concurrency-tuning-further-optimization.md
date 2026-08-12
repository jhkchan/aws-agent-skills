# Eval prompt: concurrency-tuning-further-optimization

Analyze this App Runner service for cost optimization and emit the
standard optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS, CURRENT_MONTHLY_COST,
PROJECTED_MONTHLY_COST, TRAFFIC_PATTERN, RISK, NOTES).

Service: prod-api-service
Region: us-east-1

```json
{
  "AutoScalingConfiguration": {
    "MinSize": 1,
    "MaxSize": 25,
    "Concurrency": 100
  },
  "InstanceConfiguration": {
    "Cpu": "1 vCPU",
    "Memory": "2 GB"
  },
  "Metrics": {
    "RequestCount": "8,000,000/month",
    "AvgInstanceCount": 2.3,
    "PeakInstanceCount": 6,
    "AvgCPUUtilization": "35%",
    "AvgMemoryUtilization": "30%",
    "PeakConcurrentRequestsPerInstance": 42,
    "LatencyP50": "120ms",
    "LatencyP95": "280ms",
    "LatencyP99": "450ms",
    "5xxResponseCount": 12
  },
  "TrafficPattern": "dynamic (3x peak during business hours)",
  "CurrentMonthlyCost": "$1,200"
}
```
