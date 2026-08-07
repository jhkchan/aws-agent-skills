# Eval prompt: anomaly-detection-warmup-blocked

Plan the following CloudWatch alarm conversion (static -> anomaly
detection) and emit the standard VERDICT block (OPERATION, VERDICT,
TARGET, PRE_CHECKS, STEPS, POST_VERIFY, STATE, NOTES).

Operation: anomaly
Alarm name: alb-latency-anomaly-prod
Namespace: AWS/ApplicationELB
Metric: TargetResponseTime
Dimensions: LoadBalancer=app/prod-alb/1234567890
Statistic: Average
Stdev: 2
AlarmActions: arn:aws:sns:us-east-1:111111111111:on-call-critical

```json
{
  "MetricChecks": {
    "get-metric-statistics.AWS/ApplicationELB.TargetResponseTime.app/prod-alb/1234567890": {
      "datapoints": 8,
      "window_minutes": 8,
      "note": "ALB was promoted 8 min ago"
    },
    "describe-anomaly-detectors.AWS/ApplicationELB": []
  },
  "AlarmActionsCheck": {
    "sns.get-topic-attributes.on-call-critical": {"status": "OK"}
  }
}
```
