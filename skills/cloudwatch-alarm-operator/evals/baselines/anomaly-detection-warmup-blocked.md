# Baseline (no-skill) response: anomaly-detection-warmup-blocked

This file captures what a generic assistant produces WITHOUT the
cloudwatch-alarm-operator skill loaded.

---

To convert your latency alarm to anomaly detection:

```bash
aws cloudwatch put-anomaly-detector \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=app/prod-alb/1234567890

aws cloudwatch put-metric-alarm \
  --alarm-name alb-latency-anomaly-prod \
  --namespace AWS/ApplicationELB \
  --metrics "m1,TargetResponseTime,Average,60,LoadBalancer,app/prod-alb/1234567890" "ad1,ANOMALY_DETECTION_BAND(m1,2),60" \
  --comparison-operator GreaterThanUpperThreshold \
  --evaluation-periods 3 \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical
```

This should start detecting anomalies on your ALB's TargetResponseTime
metric.
