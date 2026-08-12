# Eval: lambda-sync-realtime

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — synchronous AnalyzeDocument behind Lambda, single-page PNG, S3 PUT trigger, FORMS+TABLES

## Prompt

Build a real-time Textract endpoint for single-page PNG documents
uploaded to s3://realtime-input/ in us-east-1. Use Lambda to
AnalyzeDocument with FORMS and TABLES. The Lambda should be triggered
on S3 PUT. Role arn:aws:iam::123456789012:role/TextractLambdaRole.
Output via API response (no OutputConfig — single page).
