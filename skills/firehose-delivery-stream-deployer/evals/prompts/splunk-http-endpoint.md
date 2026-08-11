# Eval: splunk-http-endpoint

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — Direct PUT source, HTTP endpoint destination (Splunk HEC), 5MB/60s buffering for SIEM, S3 backup

## Prompt

Create a Firehose delivery stream named security-to-splunk in
us-east-1, account 123456789012. Source: Direct PUT. Destination:
HTTP endpoint at https://splunk.example.com:8088/services/collector
with access key. Buffering hints 5MB / 60s for low-latency SIEM.
Retry duration 300s. S3 backup to bucket firehose-splunk-backup.
Tags: Environment=production, Pipeline=siem.
