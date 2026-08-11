# Eval: sse-config-insight-suppress-or-implement

**Difficulty:** medium
**Branch:** ROOT_CAUSE_FOUND — bucket prod-data-lake lacks SSE-KMS; CONFIGURATION analysis category; enable SSE-KMS with customer CMK

## Prompt

Diagnose this DevOps Guru insight:
Insight ID: v-7890qrst in us-east-1
describe-insight: PROACTIVE, MEDIUM, OPEN, Name="S3 bucket
prod-data-lake lacks server-side encryption", StartTime=
2026-08-09T00:00Z. AnalysisCategory=CONFIGURATION.
list-anomalies-for-insight: Configuration check detected
SSE-S3 not enabled, SSE-KMS not enabled on bucket
prod-data-lake (account 111111111111).
list-recommendations: CONFIGURATION — "Enable server-side
encryption on the S3 bucket using a customer-managed KMS key
for compliance workloads."
KMS alias/prod-s3-cmk exists and is enabled in us-east-1.
Region: us-east-1.
