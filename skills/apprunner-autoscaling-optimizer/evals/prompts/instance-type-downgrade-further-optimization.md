# Eval prompt: instance-type-downgrade-further-optimization

Analyze this App Runner service for cost optimization and emit the
standard optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS, CURRENT_MONTHLY_COST,
PROJECTED_MONTHLY_COST, TRAFFIC_PATTERN, RISK, NOTES).

Service: prod-worker-service
Region: us-east-1

```json
{
  "AutoScalingConfiguration": {
    "MinSize": 1,
    "MaxSize": 8,
    "Concurrency": 50
  },
  "InstanceConfiguration": {
    "Cpu": "2 vCPU",
    "Memory": "4 GB"
  },
  "Metrics": {
    "RequestCount": "2,000,000/month",
    "AvgInstanceCount": 1.2,
    "PeakInstanceCount": 3,
    "AvgCPUUtilization": "15%",
    "AvgMemoryUtilization": "22%",
    "PeakConcurrentRequestsPerInstance": 28,
    "LatencyP95": "150ms",
    "5xxResponseCount": 0
  },
  "TrafficPattern": "bursty (event-driven batch processing)",
  "CurrentMonthlyCost": "$950"
}
```
