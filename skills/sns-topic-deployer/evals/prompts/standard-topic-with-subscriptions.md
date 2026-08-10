# Eval: standard-topic-with-subscriptions

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — full checklist with subscriptions, filter, logging

## Prompt

Deploy a production SNS topic named "order-events" in us-east-1. It
receives messages from S3 bucket "order-uploads" via S3 Event
Notification. Two subscribers: SQS queue "order-queue" (filter on
event_type=["order_created"]) and Lambda function "order-handler".
Enable SSE-KMS with AWS-managed key. Enable SQS delivery status
logging. Account: 111111111111.
