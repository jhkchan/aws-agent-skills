# Topic Configuration Guide — SNS Topic Deployer

Deep reference on SNS topic internals, delivery retry semantics, subscription
confirmation flow, filter policy operators, cross-account KMS key policy
requirements, and mobile push platform-specific message formats.

## Topic type internals

### Standard topic delivery semantics

Standard SNS topics provide **best-effort ordering** and **at-least-once**
delivery. Under normal operation, messages are delivered in the order
published. Under high throughput or cross-region delivery, messages may
arrive out of order at the subscriber.

Standard topics support all subscription protocols: HTTP/HTTPS, SQS,
Lambda, Email/Email-JSON, Firehose, Application (mobile push), and SMS.

### FIFO topic delivery semantics

FIFO topics provide **strict ordering** and **exactly-once** delivery
(with deduplication). Messages are ordered per `MessageGroupId`.

**FIFO topic constraints:**

- ONLY SQS FIFO queues can be subscribers. HTTP, HTTPS, email, SMS,
  Lambda, and Application subscriptions are rejected by the SNS API.
- Throughput: 300 TPS (aggregate across all message groups).
- Name MUST end in `.fifo`.
- `MessageGroupId` is required on every published message.
- Deduplication: `ContentBasedDeduplication=true` (topic-level SHA-256
  hash) OR explicit `MessageDeduplicationId` per message (5-minute
  window).

### Why FIFO only supports SQS FIFO subscribers

SNS FIFO topics are designed for ordered fan-out to ordered queues. HTTP,
email, Lambda, and mobile push endpoints do not have a concept of
"ordered delivery" — they are fire-and-forget push targets. SQS FIFO
queues are the only subscriber type that can preserve SNS FIFO ordering
guarantees.

If you need ordering AND a Lambda subscriber, use:
```
SNS FIFO topic → SQS FIFO queue → Lambda (event source mapping)
```
This preserves ordering while allowing Lambda consumption.

## Delivery retry semantics

SNS retries delivery differently per protocol:

| Protocol | Retry strategy | Duration | Max attempts |
|---|---|---|---|
| HTTP/HTTPS | Exponential backoff (4 hours) | 4 hours | 100,010 |
| SQS | Immediate (single attempt) | Instant | 1 (SQS handles its own retry) |
| Lambda | Lambda async retry | ~6 hours | 2 retries + DLQ |
| Firehose | Firehose handles retry | Configurable | Firehose config |
| Email | One-time (no retry) | — | 1 |
| Application (mobile push) | Platform-dependent | Varies | Varies |
| SMS | One-time (no retry) | — | 1 |

**HTTP retry schedule:** 20s, 20s, 20s, 20s, 20s, 30s, 30s, 30s, 30s, 30s,
60s, 60s, 60s, 60s, 60s, ... up to 100,010 attempts over 4 hours.

After the retry budget is exhausted, the message is silently dropped
(unless a subscription DLQ is configured). This is why delivery status
logging is critical for HTTP subscriptions.

## Subscription confirmation flow

When `aws sns subscribe` is called for HTTP/HTTPS/email protocols, SNS
sends a `SubscriptionConfirmation` message to the endpoint:

```json
{
  "Type": "SubscriptionConfirmation",
  "MessageId": "xxxxx",
  "Token": "xxxxx",
  "TopicArn": "arn:aws:sns:us-east-1:111111111111:order-events",
  "Message": "You have chosen to subscribe...",
  "SubscribeURL": "https://sns.us-east-1.amazonaws.com/?Action=ConfirmSubscription&TopicArn=...&Token=...",
  "Timestamp": "2026-01-01T00:00:00.000Z"
}
```

The endpoint must GET the `SubscribeURL` within **3 days** to confirm.
After confirmation, the subscription status becomes `Confirmed`.

**For SQS and Lambda subscriptions** (same-account), SNS auto-confirms
when using `--return-subscription-arn`. No manual confirmation needed.

**For cross-account subscriptions**, only the subscriber account can
confirm — the confirmation token is sent to the subscriber's endpoint,
and the subscriber must call `ConfirmSubscription` with the token.

**PendingConfirmation state:** if the endpoint does not confirm within 3
days, the token expires. The subscription record persists in
`PendingConfirmation` indefinitely — it counts against the subscription
quota (12.5 million per topic) but does not receive messages. Clean up
with `aws sns unsubscribe --subscription-arn <arn>`.

## Filter policy operators (complete reference)

### MessageAttributes scope (default)

Filter policies on message attributes evaluate the attributes set by the
publisher via `--message-attributes`.

**Exact match:**
```json
{"event_type": ["order_created", "order_shipped"]}
```
Matches messages where `event_type` attribute is `order_created` OR
`order_shipped`.

**Prefix match:**
```json
{"order_id": [{"prefix": "ORD-"}]}
```
Matches messages where `order_id` attribute starts with `ORD-`.

**Anything-but:**
```json
{"event_type": [{"anything-but": ["order_cancelled"]}]}
```
Matches messages where `event_type` is anything except `order_cancelled`.

**Numeric range:**
```json
{"amount": [{"numeric": [">=", 100, "<=", 500]}]}
```
Matches messages where `amount` is between 100 and 500 (inclusive).

**Exists:**
```json
{"priority": [{"exists": true}]}
```
Matches messages that have a `priority` attribute (regardless of value).

**AND logic (multiple keys):**
```json
{"event_type": ["order_created"], "region": ["us-east-1"]}
```
Both conditions must match (AND logic across keys).

**OR logic (multiple values in one key):**
```json
{"event_type": ["order_created", "order_shipped"]}
```
Either value matches (OR logic within a key).

### MessageBody scope

When `FilterPolicyScope=MessageBody`, the filter evaluates JSON properties
in the message body instead of message attributes:

```json
{"event_type": ["order_created"], "amount": [{"numeric": [">=", 100]}]}
```

This matches a message body like:
```json
{"event_type": "order_created", "amount": 250, "order_id": "ORD-123"}
```

**IMPORTANT:** with `MessageBody` scope:
- The message body MUST be valid JSON. Non-JSON bodies cause silent
  filter failure (message not delivered, no error logged).
- Nested properties use dot notation: `{"user.region": ["us-east-1"]}`.
- The filter only evaluates the top-level JSON object (no arrays unless
  using special syntax).

## Cross-account KMS key policy requirements

For cross-account SNS-to-SQS delivery with SSE-KMS, three policies must
align:

### 1. SNS topic KMS key policy (topic owner's key)

The key must allow SNS to use it:
```json
{
  "Sid": "Allow SNS to use the key",
  "Effect": "Allow",
  "Principal": {"Service": "sns.amazonaws.com"},
  "Action": ["kms:Decrypt", "kms:GenerateDataKey*"],
  "Resource": "*",
  "Condition": {
    "StringEquals": {"kms:ViaService": "sns.us-east-1.amazonaws.com"}
  }
}
```

### 2. SQS queue KMS key policy (subscriber's key)

The key must allow SNS to publish encrypted messages:
```json
{
  "Sid": "Allow SNS to publish",
  "Effect": "Allow",
  "Principal": {"Service": "sns.amazonaws.com"},
  "Action": ["kms:GenerateDataKey*", "kms:Decrypt"],
  "Resource": "*",
  "Condition": {
    "StringEquals": {"kms:ViaService": "sqs.us-east-1.amazonaws.com"}
  }
}
```

### 3. SQS queue access policy

The queue policy must allow the SNS topic to SendMessage:
```json
{
  "Effect": "Allow",
  "Principal": {"Service": "sns.amazonaws.com"},
  "Action": "sqs:SendMessage",
  "Resource": "arn:aws:sqs:us-east-1:222222222222:subscriber-queue",
  "Condition": {
    "ArnEquals": {"aws:SourceArn": "arn:aws:sns:us-east-1:111111111111:topic"}
  }
}
```

If any of these three is misconfigured, messages are published to the
topic but never arrive in the subscriber queue — a silent failure.

## Mobile push platform message formats

### Apple Push Notification Service (APNS/APNS_SANDBOX)

```json
{
  "APNS": "{\"aps\":{\"alert\":\"Order shipped\",\"badge\":1,\"sound\":\"default\"},\"orderId\":\"12345\"}"
}
```

The `aps` dictionary is required by Apple. Custom payload data goes
alongside `aps`.

### Firebase Cloud Messaging (FCM/GCM)

```json
{
  "FCM": "{\"notification\":{\"title\":\"Order shipped\",\"body\":\"Your order #12345 has shipped\"},\"data\":{\"orderId\":\"12345\"}}"
}
```

`notification` triggers a system notification. `data` is a custom
key-value payload delivered to the app silently.

### Baidu Cloud Push

```json
{
  "Baidu": "{\"title\":\"Order shipped\",\"description\":\"Your order #12345 has shipped\",\"customContent\":{\"orderId\":\"12345\"}}"
}
```

### Amazon Device Messaging (ADM)

```json
{
  "ADM": "{\"data\":{\"message\":\"Order shipped\",\"orderId\":\"12345\"}}"
}
```

### Windows Push Notification Service (WNS)

WNS uses XML payloads per the WNS template type (Toast, Tile, Badge,
Raw).

### Multi-platform message (using message-structure json)

```bash
aws sns publish \
  --target-arn <endpoint-arn> \
  --message-structure json \
  --message '{
    "default": "{\"message\":\"Order shipped\"}",
    "APNS": "{\"aps\":{\"alert\":\"Order shipped\"}}",
    "FCM": "{\"notification\":{\"title\":\"Order shipped\"}}",
    "Baidu": "{\"title\":\"Order shipped\",\"description\":\"Order #12345\"}"
  }'
```

SNS delivers the platform-specific payload to each device type. The
`default` key is the fallback.

## Terraform equivalent

```hcl
# Standard topic with SSE-KMS
resource "aws_sns_topic" "events" {
  name              = "order-events"
  kms_master_key_id = "alias/aws/sns"
}

# FIFO topic
resource "aws_sns_topic" "fifo_events" {
  name                        = "order-events.fifo"
  fifo_topic                  = true
  content_based_deduplication = true
}

# SQS subscription
resource "aws_sns_topic_subscription" "sqs_sub" {
  topic_arn = aws_sns_topic.events.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.subscriber.arn

  filter_policy = jsonencode({
    event_type = ["order_created"]
  })
}

# HTTP subscription with delivery logging
resource "aws_sns_topic_subscription" "http_sub" {
  topic_arn           = aws_sns_topic.events.arn
  protocol            = "https"
  endpoint            = "https://api.example.com/sns-webhook"
  delivery_policy     = jsonencode({
    minDelayTarget     = 20
    maxDelayTarget     = 20
    numRetries         = 3
    numNoDelayRetries  = 0
    numMinDelayRetries = 0
    numMaxDelayRetries = 0
    backoffFunction    = "linear"
  })
}

# Topic access policy for S3 Event Notifications
resource "aws_sns_topic_policy" "events" {
  arn = aws_sns_topic.events.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = "*"
      Action    = "sns:Publish"
      Resource  = aws_sns_topic.events.arn
      Condition = {
        ArnEquals = {
          "aws:SourceArn" = "arn:aws:s3:::order-uploads"
        }
      }
    }]
  })
}
```

## Cross-account KMS key policy requirement

Cross-account KMS key policy requirement:
```json
{
  "Sid": "Allow cross-account SNS subscribers",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::222222222222:root" },
  "Action": ["kms:Decrypt", "kms:GenerateDataKey*"],
  "Resource": "*",
  "Condition": { "StringEquals": { "kms:ViaService": "sns.us-east-1.amazonaws.com" } }
}
```

## Mobile push notifications (Step 9)

```bash
# Create platform application
aws sns create-platform-application \
  --name MyAppAPNS --platform APNS \
  --attributes PlatformCredential=<private-key>,PlatformPrincipal=<certificate>

# Register device endpoint
aws sns create-platform-endpoint \
  --platform-application-arn arn:aws:sns:us-east-1:111111111111:app/APNS/MyAppAPNS \
  --token <device-token> \
  --custom-user-data '{"userId": "12345"}'

# Publish to mobile endpoint (use --message-structure json with default key)
aws sns publish \
  --target-arn <endpoint-arn> \
  --message-structure json \
  --message '{"default": "...", "APNS": "{\"aps\":{\"alert\":\"Order shipped\"}}", "FCM": "{\"notification\":{\"title\":\"Order shipped\"}}"}'
```

| Platform | Key | Format |
|---|---|---|
| APNS | `APNS` | `{"aps":{"alert":"message"}}` |
| FCM (Android) | `FCM`/`GCM` | `{"notification":{"title":"...","body":"..."}}` |
| Baidu | `Baidu` | `{"title":"...","description":"..."}` |
| Default | `default` | Fallback for all platforms |
