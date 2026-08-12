# Eval: missing-firehose-role

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — role trust policy allows firehose.amazonaws.com but NOT cloudwatch.amazonaws.com; stream would silently deliver nothing

## Prompt

Create a CloudWatch metric stream named
BrokenStream in us-east-1. Output format JSON. Include namespace
AWS/EC2. Use Firehose delivery stream cw-metrics-to-s3 (exists,
delivers to s3://my-cloudwatch-metrics/data/ with SSE-KMS). IAM
role MyFirehoseRole — but this role's trust policy only allows
firehose.amazonaws.com, NOT cloudwatch.amazonaws.com.
