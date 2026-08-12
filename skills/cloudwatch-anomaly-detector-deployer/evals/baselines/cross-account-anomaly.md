# Baseline (no-skill) — cross-account-anomaly

> This is the response a model produces **without** the skill
> definition. It creates the detector but misses the cross-account
> sharing requirement (resource policy on the source account, data
> source link in the monitoring account), the monitoring-vs-source
> account distinction, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create the anomaly detector:

```bash
aws cloudwatch put-metric-anomaly-detector \
  --namespace "AWS/RDS" \
  --metric-name "DatabaseConnections" \
  --dimensions Name=DBInstanceIdentifier,Value=prod-db-001 \
  --stat "Average" \
  --period 300
```

Then set up the alarm with SNS.
