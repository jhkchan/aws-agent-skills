# Eval: cross-account-fifo-delivery

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — cross-account delivery, access policy grants sqs:SendMessage to producer account, SSE-KMS with cross-account key policy

## Prompt

Create an SQS FIFO queue named cross-account-orders.fifo in
us-east-1, account 123456789012. Cross-account delivery from
producer account 999999999999. Access policy grants
sqs:SendMessage to the producer role. Content-based
deduplication enabled. SSE-KMS encryption with key policy
allowing producer account. Visibility timeout 90 seconds.
Tags: Environment=production, Topology=cross-account.
