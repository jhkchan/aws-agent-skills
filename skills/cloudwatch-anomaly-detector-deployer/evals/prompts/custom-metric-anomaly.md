# Eval: custom-metric-anomaly

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — custom namespace MyApp, RequestLatency metric, p99 stat, 1-min period, std dev 2 (more sensitive for volatile latency), upper band breach alarm

## Prompt

Create a CloudWatch Anomaly Detection model for the
RequestLatency custom metric in namespace MyApp, dimension
ServiceName=checkout-service, in us-east-1. Stat p99, period 60
seconds. The custom metric has been reporting for 45 days at
1-minute resolution. Standard deviation multiplier 2 (latency is
volatile, want more sensitivity). Band-breach alarm on upper band
breach with 2 evaluation periods. SNS topic
arn:aws:sns:us-east-1:123456789012:latency-alerts.
