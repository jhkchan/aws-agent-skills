---
description: Diagnose SNS delivery failures through a twelve-category (HTTP subscription confirmation, signature verification, 4xx/5xx retry, Lambda async invocation, SQS message size / redrive, email bounce, platform endpoint, filter policy, message attributes, FIFO ordering, cross-region) diagnostic tree — emits ROOT_CAUSE_IDENTIFIED with the specific failure layer or INSUFFICIENT_DATA.
nl_triggers:
  - "SNS delivery failure"
  - "SNS not delivering messages"
  - "SNS subscription confirmation pending"
  - "SNS signature verification failure"
  - "SNS HTTP endpoint 4xx 5xx"
  - "SNS Lambda subscription not invoking"
  - "SNS SQS subscription empty"
  - "SNS email bounce complaint"
  - "SNS platform endpoint disabled"
  - "SNS mobile push failure"
  - "SNS filter policy mismatch"
  - "SNS message attributes missing"
  - "SNS FIFO topic ordering"
  - "SNS cross-region delivery"
  - "SNS DLQ"
  - "troubleshoot SNS delivery"
  - "diagnose SNS topic delivery"
  - "SNS subscription not receiving"
routes_to: sns-delivery-troubleshooter
---

# /aws:troubleshoot-sns-delivery

Activate the `sns-delivery-troubleshooter` skill and diagnose an AWS
SNS delivery failure through the twelve-category diagnostic tree.

## What it does

Reads a symptom description (topic name, subscription protocol,
observed failure — endpoint receives nothing / Lambda not invoked /
SQS empty / email bounced / push dropped) plus the subscription
configuration, then walks the symptom-driven diagnostic tree to a
root cause with positive evidence:

1. **Pre-flight** — topic and subscription state
   (`get-topic-attributes`, `list-subscriptions-by-topic`,
   `get-subscription-attributes`), SNS delivery metrics
   (`NumberOfNotificationsDelivered`, `NumberOfNotificationsFailed`),
   Lambda errors, SQS queue depth. Short-circuits on
   `PendingConfirmation`, `Enabled: false` platform endpoints, and
   delivery-accounting gaps (Delivered + Failed < Published =
   filter-policy drop).
2. **Symptom entry** — map the symptom to one of: HTTP subscription
   confirmation, HTTP 4xx/5xx retry, HTTP signature verification,
   Lambda async invocation / DLQ, SQS message size / redrive, email
   bounce/complaint, platform endpoint disabled, filter policy
   mismatch, message attribute loss, FIFO ordering, cross-region
   delivery.
3. **Layer-specific probes** —
   - HTTP: `get-subscription-attributes` (ConfirmationStatus),
     endpoint access logs for 4xx/5xx in the delivery window,
     signature validation code review.
   - Lambda: `get-subscription-attributes` (FilterPolicy),
     `get-policy` on the function (resource-based policy),
     `get-metric-statistics` on AWS/Lambda Errors and Invocations.
   - SQS: `get-subscription-attributes` (FilterPolicy,
     RawMessageDelivery), `get-queue-attributes` (Policy,
     RedrivePolicy, MaximumMessageSize, ApproximateNumberOfMessagesVisible).
   - Email: `get-send-statistics` for bounce/complaint rates.
   - Platform endpoint: `list-endpoints-by-platform-application`
     (Enabled status).
   - Filter policy: `get-subscription-attributes` (FilterPolicy),
     test publish with specific attributes.
   - FIFO: `get-topic-attributes` (FifoTopic),
     `get-queue-attributes` (FifoQueue), MessageGroupId.
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with failing probe that
   matches the symptom) or INSUFFICIENT_DATA (SNS-side config is
   clean; issue is downstream in the endpoint, consumer, or a service
   outside SNS's delivery path).

Emits a deterministic diagnostic block per target:

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
```

## When to invoke

Paste a symptom description and ask any of:

- "SNS not delivering to HTTP endpoint"
- "SNS Lambda subscription not invoking"
- "SNS SQS subscription queue empty"
- "SNS filter policy dropping messages"
- "SNS email bounce rate high"
- "SNS mobile push not received"
- "SNS message attributes missing on SQS"
- "SNS FIFO ordering broken"
- "SNS cross-region Lambda subscription"
- "SNS delivery failures spiking"

A bare topic name + any delivery verb ("SNS is not delivering", "SNS
subscription failing", "messages not arriving") also routes here via
the orchestrator.

## Inputs

- Symptom description: topic ARN, subscription protocol, observed
  failure pattern (nothing / partial / intermittent / all failing),
  time window.
- Subscription configuration: TopicArn, Protocol, Endpoint,
  ConfirmationStatus, FilterPolicy, RawMessageDelivery,
  DeliveryPolicy, SubscriptionRolePolicy.
- For live-account diagnosis: `get-topic-attributes` output,
  `list-subscriptions-by-topic` output, per-subscription
  `get-subscription-attributes`, CloudWatch AWS/SNS delivery metrics
  (NumberOfNotificationsDelivered / Failed per subscription),
  endpoint access logs, Lambda resource-based policy, SQS queue
  attributes.

## Outputs

- One diagnostic block per target subscription.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: subscribe / confirm-subscription,
  set-subscription-attributes (FilterPolicy, RawMessageDelivery,
  DeliveryPolicy, RedrivePolicy), Lambda add-permission, Lambda
  put-function-event-invoke-config (OnFailure destination), SQS
  queue policy fix, platform endpoint re-registration, or routing to
  the downstream consumer's troubleshooter.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for SNS delivery failures).
- `/aws:troubleshoot-lambda-invocation` for deeper diagnosis when the
  SNS-to-Lambda subscription invokes but the handler throws or times
  out.
- `/aws:operate-sqs-dlq` for deeper diagnosis when the SQS
  subscription's DLQ fills or messages are redriving unexpectedly.
- `/aws:audit-sns-topic-public-subscription` for posture review on
  the same topic (public subscription exposure, policy audit).
- `/aws:deploy-sns-topic` for creating or updating the SNS topic and
  subscription topology.
