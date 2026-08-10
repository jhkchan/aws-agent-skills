# Baseline (no-skill) response: deploy-slo-dashboard-ready

This file captures what a generic assistant produces WITHOUT the
cloudwatch-dashboard-deployer skill loaded.

---

To create an SLO dashboard using Application Signals, use:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name prod-slo-burn-rate \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "x": 0, "y": 0, "width": 24, "height": 6,
        "properties": {
          "metrics": [
            ["AWS/ApplicationSignals", "ConsumedRAT", "ServiceName", "checkout-service", "SLO", "checkout-availability-slo"]
          ],
          "period": 300,
          "title": "SLO Burn Rate"
        }
      }
    ]
  }'
```

You need Application Signals enabled for this to work.
