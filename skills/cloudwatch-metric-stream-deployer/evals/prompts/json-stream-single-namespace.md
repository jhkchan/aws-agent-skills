# Eval: json-stream-single-namespace

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — JSON output, IncludeFilter [AWS/EC2], specific statistics (Average, Sum, SampleCount), Firehose to S3 with SSE-KMS

## Prompt

Create a CloudWatch metric stream named
Ec2MetricStream in us-east-1. Output format JSON. Stream only the
AWS/EC2 namespace. Statistics: Average, Sum, SampleCount. Use the
existing Firehose delivery stream cw-metrics-to-s3 (delivers to
s3://my-cloudwatch-metrics/cloudwatch-metrics/ with SSE-KMS key
arn:aws:kms:us-east-1:123456789012:key/abc123). IAM role
CWMetricStreamRole already exists with trust policy for
cloudwatch.amazonaws.com and firehose:PutRecord permission. Tags:
Environment=production.
