# SNS Subscription Protocols & Attributes Reference

Load this reference when planning subscription creation or attribute
changes. Contains the protocol-to-endpoint mapping, subscription
attribute catalog, and per-protocol capability matrix.

## Protocol-to-endpoint format mapping

| Protocol | Endpoint format | Example | Auto-confirm? |
|---|---|---|---|
| `sqs` | SQS queue ARN | `arn:aws:sqs:us-east-1:111111111111:my-queue` | Yes (if caller owns) |
| `lambda` | Lambda function ARN | `arn:aws:lambda:us-east-1:111111111111:function:my-fn` | Yes (if caller owns) |
| `firehose` | Firehose ARN | `arn:aws:firehose:us-east-1:111111111111:deliverystream/my-stream` | Yes (if caller owns) |
| `https` | HTTPS URL | `https://api.example.com/webhook` | No (token-based) |
| `http` | HTTP URL | `http://api.example.com/webhook` | No (token-based) |
| `email` | Email address | `user@example.com` | No (token-based) |
| `email-json` | Email address | `user@example.com` | No (token-based) |
| `sms` | E.164 phone | `+12065551234` | No (token-based) |
| `application` | Platform endpoint ARN | `arn:aws:sns:us-east-1:111111111111:endpoint/GCM/...` | No (token-based) |

## Subscription attribute catalog

Set via `set-subscription-attributes --subscription-arn <arn>
--attribute-name <name> --attribute-value <value>`.

| Attribute | Applies to | Description |
|---|---|---|
| `FilterPolicy` | All | JSON filter policy; matches on message attributes |
| `FilterPolicyScope` | All | `MessageAttributes` (default) or `MessageBody` |
| `RawMessageDelivery` | sqs, lambda, http(s), firehose | `true` = deliver only Message body; `false` = full SNS envelope |
| `DeliveryPolicy` | sqs, lambda, http(s), firehose, application | JSON retry/backoff policy |
| `RedrivePolicy` | sqs, lambda, http(s), firehose, application | JSON with `deadLetterTargetArn` (SQS DLQ ARN) |
| `ConfirmationTimeout` | All | Not settable; confirmation tokens expire after 3 days |
| `SubscriptionRoleArn` | firehose | IAM role for SNS to write to Firehose |

## Per-protocol capability matrix

| Capability | sqs | lambda | firehose | https | http | email | sms |
|---|---|---|---|---|---|---|---|
| Filter policy | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Delivery policy (retry) | Yes | Yes | Yes | Yes | Yes | No | No |
| DLQ (redrive) | Yes | Yes | Yes | Yes | Yes | No | No |
| RawMessageDelivery | Yes | Yes | Yes | Yes | Yes | N/A | N/A |
| FIFO topic support | Yes (FIFO queue only) | No | No | No | No | No | No |

## RawMessageDelivery payload comparison

### RawMessageDelivery: false (default for SQS)

The SQS message body contains the full SNS envelope:
```json
{
  "Type": "Notification",
  "MessageId": "abc-123",
  "TopicArn": "arn:aws:sns:us-east-1:111111111111:my-topic",
  "Message": "{\"order_id\": \"ORD-001\"}",
  "Timestamp": "2026-08-11T10:00:00.000Z",
  "MessageAttributes": {"event_type": {"Type": "String", "Value": "order_created"}}
}
```

### RawMessageDelivery: true

The SQS message body contains only the Message field:
```json
{"order_id": "ORD-001"}
```

**When to use RawMessageDelivery: true:**
- SQS-to-Lambda triggers (Lambda receives the message body directly,
  no SNS envelope parsing needed).
- HTTP/HTTPS endpoints that expect the raw message body, not the SNS
  envelope.
- Firehose subscriptions where the stream delivers the raw body to S3.

**When to keep RawMessageDelivery: false:**
- Endpoints that need the SNS metadata (MessageId, TopicArn,
  Timestamp, MessageAttributes).
- Debugging workflows where the envelope context is useful.

## Firehose subscription specifics (2024+)

- Protocol: `firehose`
- Endpoint: Firehose delivery stream ARN
- `SubscriptionRoleArn`: IAM role that grants SNS permission to write
  to the Firehose stream. The role must have
  `firehose:PutRecordBatch` on the stream ARN.
- RawMessageDelivery: `true` recommended (deliver raw body to
  Firehose, which then delivers to S3/Redshift/OpenSearch).
- The Firehose stream must be `ACTIVE` before subscription creation.

## SNS message data protection interaction

If the topic has a message data protection policy (`getDataProtectionPolicy`):
- Messages containing sensitive data (PII, financial, health) may be
  audited (logged), masked (redacted), or denied (blocked).
- Subscribers may receive masked versions of messages or no message at
  all if the policy denies.
- The data protection policy is evaluated BEFORE the subscription
  filter policy — a denied message never reaches any subscriber.
- Always verify the data protection policy when diagnosing missing
  messages on a topic with known sensitive content.
