---
name: sns-delivery-troubleshooter
description: 'Diagnoses SNS delivery failures through a twelve-category diagnostic tree: HTTP/HTTPS endpoint delivery (subscription confirmation pending, signature verification failure, 4xx/5xx retry policy with 4 immediate + delayed retries), Lambda subscription failures (async invocation errors, DLQ routing), SQS subscription issues (message size cap, redrive policy), email bounce/complaint, platform endpoint (mobile push) disabled, subscription filter policy JSON scope mismatch, message attribute preservation, FIFO topic vs standard topic delivery ordering, cross-region delivery, CloudWatch delivery metrics (NumberOfNotificationsDelivered / Failed), and DLQ for SNS. Walks symptoms to a verified root cause with evidence-backed probes; emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted delivery logs and subscription configuration. Live-account diagnosis uses aws sns get-topic-attributes, list-subscriptions-by-topic, get-subscription-attributes, list-endpoints-by-platform-application, aws cloudwatch get-metric-statistics on AWS/SNS delivery metrics, aws logs filter-log-events for Lambda subscription failures, and aws sqs receive-message /...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AppIntegration
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing an SNS delivery failure — HTTP/HTTPS endpoint receives nothing or receives out-of-order, Lambda subscription does not invoke or fails, SQS subscription queue is empty or filling, email notifications bounce or get complaint-flagged, mobile push endpoint not receiving, filter policy drops messages it should match, message attributes missing downstream, FIFO topic ordering broken, cross-region delivery lagging, or CloudWatch delivery metrics show failures. Use whenever the operator says "SNS is not delivering" and the root cause may be subscription state, endpoint policy, filter policy, message attribute shape, topic type, or delivery target configuration — not necessarily the SNS topic itself.
  when_not_to_use: Designing a new SNS topic / subscription topology from scratch (use sns-topic-deployer for creation, sns-topic-public-subscription-auditor for posture review), debugging the Lambda handler code that processes the SNS message (use lambda-invocation-troubleshooter), debugging the SQS consumer worker (use sqs-dlq-operator or sqs-throughput-optimizer), investigating SES sending limits or DKIM configuration (use ses-email-deployer), or building a full fan-out pipeline (use event-driven-automator). This skill diagnoses delivery-behaviour failures; it does not redesign the pub/sub topology or fix the downstream consumer.
  activation_triggers: SNS delivery failure, SNS not delivering messages, SNS subscription confirmation pending, SNS signature verification failure, SNS HTTP endpoint 4xx 5xx, SNS Lambda subscription not invoking, SNS SQS subscription empty, SNS email bounce complaint, SNS platform endpoint disabled, SNS mobile push failure, SNS filter policy mismatch, SNS message attributes missing, SNS FIFO topic ordering, SNS cross-region delivery, SNS DLQ, troubleshoot SNS delivery
  invocation_schema: 'Input: either (a) a symptom description (topic name, subscription protocol, observed failure — endpoint receives nothing / Lambda not invoked / SQS empty / email bounced / push dropped, time window), optionally paired with the topic and subscription configuration for offline classification, OR (b) a TopicArn plus the subscription ARN / endpoint / protocol for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {HTTP_SUBSCRIPTION_CONFIRMATION, HTTP_SIGNATURE_VERIFICATION, HTTP_4XX_5XX_RETRY, LAMBDA_ASYNC_INVOCATION, LAMBDA_DLQ, SQS_MESSAGE_SIZE, SQS_REDRIVE, EMAIL_BOUNCE_COMPLAINT, PLATFORM_ENDPOINT_DISABLED, FILTER_POLICY_MISMATCH, MESSAGE_ATTRIBUTE_LOSS, FIFO_ORDERING, CROSS_REGION_DELIVERY, DLQ_MISSING, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline symptom classification):\nSymptom: \"SNS topic orders-events is publishing 200\nmessages/sec to an HTTP endpoint\nhttps://api.partner.com/webhook. The partner reports ~5% of\nmessages are never received. CloudWatch shows\nNumberOfNotificationsFailed at ~10/sec consistently.\"\nTopicArn: arn:aws:sns:us-east-1:111111111111:orders-events\nProtocol: https\nEndpoint: https://api.partner.com/webhook\nSubscription status: Confirmed (not PendingConfirmation)\nFilter policy: none\nDelivery policy: default (4 immediate retries + 3 delayed)\nCloudWatch metrics: NumberOfNotificationsPublished: 200/sec,\n  NumberOfNotificationsDelivered: 190/sec,\n  NumberOfNotificationsFailed: 10/sec"
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: SNS, delivery failure, subscription confirmation, signature verification, HTTP endpoint, Lambda subscription, SQS subscription, email bounce, platform endpoint, filter policy, message attributes, FIFO topic, cross-region, DLQ, troubleshooting
  tags: sns, appintegration, troubleshooting, delivery, subscriptions, filter-policy, fifo-topic
---

# SNS Delivery Troubleshooter

## Quick navigation

| Section | Purpose |
|---|---|
| STRICT output contract | TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION contract |
| NEVER section | Anti-patterns that produce misdiagnosis |
| Expert heuristic | HTTP retry sequence, filter-policy scope, SQS fan-out durability |
| Configuration dependency graph | What the topic reads from, what reads the topic |
| Symptom triage table | One-line per symptom: most-likely layer + first probe |
| Pre-flight gate | Subscription-state short-circuit; gather-info commands |
| Diagnostic tree (Steps 0-9) | Symptom-driven probes; each ends in ROOT_CAUSE_IDENTIFIED or pass |
| Worked examples | Two full diagnostic blocks for reference |
| Remediation guidance | Per-layer fix commands |
| AWS documentation | Canonical AWS docs by topic |

## STRICT output contract

```text
TARGET: <topic-arn and/or subscription-arn>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <HTTP_SUBSCRIPTION_CONFIRMATION | HTTP_SIGNATURE_VERIFICATION |
        HTTP_4XX_5XX_RETRY | LAMBDA_ASYNC_INVOCATION |
        LAMBDA_DLQ | SQS_MESSAGE_SIZE | SQS_REDRIVE |
        EMAIL_BOUNCE_COMPLAINT | PLATFORM_ENDPOINT_DISABLED |
        FILTER_POLICY_MISMATCH | MESSAGE_ATTRIBUTE_LOSS |
        FIFO_ORDERING | CROSS_REGION_DELIVERY | DLQ_MISSING | UNKNOWN>
EVIDENCE:
  - <observed symptom — delivery metric or operator report>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <topic-or-subscription> in
  <region>. Proceed? (yes/no)"
```

**Verdict contract:** `ROOT_CAUSE_IDENTIFIED` requires a failing probe
that matches the symptom. `INSUFFICIENT_DATA` is emitted when the
SNS-side configuration is clean and the issue is downstream in the
endpoint, consumer, or a service outside SNS's delivery path. There is
no third verdict value.

## NEVER section — anti-patterns

- **NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe that
  matches the symptom.** A process-of-elimination diagnosis erodes
  operator trust when the real cause is downstream.
- **NEVER assume an HTTP endpoint is "down" without checking
  `ConfirmationStatus` first.** A PendingConfirmation subscription
  NEVER receives messages — the endpoint never confirmed the token.
  The endpoint is fine; the subscription is not active.
- **NEVER conclude "SNS is broken" without reading
  `NumberOfNotificationsFailed`.** If zero, SNS believes it delivered
  every message; the failure is downstream. If non-zero, SNS itself
  reports delivery failures.
- **NEVER assume filter-policy mismatch produces an error.** Filter
  policies silently drop non-matching messages — no error, no metric
  spike, no DLQ entry. The only signal is `NumberOfNotificationsDelivered`
  < `NumberOfNotificationsPublished` for the subscription.
- **NEVER treat 4xx the same as 5xx.** SNS retries both (4 immediate +
  delayed by default) but 4xx is a permanent rejection after the final
  retry; 5xx is transient. A 403 needs a policy fix, not more retries.
- **NEVER assume message attributes survive an SQS fan-out
  automatically.** `RawMessageDelivery: false` propagates attributes
  (but adds envelope overhead). `RawMessageDelivery: true` passes the
  raw body but does NOT set attributes on the SQS message.
- **NEVER rely on standard-topic ordering for application semantics.**
  Standard topics deliver best-effort, often out-of-order under fan-out.
  FIFO topics deliver in order; but FIFO topics require FIFO SQS queues.
- **NEVER assume cross-region delivery is automatic.** Cross-region
  Lambda subscription needs the function resource policy to grant
  `lambda:InvokeFunction` from the SNS topic's account. Console auto-
  adds for same-region; CLI / Terraform do not.
- **NEVER ignore the SQS size cap on SNS fan-out.** SNS caps payload
  at 256 KB. With `RawMessageDelivery: false`, the JSON envelope adds
  1-4 KB overhead; a 254 KB SNS message can exceed the 256 KB SQS cap.
- **NEVER use a Lambda subscription without an OnFailure DLQ or
  destination.** Lambda async invocation retries twice then drops.
  Without a DLQ, the failed SNS message vanishes.

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

## Configuration dependency graph

```
[publisher]                    [SNS topic]
 application / step fn ──────►  (standard or FIFO,
 eventbridge fan-out  ───────►   attributes, body ≤ 256 KB)
                                       │ per-subscription delivery
                                       ▼
                              [Subscriptions]
                               HTTP/HTTPS  (needs Confirmed; 4xx=permanent; 5xx=retried)
                               Lambda      (async; needs lambda:InvokeFunction from sns.amazonaws.com)
                               SQS queue   (fan-out; needs sqs:SendMessage from SNS service)
                               email       (subject to SES bounce/complaint)
                               platform    (mobile push; needs endpoint Enabled)
                                       │ delivery result
                                       ▼
                              [CloudWatch AWS/SNS metrics]
                               NumberOfNotificationsPublished / Delivered / Failed
                               (per-topic, per-subscription dimensions)
```

A delivery failure has exactly three layers to investigate: the
subscription state (Confirmed? filter policy match?), the delivery
target (endpoint reachable? policy grants SNS invoke?), and the
downstream consumer (Lambda handler working? SQS worker polling?).

## Quick reference — symptom triage table

| Symptom phrase / observed state | Most likely layer | First probe |
|---|---|---|
| HTTP endpoint receives nothing since subscription creation | HTTP_SUBSCRIPTION_CONFIRMATION | `get-subscription-attributes` (ConfirmationStatus) |
| HTTP endpoint receives some but ~5% missing; NumberOfNotificationsFailed > 0 | HTTP_4XX_5XX_RETRY | Endpoint access logs for 4xx/5xx in the delivery window |
| HTTP endpoint reports "signature verification failed" | HTTP_SIGNATURE_VERIFICATION | Endpoint's signature validation code vs AWS cert chain |
| Lambda subscription never invokes | LAMBDA_ASYNC_INVOCATION / FILTER_POLICY_MISMATCH | `get-subscription-attributes` (FilterPolicy), Lambda CloudWatch Logs |
| Lambda invokes but ~30% fail after retries | LAMBDA_DLQ | Lambda DestinationConfig / DeadLetterConfig, Errors metric |
| SQS subscription queue empty despite publishes | FILTER_POLICY_MISMATCH / SQS_REDRIVE | `get-subscription-attributes` (FilterPolicy), SQS RedrivePolicy |
| Email recipients bounce or mark complaint | EMAIL_BOUNCE_COMPLAINT | SES bounce/complaint notifications, SNS delivery status |
| Mobile push endpoint receives nothing | PLATFORM_ENDPOINT_DISABLED | `list-endpoints-by-platform-application` (Enabled status) |
| Some messages delivered, others silently dropped | FILTER_POLICY_MISMATCH / MESSAGE_ATTRIBUTE_LOSS | Filter policy vs message attributes |
| FIFO topic: messages out of order at consumer | FIFO_ORDERING | Topic FifoTopic flag, SQS queue FifoQueue flag, MessageGroupId |
| Cross-region Lambda subscription not invoking | CROSS_REGION_DELIVERY | Lambda resource policy for cross-account / cross-region grant |
| All deliveries failing; NumberOfNotificationsFailed = NumberOfNotificationsPublished | DLQ_MISSING / endpoint-wide outage | `get-topic-attributes`, endpoint health check |

## Pre-flight: subscription state and gather-info gate

Before running symptom-specific probes, gather the canonical topic
and subscription configuration and short-circuit on subscription
states that mimic delivery failures.

### Account-wide pre-flight commands

```bash
# 1. Topic attributes (FifoTopic, policy, delivery status, KmsMasterKeyId)
aws sns get-topic-attributes --topic-arn <topic-arn> --output json

# 2. All subscriptions on the topic
aws sns list-subscriptions-by-topic --topic-arn <topic-arn> --output json

# 3. Per-subscription attributes (ConfirmationStatus, FilterPolicy,
#    DeliveryPolicy, RawMessageDelivery, SubscriptionRolePolicy)
aws sns get-subscription-attributes \
  --subscription-arn <subscription-arn> --output json

# 4. SNS delivery metrics (per-subscription dimension available)
aws cloudwatch get-metric-statistics --namespace AWS/SNS \
  --metric-name NumberOfNotificationsFailed \
  --dimensions Name=TopicName,Value=<topic-name> \
  Name=Endpoint,Value=<endpoint-url> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json

# 5. For Lambda subscriptions: Lambda errors and throttles
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=<fn> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json
```

### Subscription-state short-circuit

| `ConfirmationStatus` / pattern | Effect on diagnosis |
|---|---|
| `PendingConfirmation` | Subscription was created but the endpoint never confirmed the token. NO messages are delivered. ROOT_CAUSE_IDENTIFIED, `LAYER: HTTP_SUBSCRIPTION_CONFIRMATION`. |
| `Confirmed` but NumberOfNotificationsDelivered = 0 | Filter policy drops everything, OR the target policy denies SNS. Proceed with FILTER_POLICY_MISMATCH / target policy check. |
| `Confirmed`, NumberOfNotificationsDelivered > 0, but consumer sees nothing | SNS delivered; the failure is downstream (endpoint received but rejected, Lambda handler threw, SQS worker not polling). Not an SNS-side issue. |
| `Deleted` | Subscription no longer exists. Messages to this subscription are not even attempted. |
| NumberOfNotificationsFailed = NumberOfNotificationsPublished | Every delivery attempt fails. Endpoint-wide outage, target policy denial, or endpoint decommissioned. |

If the input is malformed (missing TopicArn, absent symptom, no
subscription configuration for live diagnosis), emit the
INSUFFICIENT_DATA block with `LAYER: UNKNOWN` listing the missing
fields and the next probe to run.

## Process — Diagnostic decision tree (apply in symptom order)

Pick the entry point based on the observed symptom, then walk the
layer-specific probes in order. Each layer ends with either a positive
root-cause confirmation (a failing probe that matches the symptom) or
a pass that moves to the next layer. **Never emit ROOT_CAUSE_IDENTIFIED
without a failing probe that matches the symptom.**

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

### Step 1: Symptom entry

| Symptom | Branch |
|---|---|
| HTTP/HTTPS endpoint receives nothing | Step 2 — HTTP delivery |
| HTTP endpoint receives partial; intermittent loss | Step 2b — HTTP retry |
| Lambda subscription not invoking or failing | Step 3 — Lambda |
| SQS subscription queue empty | Step 4 — SQS |
| Email bounce / complaint | Step 5 — Email |
| Mobile push not received | Step 6 — Platform endpoint |
| Messages silently dropped (no error) | Step 7 — Filter policy |
| Message attributes missing downstream | Step 8 — Raw message delivery |
| FIFO ordering broken | Step 9 — FIFO |
| None of the above | Step 10 — INSUFFICIENT_DATA verdict |

### Step 2: HTTP/HTTPS endpoint — subscription confirmation

```bash
aws sns get-subscription-attributes \
  --subscription-arn <subscription-arn> --output json | \
  jq '.Attributes.ConfirmationStatus'
```

If `PendingConfirmation`, ROOT_CAUSE_IDENTIFIED,
`LAYER: HTTP_SUBSCRIPTION_CONFIRMATION`. Fix: retrieve the token from
the endpoint's access logs or re-send via `aws sns subscribe`; then
call `ConfirmSubscription`. If `Confirmed`, proceed to Step 2b.

### Step 2b: HTTP/HTTPS endpoint — retry and 4xx/5xx

```bash
aws cloudwatch get-metric-statistics --namespace AWS/SNS \
  --metric-name NumberOfNotificationsFailed \
  --dimensions Name=TopicName,Value=<topic> Name=Endpoint,Value=<endpoint-url> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json
```

If NumberOfNotificationsFailed > 0, SNS reports delivery failures.
Cross-check the endpoint access logs for 4xx / 5xx:

| HTTP | SNS behaviour | Likely cause |
|---|---|---|
| 2xx | Delivered | — |
| 3xx | Followed (up to 5); loop = failure | Redirect loop |
| 4xx | Retried (4 default); then permanently dropped | Auth (401/403), rate-limited (429), decommissioned (404) |
| 5xx | Retried (4 default); then dropped | Endpoint overloaded; upstream down |
| Timeout | Retried; then dropped | Endpoint too slow; network partition |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: HTTP_4XX_5XX_RETRY`. Fix:
address the endpoint-side issue; adjust DeliveryPolicy for more retries.

### Step 2c: HTTP signature verification failure

If the endpoint reports "signature verification failed," the
validation code is using an outdated cert, wrong chain, or not handling
`SigningCertURL`. ROOT_CAUSE_IDENTIFIED,
`LAYER: HTTP_SIGNATURE_VERIFICATION`. Fix: update the code to fetch
the cert from `SigningCertURL` and verify per the SNS message spec.

### Step 3: Lambda subscription

```bash
aws sns get-subscription-attributes \
  --subscription-arn <subscription-arn> --output json | \
  jq '.Attributes | {FilterPolicy, SubscriptionRolePolicy}'

aws lambda get-policy --function-name <fn> --output json 2>/dev/null | \
  jq '.Policy | fromjson'

aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=<fn> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json
```

| Pattern | Cause |
|---|---|
| Lambda resource-based policy does not grant `lambda:InvokeFunction` to `sns.amazonaws.com` | SNS cannot invoke the function. ROOT_CAUSE_IDENTIFIED, `LAYER: LAMBDA_ASYNC_INVOCATION`. |
| Lambda Errors metric spikes at the same rate as SNS publishes | Handler throws on every invocation. The subscription works; the handler is broken. Route to `lambda-invocation-troubleshooter`. |
| Lambda Errors spike on ~30% of invocations; retried twice then dropped | No OnFailure destination or DLQ. ROOT_CAUSE_IDENTIFIED, `LAYER: LAMBDA_DLQ`. Fix: add a destination or DLQ. |
| Filter policy present; NumberOfNotificationsDelivered < NumberOfNotificationsPublished | Filter policy drops non-matching. Proceed to Step 7. |

### Step 4: SQS subscription

```bash
aws sns get-subscription-attributes \
  --subscription-arn <subscription-arn> --output json | \
  jq '.Attributes | {FilterPolicy, RawMessageDelivery}'

aws sqs get-queue-attributes --queue-url <queue-url> \
  --attribute-names Policy RedrivePolicy MaximumMessageSize \
  ApproximateNumberOfMessagesVisible --output json
```

| Pattern | Cause |
|---|---|
| Queue policy does not grant `sqs:SendMessage` to `sns.amazonaws.com` for this topic | SNS cannot enqueue. Fix: add the statement. |
| Queue `ApproximateNumberOfMessagesVisible` growing; consumer not polling | Consumer-side issue. Route to `sqs-dlq-operator` or `sqs-throughput-optimizer`. |
| Queue RedrivePolicy sending messages to a DLQ | Source queue's redrive is moving messages out. Inspect the DLQ. ROOT_CAUSE_IDENTIFIED, `LAYER: SQS_REDRIVE`. |
| SNS message + envelope > 256 KB (queue MaximumMessageSize) | MessageSize cap. ROOT_CAUSE_IDENTIFIED, `LAYER: SQS_MESSAGE_SIZE`. Fix: reduce payload, or enable `RawMessageDelivery: true` to remove envelope overhead. |

### Step 5: Email bounce / complaint

```bash
aws sns get-subscription-attributes \
  --subscription-arn <subscription-arn> --output json | jq '.Attributes'
aws ses get-send-statistics --output json
```

If SES suppresses the recipient (permanent bounce or complaint), SNS
delivery fails permanently. ROOT_CAUSE_IDENTIFIED,
`LAYER: EMAIL_BOUNCE_COMPLAINT`. Fix: remove the bounced address;
implement SES bounce/complaint handling via SNS notifications.

### Step 6: Platform endpoint (mobile push)

```bash
aws sns list-endpoints-by-platform-application \
  --platform-application-arn <app-arn> --output json | \
  jq '.Endpoints[] | {Arn, Attributes.Enabled, Attributes.Token}'
```

| Pattern | Cause |
|---|---|
| `Enabled: false` | SNS auto-disabled the endpoint after a permanent failure from APNS/FCM (token revoked, app uninstalled). ROOT_CAUSE_IDENTIFIED, `LAYER: PLATFORM_ENDPOINT_DISABLED`. Fix: re-register the device token; create a new endpoint. |
| Endpoint ARN missing | The device never registered. Fix: call `create-platform-endpoint` with the device token. |
| Endpoint Enabled but push not received | APNS/FCM credential on the platform application is expired or wrong. Check `get-platform-application-attributes`. |

### Step 7: Filter policy evaluation

```bash
aws sns get-subscription-attributes \
  --subscription-arn <subscription-arn> --output json | \
  jq '.Attributes.FilterPolicy'
```

Publish a test message with attributes that should match:

```bash
aws sns publish --topic-arn <topic-arn> \
  --message '{"event":"test"}' \
  --message-attributes '{"event":{"DataType":"String","StringValue":"order.created"}}' \
  --output json
```

If NumberOfNotificationsDelivered does not increment for the
subscription, the filter policy dropped the message.
ROOT_CAUSE_IDENTIFIED, `LAYER: FILTER_POLICY_MISMATCH`.

Common filter-policy failures:

| Filter policy | Message attribute | Match? |
|---|---|---|
| `{"event": ["order.created"]}` | `event=order.created` | Yes |
| `{"event": ["order.created"]}` | `event=order.created.v2` | No (exact; no prefix) |
| `{"event": ["order.created"]}` | (no `event` attribute) | No (attribute missing) |
| `{"event": [{"prefix": "order."}]}` | `event=order.created` | Yes (prefix) |
| `{"event": [{"exists": false}]}` | (no `event` attribute) | Yes (non-existence) |

### Step 8: Message attribute preservation

```bash
aws sns get-subscription-attributes \
  --subscription-arn <subscription-arn> --output json | \
  jq '.Attributes.RawMessageDelivery'
```

| RawMessageDelivery | SQS message attributes | SNS envelope |
|---|---|---|
| `false` (default) | Set from SNS message attributes | Yes (full JSON envelope in SQS body) |
| `true` | NOT set on SQS message | No (raw SNS message body passed through) |

If the consumer expects attributes on the SQS message but
`RawMessageDelivery: true`, the attributes are only in the body.
ROOT_CAUSE_IDENTIFIED, `LAYER: MESSAGE_ATTRIBUTE_LOSS`. Fix: either
set `RawMessageDelivery: false` (adds envelope overhead) or parse
attributes from the body in the consumer.

### Step 9: FIFO ordering

```bash
aws sns get-topic-attributes --topic-arn <topic-arn> --output json | \
  jq '.Attributes.FifoTopic'

aws sqs get-queue-attributes --queue-url <queue-url> \
  --attribute-names FifoQueue --output json
```

| Pattern | Cause |
|---|---|
| Topic `FifoTopic: true`, queue `FifoQueue: false` | Standard queue breaks ordering. ROOT_CAUSE_IDENTIFIED, `LAYER: FIFO_ORDERING`. Fix: use a `.fifo` queue. |
| FIFO topic + FIFO queue, but messages out of order within a group | Different `MessageGroupId`s deliver in parallel. Same group delivers in order. Check the publisher's MessageGroupId assignment. |
| FIFO topic + FIFO queue, consumer sees duplicates | FIFO dedup relies on `MessageDeduplicationId` or content hash. Check the publisher's dedup config. |

### Step 10: INSUFFICIENT_DATA verdict

If none of the above produced a positive root-cause match, OR the
symptom clearly indicates an AWS-side SNS service degradation (visible
in AWS Health), emit `VERDICT: INSUFFICIENT_DATA` with
`LAYER: UNKNOWN` listing the missing pieces (subscription attributes,
delivery metrics, endpoint access logs) and the next probe to run.
Recommend routing to the downstream consumer's troubleshooter
(`lambda-invocation-troubleshooter`, `sqs-dlq-operator`) if the SNS-
side configuration is clean.

## Worked examples

### Worked example — HTTP endpoint, PendingConfirmation

```text
TARGET: arn:aws:sns:us-east-1:111111111111:orders-events
  (subscription: https://api.partner.com/webhook)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Subscription ConfirmationStatus is PendingConfirmation. The
  HTTP endpoint never confirmed the SubscriptionConfirmation token.
  SNS does not deliver messages to unconfirmed HTTP/HTTPS
  subscriptions (Step 2).
LAYER: HTTP_SUBSCRIPTION_CONFIRMATION
EVIDENCE:
  - Symptom: partner reports zero messages received since the
    subscription was created 2 hours ago.
  - Probe: aws sns get-subscription-attributes returns
    ConfirmationStatus: PendingConfirmation.
  - Probe: aws cloudwatch get-metric-statistics on AWS/SNS
    NumberOfNotificationsDelivered for this TopicName + Endpoint
    returns Values: [0, 0, 0, ...].
  - Passing: the topic itself is publishing (NumberOfNotificationsPublished
    is non-zero); the Lambda subscription on the same topic is
    receiving (so the topic is not the issue).
REMEDIATION:
  1. Retrieve the SubscriptionConfirmation token from the endpoint's
     access logs (SNS sent a POST with a token when the subscription
     was created), OR re-trigger confirmation by re-subscribing:
     aws sns subscribe --topic-arn <topic> --protocol https \
       --notification-endpoint https://api.partner.com/webhook \
       --return-subscription-arn --profile <p>
  2. The endpoint must call ConfirmSubscription with the token:
     aws sns confirm-subscription --topic-arn <topic> \
       --token <token> --authenticate-on-unsubscribe true \
       --profile <p>
  3. Verify ConfirmationStatus transitions to Confirmed and
     NumberOfNotificationsDelivered increments.
CONFIRM: Before re-subscribing, emit and await:
  "CONFIRM: About to re-subscribe https://api.partner.com/webhook to
   orders-events. Proceed? (yes/no)"
```

### Worked example — filter policy silent drop

```text
TARGET: arn:aws:sns:us-east-1:111111111111:order-events
  (subscription: arn:aws:sns:us-east-1:111111111111:order-events:abc)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Subscription filter policy {"event": ["order.created"]} drops
  messages with attribute event=order.updated. Filter policies silently
  drop non-matching messages — no error, no DLQ entry (Step 7).
LAYER: FILTER_POLICY_MISMATCH
EVIDENCE:
  - Symptom: consumer reports ~40% of expected messages never arrive.
    No errors in SNS delivery metrics.
  - Probe: aws sns get-subscription-attributes returns FilterPolicy:
    {"event": ["order.created"]}.
  - Probe: NumberOfNotificationsDelivered for this subscription is
    ~60% of Published — the drop ratio matches the order.created vs
    order.updated split. Test publish with event=order.updated does
    NOT increment Delivered; event=order.created does.
  - Passing: ConfirmationStatus is Confirmed; Lambda resource policy
    grants sns.amazonaws.com lambda:InvokeFunction.
REMEDIATION:
  1. Update the filter policy to include order.updated:
     aws sns set-subscription-attributes \
       --subscription-arn <sub-arn> \
       --attribute-name FilterPolicy \
       --attribute-value '{"event": ["order.created", "order.updated"]}' \
       --profile <p>
  2. Verify by publishing event=order.updated and confirming
     NumberOfNotificationsDelivered increments.
CONFIRM: Before updating the filter policy, emit and await:
  "CONFIRM: About to add order.updated to the filter policy on
   subscription <sub-arn>. Proceed? (yes/no)"
```

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`subscribe`, `unsubscribe`, `set-subscription-attributes`,
  `confirm-subscription`, `create-platform-endpoint`,
  `set-endpoint-attributes`), emit and await operator approval.
  Include the diff (old vs new value) in the prompt.
- **Read-only first.** Every diagnostic probe is read-only
  (`get-topic-attributes`, `list-subscriptions-by-topic`,
  `get-subscription-attributes`, `get-metric-statistics`,
  `get-policy`, `get-queue-attributes`,
  `list-endpoints-by-platform-application`, `get-send-statistics`).
- **`set-subscription-attributes`** with `FilterPolicy` or
  `RawMessageDelivery` changes delivery immediately. Include the diff
  in the CONFIRM prompt.
- **`subscribe`** to an existing endpoint creates a NEW subscription;
  duplicates each receive every message. Verify no existing
  subscription before re-subscribing.
- **`unsubscribe`** is irreversible. Prefer pausing via filter policy
  `{"drop": [{"exists": true}]}` if the intent is temporary.
- **Platform endpoint re-registration** creates a new endpoint ARN;
  clean up the old disabled endpoint via `delete-endpoint`.
- **Bulk remediation batch limit.** Batch same-root-cause remediation
  across multiple subscriptions into groups of at most 5; emit a
  single CONFIRM per batch; verify between batches.

## Remediation guidance

Every remediation uses `set-subscription-attributes` for per-
subscription changes, `subscribe` / `confirm-subscription` for HTTP
lifecycle, or a target-side policy command for permission-layer fixes.
Always emit CONFIRM before executing; include the diff in the prompt.

### HTTP_SUBSCRIPTION_CONFIRMATION

```bash
aws sns subscribe --topic-arn <topic> --protocol https \
  --notification-endpoint <endpoint> --return-subscription-arn --profile <p>
aws sns confirm-subscription --topic-arn <topic> --token <token> \
  --authenticate-on-unsubscribe true --profile <p>
```

### HTTP_4XX_5XX_RETRY

Address the endpoint-side issue (scale, refresh auth, raise rate
limit). Adjust the subscription delivery policy for more retries:

```bash
aws sns set-subscription-attributes --subscription-arn <sub-arn> \
  --attribute-name DeliveryPolicy \
  --attribute-value '{"healthyRetryPolicy":{"numRetries":5,"minDelayTarget":1,"maxDelayTarget":60}}' \
  --profile <p>
```

### HTTP_SIGNATURE_VERIFICATION

No SNS-side fix. Update the endpoint's validation code to fetch the
cert from `SigningCertURL` and verify per the AWS SNS message spec.

### LAMBDA_ASYNC_INVOCATION

```bash
aws lambda add-permission --function-name <fn> \
  --statement-id AllowSNSInvoke \
  --action lambda:InvokeFunction \
  --principal sns.amazonaws.com \
  --source-arn <topic-arn> --profile <p>
```

### LAMBDA_DLQ

```bash
aws lambda put-function-event-invoke-config --function-name <fn> \
  --destination-config '{"OnFailure":{"Destination":"<sns-or-sqs-arn>"}}' \
  --profile <p>
```
Route to `lambda-invocation-troubleshooter` if the handler is throwing.

### SQS_MESSAGE_SIZE / SQS_REDRIVE

```bash
# Remove envelope overhead
aws sns set-subscription-attributes --subscription-arn <sub-arn> \
  --attribute-name RawMessageDelivery --attribute-value true --profile <p>
```
For SQS_REDRIVE: inspect the source queue's RedrivePolicy; adjust
`maxReceiveCount` or fix the consumer so messages don't exhaust
retries.

### EMAIL_BOUNCE_COMPLAINT

Remove the bounced address from the subscription; implement SES
bounce/complaint handling via a separate SNS topic.

### PLATFORM_ENDPOINT_DISABLED

```bash
aws sns create-platform-endpoint --platform-application-arn <app-arn> \
  --token <device-token> --profile <p>
aws sns delete-endpoint --endpoint-arn <old-endpoint-arn> --profile <p>
```

### FILTER_POLICY_MISMATCH / MESSAGE_ATTRIBUTE_LOSS

```bash
aws sns set-subscription-attributes --subscription-arn <sub-arn> \
  --attribute-name FilterPolicy \
  --attribute-value '<corrected-json>' --profile <p>
```
Verify the corrected policy against the publisher's actual message
attributes. Use `prefix`, `anything-but`, `exists` for flexible
matching. For MESSAGE_ATTRIBUTE_LOSS: set `RawMessageDelivery: false`
to propagate attributes, OR parse from the body in the consumer.

### FIFO_ORDERING / CROSS_REGION_DELIVERY / DLQ_MISSING

- FIFO_ORDERING: use a `.fifo` queue; ensure publisher assigns
  `MessageGroupId` correctly.
- CROSS_REGION_DELIVERY: `aws lambda add-permission --function-name <fn>
  --principal sns.amazonaws.com --source-arn <topic-arn> ...`.
- DLQ_MISSING: configure SNS subscription DLQ via
  `set-subscription-attributes RedrivePolicy`, OR Lambda OnFailure
  destinations for Lambda subscriptions.

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

## Domain

AWS CloudOps / SNS Pub-Sub Messaging, Subscription Lifecycle, Delivery Retry, Filter Policy Evaluation, Fan-Out Durability.

## AWS documentation

- **SNS Developer Guide** — https://docs.aws.amazon.com/sns/latest/dg/sns-getting-started.html
- **Subscription filter policies** — https://docs.aws.amazon.com/sns/latest/dg/sns-subscription-filter-policies.html
- **HTTP/HTTPS delivery and signature** — https://docs.aws.amazon.com/sns/latest/dg/SendMessageToHttp.html
- **SNS message attributes** — https://docs.aws.amazon.com/sns/latest/dg/sns-message-attributes.html
- **SNS FIFO topics** — https://docs.aws.amazon.com/sns/latest/dg/fifo-topics.html
- **Delivery status logging** — https://docs.aws.amazon.com/sns/latest/dg/sns-topic-attributes.html#message-delivery-status
- **SNS CloudWatch metrics** — https://docs.aws.amazon.com/sns/latest/dg/sns-monitoring.html
- **SNS dead-letter queues** — https://docs.aws.amazon.com/sns/latest/dg/sns-dead-letter-queues.html
- **Mobile push notifications** — https://docs.aws.amazon.com/sns/latest/dg/sns-mobile-application-as-subscriber.html
