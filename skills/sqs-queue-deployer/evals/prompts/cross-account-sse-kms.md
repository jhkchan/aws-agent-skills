# Eval: cross-account-sse-kms

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — cross-account with SSE-KMS, both policies verified

## Prompt

Deploy a production SQS queue named "shared-events" in us-east-1.
Account 222222222222 needs to send and receive messages from this queue.
Use SSE-KMS encryption with key alias "alias/shared-sqs-key" (key
exists, policy grants the foreign account kms:Decrypt). DLQ
"shared-events-dlq" with maxReceiveCount=5 and 14-day retention. Long
polling. Visibility timeout 30s. Account: 111111111111.
