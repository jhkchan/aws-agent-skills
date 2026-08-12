# Eval: std-dev-sensitivity-tuning

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — AWS/ApplicationELB TargetResponseTime, p99, std dev 2 (more sensitive for volatile latency), composite alarm combining anomaly breach AND static threshold

## Prompt

Create a CloudWatch Anomaly Detection model for the
TargetResponseTime metric in namespace AWS/ApplicationELB,
dimension LoadBalancer=app/prod-alb/1234567890, TargetGroup
tg/prod-tg/9876543210, in us-east-1. Stat p99, period 60. The
metric has 90 days of data. Standard deviation multiplier 2
(latency is volatile, want earlier detection). Create a
band-breach alarm. Also create a composite alarm that fires when
BOTH the anomaly alarm AND a static threshold alarm
(latency-high-threshold, p99 > 500ms) are in ALARM. SNS topic
arn:aws:sns:us-east-1:123456789012:critical-alerts.
