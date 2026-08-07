# Eval prompt: diagnose-insufficient-data-dimensions-wrong

Diagnose the following CloudWatch alarm that has been stuck in
INSUFFICIENT_DATA for 6 days. Emit the standard VERDICT block.

Operation: diagnose
Alarm name: api-error-rate-prod

```json
{
  "AlarmConfig": {
    "AlarmName": "api-error-rate-prod",
    "StateValue": "INSUFFICIENT_DATA",
    "StateUpdatedTimestamp": "2026-08-01T14:30:00Z",
    "Namespace": "AWS/ApplicationELB",
    "MetricName": "HTTPCode_ELB_5XX_Count",
    "Dimensions": [{"Name": "LoadBalancer", "Value": "app/prod-alb/abc-def-OLD"}],
    "Statistic": "Sum",
    "Period": 60,
    "EvaluationPeriods": 5,
    "DatapointsToAlarm": 3,
    "Threshold": 10,
    "ComparisonOperator": "GreaterThanThreshold",
    "TreatMissingData": "missing",
    "AlarmActions": ["arn:aws:sns:us-east-1:111111111111:on-call-critical"],
    "ActionsEnabled": true
  },
  "MetricChecks": {
    "get-metric-statistics.AWS/ApplicationELB.HTTPCode_ELB_5XX_Count.app/prod-alb/abc-def-OLD": {
      "datapoints": 0
    },
    "elbv2.describe-load-balancers.prod-alb": {
      "DNSName": "prod-alb-1234567890.us-east-1.elb.amazonaws.com",
      "currentArn": "app/prod-alb/1234567890"
    }
  },
  "AlarmHistory": [
    {
      "timestamp": "2026-08-01T14:30:00Z",
      "transition": "OK -> INSUFFICIENT_DATA",
      "summary": "metric stopped reporting"
    }
  ]
}
```
