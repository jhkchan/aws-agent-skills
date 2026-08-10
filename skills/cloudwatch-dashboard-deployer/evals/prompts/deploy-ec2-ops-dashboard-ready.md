# Eval prompt: deploy-ec2-ops-dashboard-ready

Plan the following CloudWatch dashboard creation and emit the standard
VERDICT block (DASHBOARD, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, WIDGETS, SHARING, NOTES).

Operation: create
Dashboard name: prod-ec2-ops
Region: us-east-1
Account: 111111111111
Widgets:
  - type: metric
    title: CPU Utilization
    namespace: AWS/EC2
    metric: CPUUtilization
    dimensions: InstanceId=${INSTANCE_ID}
    statistic: Average
    period: 300
    position: x=0, y=0, w=12, h=6
  - type: metric
    title: Memory Utilization
    namespace: CWAgent
    metric: mem_used_percent
    dimensions: InstanceId=${INSTANCE_ID}
    statistic: Average
    period: 300
    position: x=12, y=0, w=12, h=6
  - type: metric
    title: Network Traffic
    namespace: AWS/EC2
    metrics: NetworkIn, NetworkOut
    dimensions: InstanceId=${INSTANCE_ID}
    statistic: Sum
    period: 300
    position: x=0, y=6, w=24, h=3
Dashboard variable: INSTANCE_ID

```json
{
  "MetricChecks": {
    "get-metric-statistics.AWS/EC2.CPUUtilization.InstanceId=i-0123456789abcdef0": {
      "datapoints": 60,
      "Average": 45.2,
      "Maximum": 72.1
    },
    "get-metric-statistics.CWAgent.mem_used_percent.InstanceId=i-0123456789abcdef0": {
      "datapoints": 60,
      "Average": 62.4
    },
    "get-metric-statistics.AWS/EC2.NetworkIn.InstanceId=i-0123456789abcdef0": {
      "datapoints": 60,
      "Sum": 1048576
    }
  },
  "ExistingDashboard": null
}
```
