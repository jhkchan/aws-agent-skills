# Eval: cross-account-aws-managed-key

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — AWS-managed key blocks cross-account decryption

## Prompt

Deploy a production SNS topic named "shared-events" in us-east-1.
SSE-KMS with AWS-managed key (alias/aws/sns). Subscriber: SQS queue in
account 222222222222
("arn:aws:sqs:us-east-1:222222222222:partner-queue"). Enable delivery
status logging. Account: 111111111111.
