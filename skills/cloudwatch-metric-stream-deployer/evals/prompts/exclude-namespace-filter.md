# Eval: exclude-namespace-filter

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — ExcludeFilter [AWS/Logs], JSON output, cost implication of streaming all non-excluded namespaces

## Prompt

Create a CloudWatch metric stream named
OpsAllExceptLogs in us-east-1. Output format JSON. Stream all
namespaces EXCEPT AWS/Logs (too noisy, not needed for ops).
Statistics: Average, Sum. Use Firehose delivery stream ops-firehose
(delivers to s3://ops-metrics/data/ with SSE-KMS). IAM role
CWMetricStreamRole exists with cloudwatch.amazonaws.com trust. Tags:
Environment=production, Purpose=ops-monitoring.
