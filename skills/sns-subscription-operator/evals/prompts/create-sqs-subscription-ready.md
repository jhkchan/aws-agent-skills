# Eval prompt: create-sqs-subscription-ready

Plan the following SNS subscription creation and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: create
TopicArn: arn:aws:sns:us-east-1:111111111111:order-events
Protocol: sqs
Endpoint: arn:aws:sqs:us-east-1:111111111111:order-processing-queue

```json
{
  "TopicAttributes": {
    "Owner": "111111111111",
    "PolicyAllowsSubscribe": true,
    "PolicySubscriberAccount": "arn:aws:iam::111111111111:root"
  },
  "QueueAttributes": {
    "QueueArn": "arn:aws:sqs:us-east-1:111111111111:order-processing-queue",
    "PolicyAllowsSnsSendMessage": true,
    "PolicySourceArn": "arn:aws:sns:us-east-1:111111111111:order-events"
  },
  "DesiredFilterPolicy": {"event_type": ["order_created", "order_updated"]},
  "DesiredRawMessageDelivery": true,
  "CallingIdentity": "arn:aws:iam::111111111111:role/AppDeployRole",
  "CallerOwnsTopicAndQueue": true
}
```
