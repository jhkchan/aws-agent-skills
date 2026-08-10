# Eval: http-subscription-no-logging

**Difficulty:** medium
**Branch:** PREREQUISITES_MISSING — HTTP subscriptions require delivery failure logging

## Prompt

Deploy a production SNS topic named "webhook-delivery" in us-east-1.
Subscriber: HTTPS endpoint https://api.partner.com/webhook. SSE-KMS with
AWS-managed key. No delivery status logging configured. Account:
111111111111.
