# Advanced Patterns — SNS Subscription Operator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Expert heuristic — the non-obvious rules

**One-line takeaway:** SNS subscriptions are a two-phase system
(subscribe then confirm) where the confirmation flow varies by
protocol, and the filter policy + delivery policy + RawMessageDelivery
setting together determine whether a message reaches the endpoint.
Seven non-obvious rules drive the verdict:

- **Rule 1 — SQS, Lambda, and Firehose subscriptions are auto-confirmed
  when the caller owns the endpoint.** The subscribe API returns a
  `SubscriptionArn` immediately (not `pending confirmation`). For
  cross-account endpoints, the endpoint owner must still confirm.

- **Rule 2 — HTTP/HTTPS/email/sms subscriptions require token-based
  confirmation.** The subscribe API returns `SubscriptionArn:
  "pending confirmation"`. The endpoint receives a message/email/SMS
  containing a token. The token is passed to `confirm-subscription`.
  Without confirmation, the subscription does not receive messages.

- **Rule 3 — Filter policies match on message attributes, not message
  body.** A filter policy like `{"event_type": ["order_created"]}`
  matches only if the published message includes a message attribute
  `event_type` with value `order_created`. Without the attribute, the
  message is NOT delivered to the subscription. This is the #1 cause
  of "SNS not delivering" issues.

- **Rule 4 — `FilterPolicyScope` defaults to `MessageAttributes`.** Set
  to `MessageBody` to filter on the message body (requires the message
  body to be valid JSON). Mixing the two without setting the scope
  produces silent non-delivery.

- **Rule 5 — RawMessageDelivery strips S3/SNS envelope JSON for
  SQS/Lambda/HTTP endpoints.** With RawMessageDelivery enabled, the
  endpoint receives only the `Message` field (not the full SNS JSON
  envelope). This is required for SQS triggers on Lambda (otherwise
  the Lambda receives the SNS envelope and must parse it).

- **Rule 6 — The delivery policy retry is per-subscription, not per-
  topic.** Each subscription has its own delivery policy with
  `minDeliveryTarget`, `maxRetryAttempts`, and backoff. The topic-
  level delivery policy is a default; the subscription delivery policy
  overrides it.

- **Rule 7 — The subscription DLQ (redrive) is configured via
  `set-subscription-attributes` with `RedrivePolicy`, not the topic
  DLQ.** The subscription redrive policy specifies a DLQ SQS ARN.
  Failed deliveries (after exhausting retries) are sent to the DLQ.
  The DLQ must be an SQS queue — no other protocol is supported for
  subscription redrive.

### Step 0: Expert knowledge — non-obvious SNS subscription behaviors

These behaviors are easy to misjudge without operational SNS
experience. Each changes a plan if ignored:

- **Confirmation is a two-phase commit for HTTP/HTTPS/email/sms.** The
  subscribe API returns `"pending confirmation"` and sends a
  confirmation message to the endpoint. The endpoint must extract the
  token and return it to SNS via `confirm-subscription`. Without
  confirmation, no messages are delivered. SQS, Lambda, and Firehose
  subscriptions owned by the caller are auto-confirmed.

- **Cross-account subscriptions require BOTH sides' permission.** The
  topic policy must allow `sns:Subscribe` for the subscriber's
  account. The endpoint (if SQS/Lambda) must have a resource policy
  allowing the SNS topic to invoke it. Missing either side's
  permission is the #1 cause of cross-account subscription failures.

- **Filter policies silently drop non-matching messages.** A filter
  policy like `{"event_type": ["order_created"]}` drops any message
  that does not include a `event_type` message attribute with value
  `order_created`. There is no error, no CloudTrail event, no DLQ
  delivery — the message is silently filtered. This is by design but
  catches operators off guard.

- **Filter policies support `anything-but`, `prefix`, `numeric`
  conditions, and `exists` operators.** A filter policy is not limited
  to exact match. `{"event_type": [{"anything-but": ["test"]}]}`,
  `{"price": [{"numeric": [">=", 100]}]}`, and `{"optional_field":
  [{"exists": true}]}` are all valid.

- **`FilterPolicyScope: MessageBody` enables body-based filtering.**
  By default, filter policies match on message attributes. Set the
  scope to `MessageBody` to filter on the JSON message body. The
  message body must be valid JSON; non-JSON bodies are rejected by
  the filter.

- **RawMessageDelivery changes the payload format at the endpoint.**
  With RawMessageDelivery disabled (default), SQS/Lambda/HTTP
  endpoints receive the full SNS JSON envelope (`Type`, `MessageId`,
  `TopicArn`, `Message`, etc.). With RawMessageDelivery enabled, the
  endpoint receives only the `Message` field. For SQS-to-Lambda
  triggers, RawMessageDelivery is recommended (the Lambda receives
  the message body directly).

- **The subscription delivery policy overrides the topic delivery
  policy.** If both are set, the subscription delivery policy wins.
  The topic delivery policy is a fallback for subscriptions without
  their own policy.

- **Delivery retry uses exponential backoff.** The default retry is 4
  attempts over 1 hour (immediate, 1s, 2s, 4s... up to the max). The
  subscription delivery policy allows tuning `numMaxRetries`,
  `numMinDelayRetries`, `numMaxDelayRetries`, and backoff function
  (linear or arithmetic).

- **The subscription DLQ (redrive) requires an SQS queue.** The
  `RedrivePolicy` attribute specifies a `deadLetterTargetArn` (SQS
  queue ARN). No other protocol is supported. The DLQ queue policy
  must allow the SNS service to `sqs:SendMessage` to it.

- **FIFO topics require SQS FIFO queue subscriptions.** A FIFO topic
  (name suffix `.fifo`) only supports SQS FIFO queue endpoints.
  HTTP/HTTPS/Lambda/email/sms/firehose are NOT supported for FIFO
  topics. Content-based deduplication and message grouping apply.

- **SNS message data protection (2024-2026) can block messages before
  delivery.** A message data protection policy on the topic can
  audit, mask, or deny messages containing sensitive data (PII,
  financial data) based on message attributes or body. A subscription
  may receive masked messages or no message if the policy denies.
  Verify the topic's message data protection policy when diagnosing
  missing messages.

- **Firehose subscription (2024+) delivers messages to a Firehose
  delivery stream.** The Firehose can then deliver to S3, Redshift,
  OpenSearch, or an HTTP endpoint. This is useful for streaming
  pipelines where SNS fans out to Firehose for batch delivery. The
  Firehose delivery stream must be `ACTIVE`.

- **Subscription attributes are eventually consistent.**
  `set-subscription-attributes` returns immediately, but
  `get-subscription-attributes` may show the old value for a few
  seconds. Do not alarm on a short-lived inconsistency.

## Edge-case handling

| Scenario | Detection | Handling |
|---|---|---|
| **HTTP endpoint returns 403 on confirmation POST** | SNS confirmation POST includes `x-amz-sns-message-type: SubscriptionConfirmation`; endpoint rejects it | Fix the endpoint to accept the SNS POST header and return 200. The endpoint must extract the `Token` and `SubscribeURL` from the JSON body. |
| **FIFO topic with Lambda subscription** | Topic name ends in `.fifo` | FIFO topics only support SQS FIFO queue endpoints. Lambda/HTTP/email are NOT supported. Switch to an SQS FIFO queue and trigger Lambda from the queue. |
| **Firehose subscription with delivery stream in CREATING state** | `describe-delivery-stream` shows `DeliveryStreamStatus: CREATING` | Wait for the stream to become `ACTIVE` before creating the subscription. SNS will fail delivery to a non-active stream. |
| **Topic message data protection denying messages** | Topic `getDataProtectionPolicy` has a `Deny` rule for the message content | The data protection policy audits, masks, or denies messages containing sensitive data. Verify the policy and adjust the publisher to exclude sensitive data, or adjust the policy to allow the data for trusted workloads. |

## Recent AWS features (2024-2026)

- **SNS subscription with Firehose target (2024-2025):** SNS now
  supports `firehose` as a subscription protocol. Messages are
  delivered to a Firehose delivery stream, which can then deliver to
  S3, Redshift, OpenSearch, or an HTTP endpoint. Useful for streaming
  pipelines where SNS fans out to Firehose for batch delivery. The
  Firehose stream must be `ACTIVE`.

- **SNS message data protection (2024-2026):** A message data
  protection policy on the topic can audit, mask, or deny messages
  containing sensitive data (PII, financial, health) based on message
  attributes or body content. Subscribers may receive masked messages
  or no message if the policy denies. Verify the topic's
  `getDataProtectionPolicy` when diagnosing missing messages.

- **Subscription filter-policy scope for MessageBody (2024):**
  `FilterPolicyScope: MessageBody` enables filtering on the JSON
  message body (not just attributes). The message body must be valid
  JSON. Useful when the publisher cannot set message attributes.

- **SNS FIFO topic support expanded (2024-2025):** FIFO topics support
  content-based deduplication, message grouping, and exactly-once
  processing when paired with SQS FIFO queues. HTTP/HTTPS/Lambda/email
  subscriptions are NOT supported for FIFO topics.

- **Batch publish API (2024-2025):** SNS supports publishing up to 10
  messages in a single `PublishBatch` API call. Does not affect
  subscription operations but is relevant for publisher-side
  throughput planning.

- **Cross-account delivery logging (2025):** CloudTrail now includes
  the subscriber account in delivery events for cross-account
  subscriptions, making it easier to audit message flow across
  accounts.
