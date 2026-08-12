# Eval prompt: already-optimal-config-optimized

Analyze this App Runner service for cost optimization and emit the
standard optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS, CURRENT_MONTHLY_COST,
PROJECTED_MONTHLY_COST, TRAFFIC_PATTERN, RISK, NOTES).

Service: prod-web-service
Region: us-east-1

```json
{
  "AutoScalingConfiguration": {
    "MinSize": 1,
    "MaxSize": 10,
    "Concurrency": 80
  },
  "InstanceConfiguration": {
    "Cpu": "1 vCPU",
    "Memory": "2 GB"
  },
  "HealthCheckConfiguration": {
    "Interval": 10,
    "Timeout": 3,
    "HealthyThreshold": 2,
    "UnhealthyThreshold": 3
  },
  "Metrics": {
    "RequestCount": "12,000,000/month",
    "AvgInstanceCount": 1.8,
    "PeakInstanceCount": 4,
    "AvgCPUUtilization": "45%",
    "AvgMemoryUtilization": "38%",
    "PeakConcurrentRequestsPerInstance": 72,
    "LatencyP50": "80ms",
    "LatencyP95": "180ms",
    "5xxResponseCount": 3
  },
  "NetworkConfiguration": "no VPC connector (public ingress)",
  "TrafficPattern": "static (consistent 24/7)",
  "CurrentMonthlyCost": "$850"
}
```
