# Baseline (no-skill) — builtin-cpu-anomaly-alarm

> This is the response a model produces **without** the skill
> definition. It creates the anomaly detector but misses the
> historical data depth check, the ANOMALY_DETECTION_BAND metric math
> function for the alarm, the evaluation-periods tuning, the std dev
> multiplier explanation, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Here's how to set up anomaly detection for your CPU metric:

```bash
aws cloudwatch put-metric-anomaly-detector \
  --namespace "AWS/EC2" \
  --metric-name "CPUUtilization" \
  --dimensions Name=InstanceId,Value=i-abc1234567890 \
  --stat "Average" \
  --period 300
```

Then create an alarm:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "cpu-anomaly" \
  --namespace "AWS/EC2" \
  --metric-name "CPUUtilization" \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```
