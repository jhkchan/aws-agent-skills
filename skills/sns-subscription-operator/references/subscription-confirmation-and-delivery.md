# SNS Subscription Confirmation & Delivery Reference

Load this reference when planning subscription creation, confirmation,
or delivery-policy operations. Contains the per-protocol confirmation
matrix, delivery-retry math, and the filter-policy match model.

## Confirmation matrix (per protocol)

| Protocol | Auto-confirmed? | Token delivery method | Token validity | Confirm API needed? |
|---|---|---|---|---|
| `sqs` | Yes (if caller owns queue) | N/A | N/A | No |
| `sqs` (cross-account) | No | N/A (endpoint owner must confirm) | N/A | Yes (endpoint owner) |
| `lambda` | Yes (if caller owns function) | N/A | N/A | No |
| `lambda` (cross-account) | No | N/A | N/A | Yes (endpoint owner) |
| `firehose` | Yes (if caller owns stream) | N/A | N/A | No |
| `https` | No | POST to endpoint with Token + SubscribeURL | 3 days | Yes |
| `http` | No | POST to endpoint with Token + SubscribeURL | 3 days | Yes |
| `email` | No | Email with Token + confirmation link | 3 days | Yes (click link or API) |
| `email-json` | No | Email (JSON format) with Token | 3 days | Yes |
| `sms` | No | SMS with Token | 3 days | Yes |
| `application` | No | Mobile push with Token | 3 days | Yes |

## Confirmation flow (HTTP/HTTPS)

1. `subscribe --protocol https --notification-endpoint <url>` returns
   `SubscriptionArn: "pending confirmation"`.
2. SNS sends an HTTP POST to the endpoint with header
   `x-amz-sns-message-type: SubscriptionConfirmation` and a JSON body
   containing `Token`, `SubscribeURL`, and `TopicArn`.
3. The endpoint MUST return HTTP 200 to acknowledge receipt.
4. The endpoint extracts the `Token` and either:
   - Visits the `SubscribeURL` (GET request), OR
   - Calls `confirm-subscription --topic-arn <arn> --token <token>`.
5. SNS marks the subscription as confirmed
   (`PendingConfirmation: false`).

**Common failure:** the endpoint returns 4xx/5xx for the confirmation
POST. SNS retries the confirmation POST up to 3 times over 5 minutes,
then gives up. The subscription remains in `pending confirmation`.

## Confirmation flow (email)

1. `subscribe --protocol email --notification-endpoint <addr>` returns
   `SubscriptionArn: "pending confirmation"`.
2. SNS sends a confirmation email containing a `SubscribeURL` link.
3. The recipient clicks the link (or the token is extracted and passed
   to `confirm-subscription`).
4. SNS marks the subscription as confirmed.

**Common failure:** the email is spam-filtered. Always check the spam
folder. The email is sent from `no-reply@sns.amazonaws.com`.

## Delivery retry policy (per subscription)

The default retry policy is 4 attempts over 1 hour:
- Attempt 1: immediate
- Attempt 2: 1 second
- Attempt 3: 2 seconds
- Attempt 4: 4 seconds (then stop, send to DLQ if configured)

Configurable via `set-subscription-attributes --attribute-name
DeliveryPolicy`:

```json
{
  "healthyRetryPolicy": {
    "numRetries": 5,
    "minDelayTarget": 1,
    "maxDelayTarget": 16,
    "numMinDelayRetries": 2,
    "numMaxDelayRetries": 3,
    "backoffFunction": "exponential"
  },
  "sicklyRetryPolicy": {
    "numRetries": 10,
    "minDelayTarget": 10,
    "maxDelayTarget": 600,
    "numMinDelayRetries": 5,
    "numMaxDelayRetries": 5,
    "backoffFunction": "linear"
  },
  "throttlePolicy": {
    "maxReceivesPerSecond": 10
  }
}
```

- `healthyRetryPolicy`: applies when the endpoint was previously
  healthy (returning 200) and starts failing.
- `sicklyRetryPolicy`: applies when the endpoint has been failing.
- `throttlePolicy`: rate-limits delivery to protect the endpoint.
- `backoffFunction`: `exponential` or `linear` or `arithmetic`.

## Filter-policy match model

Filter policies match on **message attributes** (default) or **message
body** (if `FilterPolicyScope: MessageBody`).

### Attribute-based filtering (default)

```json
// Filter policy
{"event_type": ["order_created", "order_updated"]}

// Publisher must include message attribute:
// --message-attributes '{"event_type": {"DataType": "String", "StringValue": "order_created"}}'
```

### Conditional operators

| Operator | Example | Matches |
|---|---|---|
| Exact | `["order_created"]` | event_type == "order_created" |
| Anything-but | `[{"anything-but": ["test"]}]` | event_type != "test" |
| Prefix | `[{"prefix": "order_"}]` | event_type starts with "order_" |
| Numeric | `[{"numeric": [">=", 100]}]` | price >= 100 |
| Exists | `[{"exists": true}]` | attribute "optional_field" is present |
| Exists (false) | `[{"exists": false}]` | attribute is absent |

### Boolean logic

- Multiple attributes in the filter policy: logical AND (all must
  match).
- Multiple values for one attribute: logical OR (any match).

### Body-based filtering

```json
// Filter policy (matches message body)
{"customer_tier": ["premium"]}

// Requires:
// 1. FilterPolicyScope = MessageBody
// 2. Message body is valid JSON: {"customer_tier": "premium", ...}
```

## DLQ (subscription redrive) requirements

- DLQ MUST be an SQS queue (no other protocol).
- DLQ queue policy MUST allow `sqs:SendMessage` from SNS:
  ```json
  {"Effect": "Allow", "Principal": {"Service": "sns.amazonaws.com"},
   "Action": "sqs:SendMessage", "Resource": "<dlq-arn>",
   "Condition": {"ArnEquals": {"aws:SourceArn": "<topic-arn>"}}}
  ```
- DLQ MUST NOT be the same SQS queue as the subscription endpoint
  (creates a retry loop).
- Messages land in the DLQ after the delivery policy retries are
  exhausted.
- To replay: read from the DLQ and re-publish to the topic (or deliver
  directly to the endpoint after fixing it).

## Cross-account subscription requirements

Both sides must have permission:

**Topic owner side** (topic policy):
```json
{"Effect": "Allow",
 "Principal": {"AWS": "arn:aws:iam::<subscriber-account>:root"},
 "Action": "sns:Subscribe",
 "Resource": "<topic-arn>"}
```

**Endpoint owner side** (queue policy for SQS):
```json
{"Effect": "Allow",
 "Principal": {"Service": "sns.amazonaws.com"},
 "Action": "sqs:SendMessage",
 "Resource": "<queue-arn>",
 "Condition": {"ArnEquals": {"aws:SourceArn": "<topic-arn>"}}}
```

Missing either side produces `AuthorizationError` or silent non-delivery.
