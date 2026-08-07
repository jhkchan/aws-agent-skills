# Eval prompt: create-cpu-alarm-ready

Plan the following CloudWatch alarm creation and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, STATE, NOTES).

Operation: create
Alarm name: ec2-cpu-high-prod-web-1
Namespace: AWS/EC2
Metric: CPUUtilization
Dimensions: InstanceId=i-0123456789abcdef0
Statistic: Average
Period: 300
EvaluationPeriods: 1
DatapointsToAlarm: 1
Threshold: 80
ComparisonOperator: GreaterThanThreshold
AlarmActions: arn:aws:sns:us-east-1:111111111111:on-call-critical
OKActions: arn:aws:sns:us-east-1:111111111111:on-call-info
TreatMissingData: notBreaching

```json
{
  "MetricChecks": {
    "get-metric-statistics.AWS/EC2.CPUUtilization.InstanceId=i-0123456789abcdef0": {
      "datapoints": 60,
      "Average": 45.2,
      "Maximum": 72.1
    },
    "sns.get-topic-attributes.on-call-critical": {
      "status": "OK",
      "subscriptions": 3
    },
    "sns.get-topic-attributes.on-call-info": {
      "status": "OK",
      "subscriptions": 8
    }
  },
  "ExistingAlarm": null
}
```
