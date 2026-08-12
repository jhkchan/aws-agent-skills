# Eval prompt: add-anomaly-detection-band-review

Plan the following CloudWatch dashboard update to add an anomaly
detection band and emit the standard VERDICT block (OPERATION, VERDICT,
TARGET, PRE_CHECKS, STEPS, POST_VERIFY, NOTES).

Operation: add-anomaly-detection
Dashboard: prod-lambda-overview (existing, 6 widgets)
Metric: AWS/Lambda Errors
Function: prod-api-handler
stdev: 2

```json
{
  "NamespaceCheck": {
    "Namespace": "AWS/Lambda",
    "MetricsFound": 128
  },
  "CurrentDashboard": {
    "DashboardName": "prod-lambda-overview",
    "WidgetCount": 6,
    "BodySize": "8 KB"
  },
  "AnomalyDetectionCheck": {
    "Metric": "Errors",
    "FunctionName": "prod-api-handler",
    "TrainingDataDays": 14,
    "Sufficient": true
  }
}
```
