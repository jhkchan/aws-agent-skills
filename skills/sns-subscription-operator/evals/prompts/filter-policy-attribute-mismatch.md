# Eval prompt: filter-policy-attribute-mismatch

Diagnose the following SNS subscription and emit the standard VERDICT
block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS, POST_VERIFY,
NOTES).

Operation: diagnose
TopicArn: arn:aws:sns:us-east-1:111111111111:order-events
SubscriptionArn: arn:aws:sns:us-east-1:111111111111:order-events:1234-abcd
Protocol: sqs
Endpoint: arn:aws:sqs:us-east-1:111111111111:order-processing-queue

```json
{
  "SubscriptionAttributes": {
    "PendingConfirmation": false,
    "FilterPolicy": {"event_type": ["order_created", "order_updated"]},
    "FilterPolicyScope": "MessageAttributes",
    "RawMessageDelivery": true
  },
  "PublisherMessageAttributes": {
    "type": "order_created",
    "order_id": "ORD-12345"
  },
  "QueueAttributes": {
    "PolicyAllowsSnsSendMessage": true,
    "PolicySourceArn": "arn:aws:sns:us-east-1:111111111111:order-events"
  },
  "QueueDepth": 0,
  "PublishesInLastHour": 523,
  "MessagesReceivedInLastHour": 0
}
```
