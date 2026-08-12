# Eval prompt: metrics-insights-dashboard-completed

Plan the following CloudWatch dashboard creation with a Metrics Insights
query and emit the standard VERDICT block (OPERATION, VERDICT, TARGET,
PRE_CHECKS, STEPS, POST_VERIFY, NOTES).

Operation: create-dashboard
Dashboard name: top10-ec2-by-cpu
Service: EC2
Widgets: 3 (Metrics Insights top-10, status checks, network)

```json
{
  "NamespaceCheck": {
    "Namespace": "AWS/EC2",
    "MetricsFound": 256
  },
  "DashboardExistence": {
    "DashboardName": "top10-ec2-by-cpu",
    "AlreadyExists": false
  },
  "MetricsInsightsQuery": {
    "Query": "SELECT avg(CPUUtilization) FROM AWS/EC2 WHERE AutoScalingGroupName LIKE 'prod-%' GROUP BY InstanceId ORDER BY avg() DESC LIMIT 10",
    "SyntaxValid": true
  },
  "BodySize": "4 KB"
}
```
