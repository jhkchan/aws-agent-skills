# Eval prompt: http-endpoint-4xx-rate-limited

Diagnose the SNS delivery issue for the following subscription. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: SNS topic `orders-events` publishes 200 messages/sec to
`https://api.partner.com/webhook`. The partner reports ~5% of messages
are never received. CloudWatch shows `NumberOfNotificationsFailed` at
~10/sec consistently.

```text
TopicArn: arn:aws:sns:us-east-1:111111111111:orders-events
Protocol: https
Endpoint: https://api.partner.com/webhook
ConfirmationStatus: Confirmed
DeliveryPolicy: default (4 immediate retries + 3 delayed)

CloudWatch metrics (last hour):
  - NumberOfNotificationsPublished: 720000 (200/sec)
  - NumberOfNotificationsDelivered: 684000 (95%)
  - NumberOfNotificationsFailed: 36000 (5%)

Endpoint access logs (partner-side):
  - During traffic peaks, the endpoint returns HTTP 429 (Too Many
    Requests) for ~5% of inbound POST requests.
  - The endpoint's rate limiter is set to 190 req/sec; SNS is
    publishing at 200 req/sec.
```

The subscription is Confirmed. SNS reports delivery failures at the
same rate the endpoint returns 429. Identify the root cause.
