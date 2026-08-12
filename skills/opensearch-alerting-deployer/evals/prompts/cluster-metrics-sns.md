# Eval: cluster-metrics-sns

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — cluster-metrics monitor, JVM heap > 85%, severity 1, SNS destination, notification plugin configured, every 1 minute

## Prompt

Create an OpenSearch cluster metrics monitor named
jvm-heap-monitor on cluster
https://search-prod.example.com. Monitor JVM heap usage and
trigger when it exceeds 85%, severity 1. Action: notify SNS
destination ops-alerts-sns (topic
arn:aws:sns:us-east-1:123456789012:alert-topic). The
notification plugin (notification.yaml) is configured with
role arn:aws:iam::123456789012:role/os-alerting-sns. Schedule
every 1 minute. Tags: Environment=production, Service=search.
