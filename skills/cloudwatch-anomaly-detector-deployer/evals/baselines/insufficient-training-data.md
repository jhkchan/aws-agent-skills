# Baseline (no-skill) — insufficient-training-data

> This is the response a model produces **without** the skill
> definition. It creates the anomaly detector without flagging the
> insufficient training data (only 3 days, ~800 points — the ML model
> needs ~2 weeks for a reliable baseline including weekly patterns).
> Does not emit a PREREQUISITES_MISSING verdict. Generated for
> with-skill-vs-baseline comparison.

---

Sure, here's the anomaly detector:

```bash
aws cloudwatch put-metric-anomaly-detector \
  --namespace "AWS/EC2" \
  --metric-name "CPUUtilization" \
  --dimensions Name=InstanceId,Value=i-newinstance999 \
  --stat "Average" \
  --period 300
```

Then create the alarm and SNS notification.
