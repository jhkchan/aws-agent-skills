# Baseline (no-skill) response: rum-custom-events-and-custom-metrics

This file captures what a generic assistant produces WITHOUT the
cloudwatch-rum-deployer skill loaded.

---

To record a custom event in RUM, you can call:

```javascript
cwr('recordEvent', {
  type: 'checkout-complete',
  data: { cartValue: 142.50, itemCount: 3 }
});
```

For a CloudWatch custom metric, you would need to send the metric
yourself via `put-metric-data`:

```
aws cloudwatch put-metric-data --namespace AWS/RUM \
  --metric-name CartValueTotal --value 142.50
```

That should let you build alarms on the cart value.
