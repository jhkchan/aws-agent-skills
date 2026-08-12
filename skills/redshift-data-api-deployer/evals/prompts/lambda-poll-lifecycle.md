# Eval: lambda-poll-lifecycle

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Lambda poll DescribeStatement every 3s, AbortStatement for timeout, UNLOAD to S3 for 24-hour expiry handling

## Prompt

Create a Lambda function integration with the Redshift Data API
for cluster data-warehouse, database production. Use SecretArn
auth with secret arn:aws:secretsmanager:us-east-1:123456789012:secret:dw-creds.
Lambda function etl-runner executes a long-running aggregation
query. Poll DescribeStatement every 3 seconds, max 200 iterations.
If timeout, abort via AbortStatement. Results must be persisted
to S3 before 24-hour expiry. Tags: Environment=production.
