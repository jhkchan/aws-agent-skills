# Baseline (no-skill) response: budgets-integration-hard-limit

This file captures what a generic assistant produces WITHOUT the
cost-anomaly-detection-automator skill loaded.

---

You can create a budget using the AWS Budgets console or CLI. Set the
monthly limit to $10,000 and add alerts at 80% and 100%. Since you
already have Cost Anomaly Detection for EC2, you're covered for both
kinds of cost monitoring.

```
aws budgets create-budget --account-id 111111111111 --budget ...
```

The budget will alert you when you're close to the limit. Combined with
the anomaly detection monitor, you should have good cost visibility.

I'm not sure about the exact notification format, but you can configure
email or SNS notifications in the console.
