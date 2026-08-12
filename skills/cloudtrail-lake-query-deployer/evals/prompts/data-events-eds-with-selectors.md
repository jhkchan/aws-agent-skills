# Eval: data-events-eds-with-selectors

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — data events EDS, selectors for PutObject/DeleteObject on specific bucket, 365-day retention

## Prompt

Create a CloudTrail Lake event data store for data events. EDS
name: s3-audit-eds. I only need S3 PutObject and DeleteObject
events on bucket arn:aws:s3:::audit-bucket/. Retention: 365
days. No management events. Account: 123456789012. Region
us-east-1.
