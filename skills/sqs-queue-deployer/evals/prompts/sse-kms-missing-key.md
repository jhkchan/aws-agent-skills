# Eval: sse-kms-missing-key

**Difficulty:** medium
**Branch:** PREREQUISITES_MISSING — KMS key does not exist

## Prompt

Deploy a production SQS queue named "secure-events" in us-east-1. Use
SSE-KMS encryption with key alias "alias/sqs-secure-key". The key alias
does not exist yet. Standard queue with DLQ "secure-events-dlq",
maxReceiveCount=5. Long polling. Visibility timeout 60s. Account:
111111111111.
