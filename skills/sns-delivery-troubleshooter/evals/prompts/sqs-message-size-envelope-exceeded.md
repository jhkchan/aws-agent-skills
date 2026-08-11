# Eval prompt: sqs-message-size-envelope-exceeded

Diagnose the SNS delivery issue for the following subscription. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: SQS subscription queue `order-queue` is missing ~20% of
expected messages. The missing messages are the large ones (~254 KB
body). Smaller messages (~50 KB) deliver fine.
`NumberOfNotificationsFailed` > 0 for this subscription.

```text
TopicArn: arn:aws:sns:us-east-1:111111111111:batch-events
SubscriptionArn: arn:aws:sns:us-east-1:111111111111:batch-events:ghi
Protocol: sqs
Endpoint: arn:aws:sqs:us-east-1:111111111111:order-queue
ConfirmationStatus: Confirmed
FilterPolicy: (none)
RawMessageDelivery: false

SQS context:
  - Queue order-queue:
    - MaximumMessageSize: 262144 (256 KB, the default)
    - ApproximateNumberOfMessagesVisible: 0 (messages not landing)
    - Queue policy grants sns.amazonaws.com sqs:SendMessage

SNS message context:
  - 80% of messages: body ~50 KB (deliver fine)
  - 20% of messages: body ~254 KB (fail — envelope adds ~4 KB,
    total ~258 KB > 256 KB SQS cap)

CloudWatch metrics (last hour):
  - NumberOfNotificationsPublished: 10000
  - NumberOfNotificationsDelivered: 8000 (the 50 KB messages)
  - NumberOfNotificationsFailed: 2000 (the 254 KB messages)
  - PublishSize p99: 260000 bytes
```

The queue policy is correct and the subscription is Confirmed. Only
the large messages fail. Identify the root cause.
