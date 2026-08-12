# Eval prompt: vpc-egress-nat-cost-further-optimization

Analyze this App Runner service for cost optimization and emit the
standard optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS, CURRENT_MONTHLY_COST,
PROJECTED_MONTHLY_COST, TRAFFIC_PATTERN, RISK, NOTES).

Service: prod-data-service
Region: us-east-1

```json
{
  "AutoScalingConfiguration": {
    "MinSize": 2,
    "MaxSize": 15,
    "Concurrency": 80
  },
  "InstanceConfiguration": {
    "Cpu": "2 vCPU",
    "Memory": "4 GB"
  },
  "NetworkConfiguration": {
    "VpcConnector": true,
    "EgressConfiguration": "NAT gateway"
  },
  "Metrics": {
    "RequestCount": "5,000,000/month",
    "AvgInstanceCount": 3.1,
    "AvgCPUUtilization": "42%",
    "AvgMemoryUtilization": "35%",
    "DataTransferredToS3": "800 GB/month",
    "DataTransferredToDynamoDB": "200 GB/month",
    "DataTransferredToRDSPrivate": "50 GB/month"
  },
  "CostBreakdown": {
    "AppRunnerCompute": "$950/month",
    "NATGatewayProcessing": "$380/month",
    "NATGatewayHourly": "$32/month",
    "TotalNATCost": "$412/month"
  },
  "CurrentMonthlyCost": "$1,362/month",
  "TrafficPattern": "dynamic"
}
```
