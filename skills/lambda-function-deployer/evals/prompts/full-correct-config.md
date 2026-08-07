# Eval: full-correct-config

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — all checklist items verified, layers + Powertools

## Prompt

Deploy a production Lambda function named "report-generator-prod"
in us-east-1. Runtime: python3.12. Handler: generate.handler. The
function reads from DynamoDB (table: reports-table) and writes PDF
reports to S3 (bucket: reports-output-prod). Use the
AWSLambdaBasicExecutionRole managed policy plus scoped DynamoDB
read + S3 write permissions. KMS key alias/lambda-env-key for env
var encryption. Environment: REPORTS_TABLE=reports-table,
OUTPUT_BUCKET=reports-output-prod. Memory: 1024 MB, Timeout: 60s.
Layers: Powertools for Python v3 (python3.12-x86_64).
On-failure destination: report-gen-dlq (SQS). X-Ray active.
CloudWatch retention: 30 days. Tags: Environment=production,
Workload=report-generator. Account: 123456789012.
