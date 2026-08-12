# Eval: cross-account-metrics

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — workload account 111111111111 streams to Firehose in observability account 123456789012, cross-account IAM noted

## Prompt

Create a CloudWatch metric stream named
WorkloadA-to-Observability in us-east-1, account 111111111111. This
stream delivers metrics to a Firehose delivery stream central-firehose
in the observability account 123456789012. Output format JSON.
Include namespaces: AWS/EC2, AWS/Lambda, ApplicationMetrics.
Statistics: Average, Sum, SampleCount. The central-firehose delivers
to s3://central-observability/metrics/ in account 123456789012.
IAM role CWMetricStreamCrossAcctRole in account 111111111111 has
cloudwatch.amazonaws.com trust and firehose:PutRecord on the
cross-account Firehose ARN. Tags: SourceAccount=111111111111,
DestinationAccount=123456789012.
