# Eval prompt: http-subscription-pending-confirmation

Diagnose the SNS delivery issue for the following subscription. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: partner webhook `https://api.partner.com/webhook` receives
zero messages since the subscription was created 2 hours ago. The
partner has checked their access logs and sees no POST requests from
AWS SNS after the initial `SubscriptionConfirmation` attempt.

```text
TopicArn: arn:aws:sns:us-east-1:111111111111:orders-events
Protocol: https
Endpoint: https://api.partner.com/webhook
SubscriptionArn: arn:aws:sns:us-east-1:111111111111:orders-events:abc-def
ConfirmationStatus: PendingConfirmation

CloudWatch metrics (last 2 hours):
  - NumberOfNotificationsPublished: 12000 (steady)
  - NumberOfNotificationsDelivered: 0 (for this Endpoint)
  - NumberOfNotificationsFailed: 0 (for this Endpoint)

Other subscriptions on the same topic:
  - Lambda subscription (fn-orders-processor): Confirmed, receiving
    normally (NumberOfNotificationsDelivered matches Published).
```

The Lambda subscription on the same topic is receiving, so the topic
is fine. Identify why this HTTP subscription delivers nothing.
