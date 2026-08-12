# Baseline (no-skill) response: add-anomaly-detection-band-review

This file captures what a generic assistant produces WITHOUT the
cloudwatch-dashboards-operator skill loaded.

---

To add an anomaly detection band, update your dashboard with a metric
widget using the ANOMALY_DETECTION_BAND function:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name prod-lambda-overview \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "properties": {
          "metrics": [
            ["AWS/Lambda", "Errors", "FunctionName", "prod-api-handler", {"id": "m1"}],
            [{"expression": "ANOMALY_DETECTION_BAND(m1, 2)", "label": "Expected", "id": "ad1"}]
          ],
          "title": "Lambda Errors Anomaly Detection"
        }
      }
    ]
  }'
```

The anomaly detection band will learn from the historical data and show
expected values. You may need to wait for it to train.
