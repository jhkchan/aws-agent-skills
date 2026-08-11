# Eval prompt: filter-policy-silent-drop

Diagnose the SNS delivery issue for the following subscription. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: consumer reports ~40% of expected messages never arrive. No
errors in SNS delivery metrics. The publisher sends both
`order.created` and `order.updated` events to the same topic.

```text
TopicArn: arn:aws:sns:us-east-1:111111111111:order-events
SubscriptionArn: arn:aws:sns:us-east-1:111111111111:order-events:abc
Protocol: sqs
Endpoint: arn:aws:sqs:us-east-1:111111111111:order-queue
ConfirmationStatus: Confirmed
FilterPolicy: {"event": ["order.created"]}
RawMessageDelivery: false

Publisher message attributes:
  - 60% of messages: event=order.created
  - 40% of messages: event=order.updated

CloudWatch metrics (last hour):
  - NumberOfNotificationsPublished: 10000 (for the topic)
  - NumberOfNotificationsDelivered: 6000 (for this subscription)
  - NumberOfNotificationsFailed: 0

Test: publish with event=order.updated; Delivered does NOT increment.
Publish with event=order.created; it does.
```

The queue is Confirmed and the queue policy is correct. Identify why
~40% of messages silently vanish.
