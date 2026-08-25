# Advanced Patterns — SNS Delivery Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Expert heuristic

A senior integration engineer applies three quick checks before any
deep diagnosis. Each is non-obvious and routes the diagnosis away from
the obvious layer:

1. **HTTP endpoint retry follows a fixed 4-attempt schedule.** SNS
   retries HTTP/HTTPS delivery: immediate, +1s, +10s, +100s (4
   immediate by default; configurable up to 4 immediate + 5 delayed).
   A 5xx endpoint that recovers within the retry window eventually
   receives the message. A 4xx endpoint is treated as a permanent
   rejection after the final retry — the message is dropped. If the
   operator reports "intermittent delivery loss," check whether the
   endpoint returns 4xx under load (rate limiting, auth expiry).
2. **Filter policy JSON scope matching is strict.**
   `{"event": ["order.created"]}` matches attribute
   `event=order.created` exactly. A message with
   `event=order.created.v2` does NOT match (no prefix by default). A
   message with NO `event` attribute does NOT match. Subscriptions
   with NO filter policy receive all messages; subscriptions WITH a
   filter policy drop messages lacking the attribute unless the policy
   uses `exists` or `anything-but` operators.
3. **Fan-out via SQS is the durability pattern.** SNS-to-SQS fan-out
   (one topic, N queues, each consumed independently) decouples the
   consumer from the publisher. A slow or failing consumer does NOT
   affect other consumers. Direct SNS-to-Lambda does not have this
   property — a slow Lambda backs up delivery and eventually triggers
   the retry policy. Recommend SQS fan-out for multi-consumer
   durability.

### Step 0: Non-obvious behaviours that change diagnosis

- **Subscription confirmation is manual for HTTP/HTTPS.** SNS sends a
  `SubscriptionConfirmation` token; the endpoint must call
  `ConfirmSubscription`. Until confirmed, ZERO messages deliver.
  Lambda and SQS subscriptions auto-confirm; HTTP/HTTPS do not.
- **Filter policies silently drop non-matching messages.** No error,
  no DLQ entry, no metric spike. Signal: `Delivered < Published`.
- **HTTP 4xx is permanent rejection after the retry sequence.** A 403
  (auth expired) or 429 (rate limited) under load looks like
  "intermittent delivery loss."
- **Lambda subscriptions use async invocation (`InvocationType:
  Event`).** Lambda retries twice on failure then drops. Without an
  OnFailure destination or DLQ, the SNS message vanishes.
- **`RawMessageDelivery: true` strips SQS message attributes.**
  Consumer must parse from the SNS JSON body. `false` propagates
  attributes but adds envelope overhead that can push a 250 KB payload
  over the 256 KB SQS cap.
- **FIFO topics require FIFO queues.** A standard SQS queue subscribed
  to a FIFO topic delivers but breaks ordering.
- **Cross-region Lambda subscription needs the function resource
  policy to grant `lambda:InvokeFunction` from the SNS topic's
  account.** Console auto-grants same-region; CLI / Terraform do not.
- **Platform endpoints auto-disable on permanent push failure** (token
  revoked, app uninstalled). SNS sets `Enabled: false`; future
  publishes silently fail.
- **SNS message size cap is 256 KB** (body + attributes combined).

## Deep reference — quick lookup

### HTTP/HTTPS retry schedule (default delivery policy)

```
Attempt 1: immediate; 2: +1s; 3: +10s; 4: +100s (final immediate)
Optional delayed: +1000s, +2000s, ... (up to 5 delayed after the 4
immediate). Maximum: 4 immediate + 5 delayed (9 total).
```
4xx = permanent rejection after final retry (dropped). 5xx = transient;
retried; dropped if all retries fail. Configurable per-subscription
via `DeliveryPolicy`.

### Subscription protocol matrix

| Protocol | Auto-confirm? | Retry / durability |
|---|---|---|
| http / https | NO (manual token) | 4 immediate + up to 5 delayed |
| lambda | YES (console) / resource policy (IaC) | Lambda async retry (2) |
| sqs | YES (console) / queue policy (IaC) | SQS handles durability |
| email / email-json | YES (recipient clicks link) | None |
| sms / platform (mobile push) | n/a | Best-effort / SNS retries per platform |

### Filter policy operator reference

| Operator | Syntax | Matches |
|---|---|---|
| Exact | `["value"]` | Attribute equals value |
| Prefix | `[{"prefix": "order."}]` | Starts with prefix |
| Anything-but | `[{"anything-but": ["x"]}]` | Not in the list |
| Numeric | `[{"numeric": [">=", 100]}]` | Numeric range |
| Exists | `[{"exists": true}]` / `[{"exists": false}]` | Present / absent |

### SNS message size limits

Message body + attributes: 256 KB total. Attribute name: 256 bytes.
With `RawMessageDelivery: false`, the JSON envelope adds 1-4 KB
overhead — a 254 KB SNS message can exceed the 256 KB SQS cap.

### CloudWatch AWS/SNS metrics

| Metric | Dimension | Meaning |
|---|---|---|
| `NumberOfNotificationsPublished` | TopicName | Messages received from publishers |
| `NumberOfNotificationsDelivered` | TopicName + Endpoint | Successful deliveries per subscription |
| `NumberOfNotificationsFailed` | TopicName + Endpoint | Failed delivery attempts |
| `PublishSize` | TopicName | Average / tail message size |

If `Delivered + Failed = Published`, SNS accounts for every message.
If `Delivered + Failed < Published`, filter policies are silently
dropping messages (not counted as Failed).

## Recent AWS features (2024-2026)

- **FIFO topic GA (2024):** In-order, exactly-once within a
  MessageGroupId. Requires FIFO queues on the subscription side.
- **`FilterPolicyScope` attribute (2024-2025):** Filter policies can
  match on `MessageBody` (JSON payload) in addition to
  `MessageAttributes`. A filter referencing body fields without
  `FilterPolicyScope: MessageBody` silently drops everything.
- **`publish-batch` (2024-2025):** Up to 10 messages per call. Batch-
  level failure (size cap exceeded) fails all 10; per-message filter-
  policy drops apply individually.
- **SNS subscription DLQ `RedrivePolicy` (2024-2025):** Routes dropped
  messages (after retry exhaustion) to an SQS DLQ. Distinct from any
  Lambda-side OnFailure destination.
- **Cross-region delivery hardening (2024-2025):** Console now auto-
  propagates the resource policy for cross-region Lambda subscriptions.
  CLI / Terraform still require explicit `add-permission`.
