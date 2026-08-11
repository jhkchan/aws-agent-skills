---
description: >-
  Operate AWS SNS subscription operations — create subscriptions
  (HTTP/HTTPS/SQS/Lambda/email/sms/firehose), confirm pending
  subscriptions, set filter policies, configure delivery retry and
  dead-letter queue (DLQ), set subscription attributes
  (RawMessageDelivery), diagnose non-delivery — with deterministic
  pre-checks, CONFIRM gate, and post-verification.
nl_triggers:
  - "create SNS subscription"
  - "confirm SNS subscription"
  - "PendingConfirmation"
  - "SNS filter policy"
  - "SNS delivery policy"
  - "SNS dead-letter queue"
  - "SNS subscription redrive"
  - "SNS retry backoff"
  - "RawMessageDelivery"
  - "subscribe to SNS topic"
  - "SNS subscription not receiving messages"
  - "SNS message data protection"
  - "cross-account SNS subscription"
  - "SNS firehose subscription"
  - "get-subscription-attributes"
routes_to: sns-subscription-operator
---

# /aws:operate-sns-subscription

Activate the `sns-subscription-operator` skill and plan/execute an SNS
subscription operation with deterministic pre-checks, CONFIRM gate, and
post-verification.

## What it does

Reads an SNS subscription configuration (topic ARN, protocol, endpoint,
filter policy, delivery policy, subscription attributes) plus the
intended operation and applies the priority-ordered pre-check sequence:

1. Pre-flight subscription metadata gate — short-circuit missing topics,
   invalid protocols, malformed endpoints, and confirmation-state
   mismatches.
2. Pre-check gate — BLOCKED if any check fails (topic policy denies
   subscription, queue/Lambda policy missing for the endpoint, filter-
   policy JSON invalid, DLQ target missing for redrive, cross-account
   without permission).
3. READY — emit the exact CLI sequence (`subscribe`, `confirm-
   subscription`, `set-subscription-attributes`), the expected
   confirmation flow, and the CONFIRM gate prompt.
4. Execute behind CONFIRM gate — capture pre-state, execute the CLI,
   verify CloudTrail logs the event.
5. Post-verification — `get-subscription-attributes` matches intent,
   test message delivered to the endpoint, DLQ policy valid. COMPLETED
   only if ALL post-verification checks pass.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <create | confirm | set-filter-policy | set-delivery-policy | set-redrive-policy | set-attributes | delete | diagnose>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <topic-arn> (subscription: <sub-arn>, protocol: <protocol>, endpoint: <endpoint>)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <verification command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <confirmation flow, filter-policy match, retry config, DLQ>
```

## When to invoke

Paste an SNS subscription configuration plus the intended operation,
or just describe the scenario and ask any of:

- "subscribe my SQS queue to this topic"
- "this HTTP subscription is pending confirmation — help me confirm"
- "my subscription isn't receiving messages — diagnose why"
- "set a filter policy on my subscription for order events"
- "configure retry and DLQ on my HTTPS webhook subscription"
- "enable raw message delivery on my SQS subscription"
- "cross-account subscription is failing with AuthorizationError"
- "subscribe a Firehose delivery stream to my topic"
- "is SNS message data protection blocking my messages?"

A bare topic ARN + any subscription verb also routes here via the
orchestrator.

## Inputs

- Topic ARN and topic attributes (`get-topic-attributes`): owner,
  policy (does it allow `sns:Subscribe` for the caller?).
- Subscription attributes (`get-subscription-attributes`):
  `PendingConfirmation`, `FilterPolicy`, `FilterPolicyScope`,
  `RawMessageDelivery`, `DeliveryPolicy`, `RedrivePolicy`.
- For SQS endpoints: queue attributes (`get-queue-attributes`) —
  does the queue policy allow `sqs:SendMessage` from the topic ARN?
- For Lambda endpoints: Lambda policy (`get-policy`) — does the
  function allow `lambda:InvokeFunction` from the topic ARN?
- For Firehose endpoints: delivery stream status
  (`describe-delivery-stream`) — is the stream `ACTIVE`?
- For HTTP/HTTPS endpoints: endpoint reachability (returns 200 for
  SNS POST?).
- For DLQ (redrive): DLQ SQS ARN and queue policy.
- CloudTrail `Subscribe` / `ConfirmSubscription` /
  `SetSubscriptionAttributes` events.

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for
  failure.
- For READY: the exact CLI command(s), the expected confirmation flow
  (auto-confirm for SQS/Lambda/firehose owned by caller; token-based
  for HTTP/HTTPS/email/sms), and the CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, including
  `get-subscription-attributes` matching intent and a test message
  delivered.
- For BLOCKED: the specific failure reason and the remediation step
  (e.g., add `sns:Subscribe` to the topic policy, add `sqs:SendMessage`
  to the queue policy, fix the filter-policy attribute names).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Operate specialist for SNS subscription operations).
- `/aws:deploy-sns-topic` for the topic-side counterpart — creating
  and configuring the SNS topic itself.
- `/aws:audit-sns-topic-public-subscription` for the audit-side
  counterpart — detecting publicly accessible subscriptions across
  many topics without changing state.
