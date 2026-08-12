# Eval prompt: s3-archive-pipeline

Design an S3 Firehose archival pipeline for compliance logs that need
retention beyond the CloudWatch hot query window. Emit the standard
RETENTION block (POLICY, TRIGGER, ARCHIVAL, VERDICT, TEMPLATE).

Design reference: s3-archive-pipeline
Account: 111111111111
Region: us-east-1

Compliance log groups: /aws/lambda/audit-logger (5 GB/day),
/aws/cloudtrail/management-events (20 GB/day)
Required: 7-year retention for compliance.
Hot query window: 90 days in CloudWatch.
Cold storage: S3 with Glacier lifecycle after 90d.
Firehose buffer: 5MB / 300s, GZIP compression.
S3 bucket: com-company-log-archive-compliance

Emit the standard RETENTION block. Include the Firehose delivery
stream config, subscription filter wiring, S3 lifecycle policy, and
the cost comparison between CloudWatch-only and CloudWatch+S3.
