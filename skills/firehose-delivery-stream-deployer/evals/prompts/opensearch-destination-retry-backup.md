# Eval: opensearch-destination-retry-backup

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Direct PUT source, OpenSearch destination with daily index rotation, 5MB buffering for low-latency, FailedDocumentsOnly backup, KMS encryption

## Prompt

Create a Firehose delivery stream named logs-to-opensearch in
us-east-1, account 123456789012. Source: Direct PUT. No Lambda
transformation. Destination: OpenSearch domain
arn:aws:es:us-east-1:123456789012:domain/logs-domain. Index name
logs with daily rotation. Buffering hints 5MB / 60s. Retry
duration 300s. S3 backup mode FailedDocumentsOnly to bucket
firehose-os-backup. KMS encryption with key
arn:aws:kms:us-east-1:123456789012:key/abc123. Tags:
Environment=production, Pipeline=logs.
