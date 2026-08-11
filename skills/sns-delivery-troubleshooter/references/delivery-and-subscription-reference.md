# SNS Delivery and Subscription Reference Guide

Supplementary reference for the SNS Delivery Troubleshooter skill.
Loaded on-demand when a diagnostic needs the exact delivery retry
sequence, subscription protocol semantics, filter-policy operator
reference, message attribute propagation rules, or size cap matrix.

## HTTP/HTTPS retry schedule (default delivery policy)

```
Attempt 1: immediate (T+0)
Attempt 2: +1 second (T+1s)
Attempt 3: +10 seconds (T+10s)
Attempt 4: +100 seconds (T+100s)   — final immediate retry
--- (if healthyRetryPolicy extends to delayed retries) ---
Attempt 5: +1000 seconds (T+1000s)
Attempt 6: +2000 seconds
Attempt 7: +4000 seconds
Attempt 8: +8000 seconds
Attempt 9: +16000 seconds          — maximum (5 delayed after 4 immediate)
```

Default: 4 immediate retries. Maximum: 4 immediate + 5 delayed (9
total). Configurable per-subscription via `DeliveryPolicy`.

### 4xx vs 5xx semantics

| Response class | SNS treatment | After final retry |
|---|---|---|
| 2xx | Delivered | n/a |
| 3xx | Followed (up to 5 redirects) | Loop = failure |
| 4xx | Retried (immediate + delayed per policy) | **Permanent rejection** — message dropped |
| 5xx | Retried | **Transient failure** — message dropped if all retries fail |
| Timeout | Retried | Dropped if DeliveryPolicy timeout exceeded |

A 4xx under load (401 auth expired, 403 forbidden, 404 decommissioned,
429 rate limited) looks like "intermittent delivery loss" because the
endpoint recovers between retries. The permanent-rejection treatment
means the message is NOT re-delivered after the final retry.

## Subscription protocol matrix

| Protocol | Auto-confirm? | Retry / durability | Notes |
|---|---|---|---|
| http / https | NO (manual token) | 4 immediate + up to 5 delayed | Endpoint must call `ConfirmSubscription` |
| lambda | YES (console) / needs resource policy (IaC) | Lambda async retry (2 retries) | `InvocationType: Event` |
| sqs | YES (console) / needs queue policy (IaC) | SQS handles durability | Fan-out pattern; ordering if both FIFO |
| email / email-json | YES (recipient clicks confirm link) | None | Subject to SES bounce / complaint |
| sms | n/a | Best-effort | Per-region opt-out lists |
| platform (mobile push) | n/a (endpoint-level) | SNS retries per platform | APNS / FCM / ADM / Baidu |
| application (legacy mobile) | n/a | Deprecated | Use `platform` instead |

### Auto-confirm gotcha

Lambda and SQS subscriptions auto-confirm when created via the AWS
console. When created via CLI, Terraform, or CloudFormation, the
subscription ARN is returned but the target-side resource policy must
explicitly grant the SNS service principal invoke permission. The
console auto-adds; IaC does NOT.

## Filter policy operator reference

| Operator | Syntax | Matches | Does NOT match |
|---|---|---|---|
| Exact | `["order.created"]` | `event=order.created` | `event=order.updated`, no attribute |
| Prefix | `[{"prefix": "order."}]` | `event=order.created`, `event=order.updated` | `event=payment.created` |
| Anything-but | `[{"anything-but": ["cancelled"]}]` | `event=order.created`, `event=shipped` | `event=cancelled` |
| Numeric | `[{"numeric": [">=", 100, "<", 1000]}]` | `amount=500` | `amount=50`, `amount=2000` |
| Exists | `[{"exists": true}]` | Attribute present (any value) | Attribute absent |
| Not-exists | `[{"exists": false}]` | Attribute absent | Attribute present |

### FilterPolicyScope (2024-2025)

By default, filter policies match on `MessageAttributes`. Set
`FilterPolicyScope: MessageBody` to match on JSON payload fields
instead. A filter policy that references body fields without setting
`FilterPolicyScope: MessageBody` silently drops everything.

### Default behaviour for missing attributes

A subscription with NO filter policy receives ALL messages (including
those without attributes). A subscription WITH a filter policy drops
messages that lack the referenced attribute UNLESS the policy uses
`exists: false`.

## Message attribute propagation (SNS to SQS)

| RawMessageDelivery | SQS message attributes | SQS message body | Envelope overhead |
|---|---|---|---|
| `false` (default) | Set from SNS attributes | Full SNS JSON envelope (Message, MessageId, TopicArn, Timestamp, Signature, ...) | 1-4 KB |
| `true` | NOT set on SQS message | Raw SNS message body (no envelope) | None |

### Size implications

SNS message body + attributes: 256 KB total cap (enforced at publish
time). SQS message: 256 KB cap (enforced at enqueue time). With
`RawMessageDelivery: false`, the SNS JSON envelope wraps the body —
a 254 KB SNS body can produce a 258 KB SQS message that exceeds the
SQS cap.

**Fix:** enable `RawMessageDelivery: true` to remove envelope overhead,
OR reduce the SNS payload, OR raise the SQS `MaximumMessageSize`
(maximum 262144 bytes = 256 KB — cannot be raised above the cap).

## SNS message size limits

| Component | Cap |
|---|---|
| Message body + attributes (combined) | 256 KB |
| Message attribute name | 256 bytes |
| Message attribute value (Binary) | 256 KB (counted toward total) |
| Message attribute value (String) | 256 KB (counted toward total) |
| Message attribute data type | 256 bytes |
| Batch publish | 10 messages per `publish-batch` call; each subject to the 256 KB cap |

## CloudWatch AWS/SNS metrics

| Metric | Dimension(s) | What it tells you |
|---|---|---|
| `NumberOfNotificationsPublished` | TopicName | Messages received from publishers |
| `NumberOfNotificationsDelivered` | TopicName, Endpoint | Successful deliveries per subscription |
| `NumberOfNotificationsFailed` | TopicName, Endpoint | Failed delivery attempts per subscription |
| `PublishSize` | TopicName | Average message size |
| `PublishSize` (extended p99) | TopicName | Tail message size (cap-exceed risk) |

### Delivery accounting

If `NumberOfNotificationsDelivered + NumberOfNotificationsFailed =
NumberOfNotificationsPublished`, SNS accounts for every message.

If `Delivered + Failed < Published`, the gap is filter-policy drops
(silent — not counted as Failed). This is the only signal for
filter-policy mismatches.

## Platform endpoint (mobile push) lifecycle

| State | Meaning | SNS behaviour |
|---|---|---|
| `Enabled: true` | Active device token | Push attempted |
| `Enabled: false` | Auto-disabled after permanent failure (token revoked, app uninstalled) | Push silently fails; no error to publisher |

SNS auto-disables an endpoint when the push service (APNS, FCM)
returns a permanent failure. The endpoint must be re-registered with
a fresh device token to resume delivery.

## AWS Health event categories that affect SNS

| Category | Likely impact |
|---|---|
| `AWS_SNS_SERVICE` | Region-wide SNS degradation; delivery delays or failures |
| `AWS_LAMBDA_SERVICE` | Lambda subscription invocations fail even if SNS is healthy |
| `AWS_SQS_SERVICE` | SQS enqueue from SNS fails; fan-out queues stop filling |

Always probe `aws health describe-events` for regional issues before
declaring a customer-side root cause during a wide-impact incident.
