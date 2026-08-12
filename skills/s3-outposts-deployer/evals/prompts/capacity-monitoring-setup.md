# Eval: capacity-monitoring-setup

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — capacity alarm at 80% of 1TB, SNS alerting, finite storage noted

## Prompt

Create an S3 bucket on Outpost op-0cap123mon. Bucket name:
monitored-bucket. Endpoint in subnet subnet-cap123 with SG
sg-cap-s3. I need CloudWatch capacity monitoring with an alarm
at 80 percent of 1TB. SNS topic arn:aws:sns:us-east-1:123456789012:outpost-alerts.
Versioning enabled. Account: 123456789012. Region us-east-1.
