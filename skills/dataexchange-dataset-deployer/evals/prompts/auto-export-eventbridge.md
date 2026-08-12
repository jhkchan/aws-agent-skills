# Eval: auto-export-eventbridge

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — EventBridge rule triggers Lambda on Data Update event, Lambda calls StartJob for EXPORT_ASSETS_TO_S3, auto-export flow noted

## Prompt

Set up auto-export for Data Exchange data set ds-auto123.
Subscription is ACTIVE. When a new revision is published, an
EventBridge rule should trigger Lambda function dx-auto-export
to start an export job copying S3_SNAPSHOT assets to bucket
my-auto-bucket in us-east-1. IAM role for Lambda has
dataexchange:StartJob and s3:PutObject permissions.
Tags: Environment=production, Pipeline=auto-export.
