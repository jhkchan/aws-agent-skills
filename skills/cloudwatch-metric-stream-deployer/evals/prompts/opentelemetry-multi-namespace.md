# Eval: opentelemetry-multi-namespace

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — opentelemetry output, IncludeFilter [AWS/EC2, AWS/Lambda, AWS/RDS, ApplicationMetrics], percentile statistics, Datadog integration

## Prompt

Create a CloudWatch metric stream named
OtelExportStream in us-east-1. Output format OpenTelemetry. This
stream feeds our Datadog integration. Include namespaces: AWS/EC2,
AWS/Lambda, AWS/RDS, and ApplicationMetrics. Statistics: Average,
p99, Sum. Use Firehose delivery stream otel-firehose (delivers to
s3://otel-metrics/data/ with SSE-KMS). IAM role
CWMetricStreamRole exists with cloudwatch.amazonaws.com trust.
Tags: Environment=production, Consumer=datadog.
