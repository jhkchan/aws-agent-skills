---
name: sns-subscription-operator
description: >-
  Operates AWS SNS subscription workflows end-to-end — subscription
  creation (HTTP/HTTPS/SQS/Lambda/email/sms/firehose), subscription
  confirmation (PendingConfirmation to Confirmed via token or
  auto-confirm for SQS/Lambda), filter-policy design (message
  attributes, FilterPolicyScope), delivery policies (retry backoff,
  dead-letter queue via redrive), subscription attributes
  (RawMessageDelivery), and diagnostic loops
  (list-subscriptions-by-topic, get-subscription-attributes,
  CloudTrail events). Runs deterministic pre-checks (topic exists,
  endpoint reachable, topic policy permits subscription, protocol
  valid, filter-policy JSON valid, DLQ target exists for redrive)
  behind a CONFIRM gate and emits a READY, BLOCKED, or COMPLETED
  verdict per operation. Use when creating subscriptions, confirming
  pending subscriptions, debugging filter-policy matches, configuring
  delivery retry and DLQ, or diagnosing why messages are not
  delivered.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). No AWS CLI required for offline plan classification.
  Live-account operations use aws sns subscribe, confirm-subscription,
  list-subscriptions-by-topic, get-subscription-attributes,
  set-subscription-attributes, unsubscribe, aws sqs
  get-queue-attributes / set-queue-attributes (for SQS-backed
  subscriptions and DLQ), aws lambda get-policy (for Lambda-backed
  subscriptions), aws firehose describe-delivery-stream (for firehose
  targets), and aws cloudtrail lookup-events (AWS CLI v2, SSO or
  key-based credentials).
keywords:
  - SNS
  - subscription
  - PendingConfirmation
  - ConfirmSubscription
  - filter policy
  - FilterPolicyScope
  - message attributes
  - delivery policy
  - retry backoff
  - dead-letter queue
  - DLQ
  - redrive policy
  - RawMessageDelivery
  - HTTP subscription
  - HTTPS subscription
  - SQS subscription
  - Lambda subscription
  - email subscription
  - firehose subscription
  - subscription attributes
  - SNS message data protection
  - cross-account subscription
keywords_tags:
  - aws
  - sns
  - app-integration
  - subscription
  - messaging
  - operate
tags: [aws, sns, app-integration, subscription, messaging, filter-policy, delivery-policy, operate]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: AppIntegration
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY | BLOCKED | COMPLETED"
  when_to_use: >-
    Creating an SNS subscription to a topic (HTTP/HTTPS/SQS/Lambda/
    email/sms/firehose/application), confirming a subscription stuck
    in PendingConfirmation, designing or debugging a subscription
    filter policy, configuring delivery retry policy and dead-letter
    queue (DLQ), setting subscription attributes (RawMessageDelivery),
    diagnosing why messages are not delivered to a subscription, or
    validating SNS message data protection posture for a subscription.
  activation_triggers:
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
  invocation_schema: >-
    Input: either (a) an SNS subscription configuration (topic ARN,
    protocol, endpoint, filter policy, delivery policy, subscription
    attributes) plus the intended operation (create, confirm,
    set-filter-policy, set-delivery-policy, set-attributes, delete,
    diagnose), OR (b) a subscription ARN + operation for live-account
    execution. Output: deterministic OPERATION / VERDICT / TARGET /
    PRE_CHECKS / STEPS / POST_VERIFY / NOTES block per operation,
    where VERDICT is one of READY, BLOCKED, COMPLETED.
---

# SNS Subscription Operator

## What this skill does

Executes SNS subscription operations correctly and safely. Runs
deterministic pre-checks before any state-changing CLI (topic exists,
endpoint reachable, topic policy permits subscription, protocol valid,
filter-policy JSON valid, DLQ target exists for redrive), executes the
`subscribe` / `confirm-subscription` / `set-subscription-attributes`
CLI behind a CONFIRM gate, and verifies the result by confirming
`get-subscription-attributes` returns the expected state and the
endpoint receives a test message. Every create-subscription produces a
confirmation-flow note (HTTP/HTTPS/email require token-based
confirmation; SQS/Lambda can be auto-confirmed if the caller owns the
endpoint). Every filter-policy plan includes a message-attribute match
simulation. Every delivery-policy plan includes the retry math and DLQ
target verification.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds (BLOCKED/READY/COMPLETED) + protocol matrix | Before any operation |
| **§ Expert heuristic** | Non-obvious rules (confirmation flow, filter-policy scope, RawMessageDelivery, redrive) | Understanding the delivery model |
| **§ Pre-flight** | Subscription metadata gate — topic exists, endpoint reachable, policy, protocol | Before executing any CLI |
| **§ Process** | Per-operation planning: create, confirm, set-filter, set-delivery, set-attributes, delete, diagnose | When choosing which operation |
| **§ STRICT output contract** | Structured OPERATION/VERDICT/TARGET/PRE_CHECKS/STEPS/POST_VERIFY/NOTES template | Formatting the response |
| **§ Anti-Patterns** | Top-5 NEVER list — common mistakes that break delivery or strand messages | Review before risky operations |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (topic does not exist, endpoint unreachable, topic policy denies subscription, invalid protocol, malformed filter-policy JSON, DLQ target does not exist for redrive, cross-account without permission) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Operation finished and post-verification passed (`get-subscription-attributes` matches intent, test message delivered or CloudTrail event present, DLQ policy valid) | Emit verification results, monitoring plan |

**Protocol matrix — confirmation requirements and capabilities:**

| Protocol | Endpoint format | Confirmation required? | RawMessageDelivery | Filter policy | Delivery policy | DLQ (redrive) |
|---|---|---|---|---|---|---|
| `sqs` | SQS queue ARN | No (auto-confirmed if caller owns queue) | Yes (recommended) | Yes | Yes | Yes (via subscription redrive) |
| `lambda` | Lambda function ARN | No (auto-confirmed if caller owns function) | Yes | Yes | Yes | Yes |
| `https` | HTTPS URL | Yes (token from POST) | Yes | Yes | Yes | Yes |
| `http` | HTTP URL | Yes (token from POST) | Yes | Yes | Yes | Yes |
| `email` | Email address | Yes (token from email) | N/A | Yes | No | No |
| `email-json` | Email address | Yes (token from email) | N/A | Yes | No | No |
| `sms` | Phone number (E.164) | Yes (token from SMS) | N/A | Yes | No | No |
| `firehose` | Firehose ARN | No (auto-confirmed if caller owns stream) | Yes | Yes | Yes | Yes |
| `application` | Platform endpoint ARN (mobile push) | Yes (token from push) | N/A | Yes | Yes | Yes |

**Priority order for pre-checks (apply in this sequence, all must pass
for READY):**

1. **Topic reachability** — topic ARN exists (`list-topics` /
   `get-topic-attributes` does not return `NotFound`).
2. **Protocol validity** — protocol is one of `sqs`, `lambda`, `https`,
   `http`, `email`, `email-json`, `sms`, `firehose`, `application`.
3. **Endpoint format** — endpoint matches the protocol's expected
   format (SQS ARN for sqs, Lambda ARN for lambda, URL for http/https,
   email for email, E.164 phone for sms, Firehose ARN for firehose).
4. **Topic policy permission** — the topic's resource-based policy
   allows `sns:Subscribe` for the caller's account/role. Cross-account
   subscriptions require both sides.
5. **Filter-policy JSON validity** — if a filter policy is specified,
   the JSON is valid and within the 30 KB limit (SNS enforces a max
   filter-policy size).
6. **DLQ target exists** — if a delivery policy includes a redrive
   policy (DLQ), the DLQ ARN exists and the topic has permission to
   deliver to it.
7. **Confirmation flow clarity** — for HTTP/HTTPS/email/sms, the
   operator understands that confirmation is a separate step requiring
   token extraction. For SQS/Lambda/firehose, confirmation is
   automatic if the caller owns the endpoint.

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

## Pre-flight: subscription metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `list-subscriptions-by-topic` paginates at 100/page —
drain `--next-token` to completion. `list-topics` paginates at 100/page.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws sns get-topic-attributes --topic-arn <arn>` — confirm topic
   exists, capture the topic policy (`Policy` attribute), and the
   topic owner account.
2. `aws sns list-subscriptions-by-topic --topic-arn <arn>` — capture
   existing subscriptions, their `SubscriptionArn`, `Protocol`,
   `Endpoint`, and `PendingConfirmation` status.
3. For SQS endpoints: `aws sqs get-queue-attributes --queue-url <url>
   --attribute-names Policy` — verify the queue policy allows
   `sqs:SendMessage` from the SNS topic ARN.
4. For Lambda endpoints: `aws lambda get-policy --function-name <name>`
   — verify the Lambda resource policy allows
   `lambda:InvokeFunction` from the SNS topic ARN.
5. For Firehose endpoints: `aws firehose describe-delivery-stream
   --delivery-stream-name <name>` — verify the stream is `ACTIVE`.
6. For HTTP/HTTPS endpoints: verify the endpoint is reachable and
   returns a 2xx for a HEAD request. SNS requires the endpoint to
   return 200 for the confirmation POST.
7. For filter policies: validate the JSON is well-formed and within
   the 30 KB size limit.
8. For DLQ (redrive): verify the DLQ SQS ARN exists and the queue
   policy allows `sqs:SendMessage` from the SNS topic ARN.

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Subscription configuration
is not valid JSON or is missing required fields — cannot plan.` and
`REMEDIATION: Re-fetch with aws sns list-subscriptions-by-topic
--topic-arn <arn> --output json and re-plan.`

| Subscription attribute | Effect on operation |
|---|---|
| `PendingConfirmation: true` | Subscription not yet confirmed. For HTTP/HTTPS/email/sms, extract the token and confirm. For SQS/Lambda/firehose cross-account, the endpoint owner must confirm. |
| `PendingConfirmation: false` + valid `SubscriptionArn` | Subscription confirmed and active. |
| `FilterPolicy` set | Messages without matching attributes are NOT delivered. Verify the filter matches the publisher's message attributes. |
| `FilterPolicyScope: MessageBody` | Filter policy matches on message body (must be valid JSON). Default is `MessageAttributes`. |
| `RawMessageDelivery: true` | Endpoint receives only the `Message` field, not the full SNS envelope. Required for SQS-to-Lambda triggers. |
| `DeliveryPolicy` set | Per-subscription retry and backoff. Overrides the topic-level delivery policy. |
| `RedrivePolicy` set (DLQ) | Failed deliveries go to the specified SQS DLQ after retries are exhausted. |
| Topic is FIFO (`*.fifo`) | Subscription must use SQS FIFO queue as endpoint. HTTP/HTTPS/Lambda/email are NOT supported for FIFO topics. |
| Cross-account topic | Topic policy must allow `sns:Subscribe` for the subscriber's account. Endpoint owner confirms if required. |

## Process — operation planning (apply in order)

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

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL pre-checks for the chosen operation. If ANY fails, the verdict
is BLOCKED with the failed checks in PRE_CHECKS. Do NOT execute.

**For ALL operations:**
1. Topic ARN exists (`get-topic-attributes` does not return `NotFound`).
2. Topic is not being deleted (topic `DisplayName` and `Owner` are
   present).
3. Calling identity has `sns:ListSubscriptionsByTopic` and
   `sns:GetSubscriptionAttributes` on the topic ARN.

**For create-subscription (`subscribe --topic-arn --protocol
--notification-endpoint`):**
4. Protocol is valid (`sqs`, `lambda`, `https`, `http`, `email`,
   `email-json`, `sms`, `firehose`, `application`).
5. Endpoint matches protocol format (ARN for sqs/lambda/firehose, URL
   for http/https, email address for email, E.164 phone for sms).
6. Topic policy allows `sns:Subscribe` for the caller (identity-based
   OR resource-based).
7. For SQS endpoint: queue policy allows `sqs:SendMessage` from the
   topic ARN.
8. For Lambda endpoint: Lambda resource policy allows
   `lambda:InvokeFunction` from the topic ARN.
9. For Firehose endpoint: delivery stream is `ACTIVE`.
10. For FIFO topic: endpoint is an SQS FIFO queue.
11. If filter policy specified: JSON is valid, within 30 KB limit.
12. If return-subscription-arn is set: caller owns the topic OR topic
    policy allows the caller to subscribe.

**For confirm-subscription (`confirm-subscription --topic-arn
--token`):**
4. Token is valid (not expired — tokens are valid for 3 days).
5. Subscription is still `pending confirmation` (not already confirmed
   or deleted).

**For set-filter-policy (`set-subscription-attributes --attribute-name
FilterPolicy`):**
4. Subscription ARN is confirmed (not `pending confirmation`).
5. Filter policy JSON is valid and within 30 KB.
6. (Optional) The publisher's message attributes match the filter —
   run a simulation to avoid silent non-delivery.

**For set-delivery-policy (`set-subscription-attributes --attribute-name
DeliveryPolicy`):**
4. Subscription ARN is confirmed.
5. Delivery policy JSON is valid (retry count, backoff, delay within
   SNS limits).

**For set-redrive-policy / set-dlq (`set-subscription-attributes
--attribute-name RedrivePolicy`):**
4. Subscription ARN is confirmed.
5. DLQ SQS ARN exists (`get-queue-attributes` does not return
   `QueueDoesNotExist`).
6. DLQ queue policy allows `sqs:SendMessage` from the SNS topic ARN
   (or the SNS service principal).
7. DLQ is NOT the same queue as the subscription endpoint (creates a
   loop).

**For diagnose-subscription (read-only):**
4. Read `get-subscription-attributes`, CloudTrail events, and the
   failure-mode table to identify why messages are not delivered.

**Subscription failure-mode table (use during diagnose):**

| Symptom | Root cause | Fix |
|---|---|---|
| `get-subscription-attributes` shows `PendingConfirmation: true` | HTTP/HTTPS/email/sms subscription not confirmed | Extract the token from the confirmation message and call `confirm-subscription` |
| Subscription confirmed but no messages received | Filter policy does not match publisher's message attributes | Verify message attributes match the filter policy; use `FilterPolicyScope` correctly |
| Subscription confirmed but no messages received (no filter policy) | Topic message data protection policy denying messages | Check topic `getDataProtectionPolicy`; the policy may audit, mask, or deny messages |
| SQS endpoint not receiving messages | Queue policy does not allow `sqs:SendMessage` from the topic ARN | Add `sqs:SendMessage` permission for the topic ARN to the queue policy |
| Lambda endpoint not invoked | Lambda resource policy does not allow `lambda:InvokeFunction` from the topic ARN | Add `lambda:InvokeFunction` permission for the topic ARN (or re-add the trigger via the console) |
| HTTP endpoint returns 4xx/5xx | Endpoint is not handling SNS POST correctly (must return 200) | Verify the endpoint returns 200 for SNS POST; check for certificate issues on HTTPS |
| Messages go to DLQ immediately | Delivery policy retries exhausted (endpoint consistently failing) | Fix the endpoint first, then replay from DLQ |
| `subscribe` returns `AuthorizationError` | Topic policy denies caller `sns:Subscribe` | Add `sns:Subscribe` to the topic policy for the caller's account |
| `subscribe` cross-account fails | Endpoint owner has not confirmed OR topic policy does not allow cross-account subscription | Both sides must have permission; confirm with `confirm-subscription` if needed |
| FIFO topic subscription fails with `InvalidParameter` | Endpoint is not an SQS FIFO queue | Use an SQS FIFO queue (`.fifo` suffix) for FIFO topic subscriptions |

### Step 2: READY — emit operation plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI
sequence and the CONFIRM gate. The plan includes:

- The exact AWS CLI command with all flags populated.
- The expected confirmation flow (auto-confirmed for SQS/Lambda/firehose
  owned by caller; token-based for HTTP/HTTPS/email/sms).
- The expected side-effects (subscription created, filter policy applied,
  delivery policy set, DLQ configured).
- The CONFIRM gate prompt.
- The verification step (`get-subscription-attributes` + test message
  or CloudTrail event).

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`subscribe`, `confirm-subscription`, `set-subscription-attributes`,
  `unsubscribe`), emit: `CONFIRM: About to <operation> on SNS topic
  <topic-arn> (subscription <sub-arn-or-"new">). This will
  <consequence>. Proceed? (yes/no)`. Do NOT execute until the operator
  confirms.
- Capture pre-state for rollback: `aws sns
  get-subscription-attributes --subscription-arn <arn> --output json >
  /tmp/<sub-arn>-pre-$(date +%s).json`.
- Execute the CLI. `subscribe` returns immediately; for HTTP/HTTPS/
  email/sms, the confirmation step follows.

### Step 4: Post-verification — COMPLETED

After the CLI completes, run post-verification. ALL checks must pass
for `COMPLETED`.

1. `get-subscription-attributes --subscription-arn <arn>` — confirm
   the attribute matches intent (FilterPolicy, DeliveryPolicy,
   RedrivePolicy, RawMessageDelivery).
2. For create-subscription: confirm `PendingConfirmation: false` and a
   valid `SubscriptionArn` (not `"pending confirmation"`).
3. For filter-policy changes: publish a test message with the expected
   attributes and confirm the endpoint receives it.
4. For DLQ: publish a message that fails delivery (e.g., endpoint
   down) and confirm the message lands in the DLQ after retries.
5. CloudTrail shows the `Subscribe` / `ConfirmSubscription` /
   `SetSubscriptionAttributes` event with the topic ARN and caller.
6. Spot-check: the endpoint (SQS queue, Lambda function, HTTP server)
   receives a test message published to the topic.

If ANY verification fails, emit `VERDICT: ERROR` with the failure
details — do not claim COMPLETED.

## STRICT output contract (per operation)

```text
OPERATION: <create | confirm | set-filter-policy | set-delivery-policy | set-redrive-policy | set-attributes | delete | diagnose>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <topic-arn> (subscription: <sub-arn-or-"new">, protocol: <protocol>, endpoint: <endpoint-or-"masked">, account <account>, region <region>)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait / monitoring command>
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <confirmation flow, filter-policy match, retry config, DLQ, caveats>
```

### Worked example — create SQS subscription with filter policy

```text
OPERATION: create
VERDICT: READY
TARGET: arn:aws:sns:us-east-1:111111111111:order-events (subscription:
        new, protocol: sqs, endpoint:
        arn:aws:sqs:us-east-1:111111111111:order-processing-queue,
        account 111111111111, region us-east-1)
PRE_CHECKS:
  - [PASS] Topic exists (arn:aws:sns:us-east-1:111111111111:order-events)
  - [PASS] Protocol sqs valid
  - [PASS] Endpoint is a valid SQS ARN
  - [PASS] Topic policy allows sns:Subscribe for caller account
  - [PASS] Queue policy allows sqs:SendMessage from topic ARN
  - [PASS] Filter policy JSON valid ({"event_type": ["order_created",
    "order_updated"]}, 48 bytes < 30 KB limit)
  - [PASS] Caller owns the SQS queue (auto-confirmation applies)
STEPS:
  1. CONFIRM: About to create an SNS subscription on topic
     arn:aws:sns:us-east-1:111111111111:order-events, protocol sqs,
     endpoint arn:aws:sqs:us-east-1:111111111111:order-processing-queue.
     Filter policy: {"event_type": ["order_created", "order_updated"]}.
     RawMessageDelivery: true. Auto-confirmation applies (caller owns
     the queue). Proceed? (yes/no)
  2. aws sns subscribe \
       --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
       --protocol sqs \
       --notification-endpoint arn:aws:sqs:us-east-1:111111111111:order-processing-queue \
       --attributes file://attrs.json
     # attrs.json:
     # {"FilterPolicy": "{\"event_type\": [\"order_created\", \"order_updated\"]}",
     #  "RawMessageDelivery": "true"}
  3. Capture the returned SubscriptionArn for verification.
POST_VERIFY: (pending execution)
NOTES:
  - Auto-confirmation applies because the caller owns the SQS queue.
    The SubscriptionArn is returned immediately — no token step needed.
  - Filter policy: only messages with message attribute event_type in
    [order_created, order_updated] will be delivered. Messages without
    this attribute are silently dropped (by design).
  - RawMessageDelivery: true — the queue receives only the Message body,
    not the full SNS envelope. The Lambda trigger on this queue will
    receive the message body directly.
  - Delivery policy: default (4 retries over 1 hour, exponential backoff).
    To customize, use set-subscription-attributes --attribute-name
    DeliveryPolicy after creation.
```

### Worked example — diagnose subscription not receiving messages

```text
OPERATION: diagnose
VERDICT: COMPLETED
TARGET: arn:aws:sns:us-east-1:111111111111:order-events (subscription:
        arn:aws:sns:us-east-1:111111111111:order-events:1234-abcd,
        protocol: sqs, endpoint:
        arn:aws:sqs:us-east-1:111111111111:order-processing-queue,
        account 111111111111, region us-east-1)
PRE_CHECKS:
  - [PASS] Subscription exists, PendingConfirmation: false (confirmed)
  - [PASS] Queue policy allows sqs:SendMessage from topic ARN
  - [FAIL] Filter policy does not match publisher's message attributes
    — filter requires {"event_type": ["order_created"]} but publisher
    sends message attribute "type" (not "event_type"). All messages are
    silently dropped by the filter.
STEPS:
  1. Fix the filter policy to match the publisher's attribute name:
     aws sns set-subscription-attributes \
       --subscription-arn arn:aws:sns:us-east-1:111111111111:order-events:1234-abcd \
       --attribute-name FilterPolicy \
       --attribute-value '{"type": ["order_created", "order_updated"]}'
  2. Publish a test message with message attribute type=order_created:
     aws sns publish \
       --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
       --message '{"order_id": "test-123"}' \
       --message-attributes '{"type": {"DataType": "String", "StringValue": "order_created"}}'
  3. Verify the message is received by the SQS queue:
     aws sqs receive-message --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/order-processing-queue
POST_VERIFY:
  - [PASS] Filter policy updated to match publisher attributes
  - [PASS] Test message with type=order_created received by queue
  - [PASS] CloudTrail shows SetSubscriptionAttributes event
NOTES:
  - Root cause: attribute name mismatch. The filter policy used
    "event_type" but the publisher sends "type". This is the #1 cause
    of SNS filter-policy non-delivery.
  - Recommendation: standardize on a single attribute naming convention
    across all publishers. Consider using SNS message data protection
    to audit attribute names at the topic level.
```

### Worked example — set delivery policy with DLQ

```text
OPERATION: set-delivery-policy
VERDICT: READY
TARGET: arn:aws:sns:us-east-1:111111111111:order-events (subscription:
        arn:aws:sns:us-east-1:111111111111:order-events:5678-efgh,
        protocol: https, endpoint: https://api.example.com/webhook,
        account 111111111111, region us-east-1)
PRE_CHECKS:
  - [PASS] Subscription exists, PendingConfirmation: false
  - [PASS] Delivery policy JSON valid (5 retries, exponential backoff)
  - [PASS] DLQ SQS ARN exists (arn:aws:sqs:us-east-1:111111111111:sns-dlq)
  - [PASS] DLQ queue policy allows sqs:SendMessage from SNS service
  - [PASS] DLQ is not the same as the subscription endpoint (no loop)
STEPS:
  1. CONFIRM: About to set delivery policy and DLQ on subscription
     5678-efgh. Retry: 5 attempts, exponential backoff (1s-16s).
     DLQ: arn:aws:sqs:us-east-1:111111111111:sns-dlq. Proceed? (yes/no)
  2. aws sns set-subscription-attributes \
       --subscription-arn arn:aws:sns:us-east-1:111111111111:order-events:5678-efgh \
       --attribute-name DeliveryPolicy \
       --attribute-value '{"healthyRetryPolicy": {"numRetries": 5, "minDelayTarget": 1, "maxDelayTarget": 16, "numMinDelayRetries": 2, "numMaxDelayRetries": 3, "backoffFunction": "exponential"}}'
  3. aws sns set-subscription-attributes \
       --subscription-arn arn:aws:sns:us-east-1:111111111111:order-events:5678-efgh \
       --attribute-name RedrivePolicy \
       --attribute-value '{"deadLetterTargetArn": "arn:aws:sqs:us-east-1:111111111111:sns-dlq"}'
  4. Verify: aws sns get-subscription-attributes \
       --subscription-arn arn:aws:sns:us-east-1:111111111111:order-events:5678-efgh
POST_VERIFY: (pending execution)
NOTES:
  - Retry: 5 attempts, exponential backoff (1s, 2s, 4s, 8s, 16s).
    Total window: ~31 seconds. DLQ: messages failing all 5 retries go
    to sns-dlq. Monitor via CloudWatch Alarm on
    ApproximateNumberOfMessagesVisible. Replay from DLQ after fixing
    the endpoint.
```

### Worked example — cross-account subscription BLOCKED

```text
OPERATION: create
VERDICT: BLOCKED
TARGET: arn:aws:sns:us-east-1:222222222222:shared-events (subscription:
        new, protocol: sqs, endpoint:
        arn:aws:sqs:us-east-1:111111111111:my-queue,
        subscriber 111111111111, topic owner 222222222222, us-east-1)
PRE_CHECKS:
  - [PASS] Topic exists in account 222222222222
  - [PASS] Protocol sqs valid, endpoint SQS ARN valid
  - [FAIL] Topic policy does not allow sns:Subscribe for account
    111111111111 (only allows topic owner 222222222222).
  - [FAIL] Queue policy in account 111111111111 does not allow
    sqs:SendMessage from the topic ARN in account 222222222222.
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
NOTES:
  - Root cause: cross-account subscription requires BOTH sides'
    permission. Fix on topic owner side (222222222222): add
    sns:Subscribe for arn:aws:iam::111111111111:root to the topic
    policy. Fix on queue owner side (111111111111): add
    sqs:SendMessage from sns.amazonaws.com with Condition
    ArnEquals aws:SourceArn = the topic ARN to the queue policy.
```

## Anti-Patterns — NEVER (top 5)

These are the five highest-impact mistakes. Each one silently breaks
message delivery or creates a security exposure.

1. **NEVER assume a subscription is delivering messages just because
   the subscription exists.** A subscription in `PendingConfirmation`
   state (HTTP/HTTPS/email/sms) receives ZERO messages until confirmed.
   Always verify `PendingConfirmation: false` before expecting delivery.
   SQS/Lambda/firehose subscriptions owned by the caller are auto-
   confirmed; cross-account endpoints are NOT.

2. **NEVER set a filter policy without verifying the publisher's
   message attribute names.** The #1 cause of SNS non-delivery is an
   attribute name mismatch between the filter policy and the publisher.
   The filter silently drops non-matching messages — no error, no
   CloudTrail event, no DLQ delivery. Always run a test publish after
   setting a filter policy.

3. **NEVER configure a subscription DLQ (redrive) pointing to the same
   SQS queue as the subscription endpoint.** This creates a delivery
   loop: failed messages go to the DLQ (which is the same queue), get
   retried, fail again, and loop forever. Always verify the DLQ ARN is
   different from the endpoint ARN.

4. **NEVER leave the topic policy allowing `sns:Subscribe` from `*`
   (all principals) in production.** This allows any AWS account to
   subscribe to the topic and exfiltrate messages. Restrict
   `sns:Subscribe` to specific accounts or roles. Use SNS message data
   protection to audit for overly permissive topic policies.

5. **NEVER use `unsubscribe` without capturing the subscription
   attributes first.** Unsubscribing is irreversible — the subscription
   ARN, filter policy, delivery policy, and DLQ configuration are all
   lost. If the subscription needs to be recreated, all attributes must
   be reconfigured. Always emit `CONFIRM:` before `unsubscribe`.

## Edge-case handling

| Scenario | Detection | Handling |
|---|---|---|
| **HTTP endpoint returns 403 on confirmation POST** | SNS confirmation POST includes `x-amz-sns-message-type: SubscriptionConfirmation`; endpoint rejects it | Fix the endpoint to accept the SNS POST header and return 200. The endpoint must extract the `Token` and `SubscribeURL` from the JSON body. |
| **FIFO topic with Lambda subscription** | Topic name ends in `.fifo` | FIFO topics only support SQS FIFO queue endpoints. Lambda/HTTP/email are NOT supported. Switch to an SQS FIFO queue and trigger Lambda from the queue. |
| **Firehose subscription with delivery stream in CREATING state** | `describe-delivery-stream` shows `DeliveryStreamStatus: CREATING` | Wait for the stream to become `ACTIVE` before creating the subscription. SNS will fail delivery to a non-active stream. |
| **Topic message data protection denying messages** | Topic `getDataProtectionPolicy` has a `Deny` rule for the message content | The data protection policy audits, masks, or denies messages containing sensitive data. Verify the policy and adjust the publisher to exclude sensitive data, or adjust the policy to allow the data for trusted workloads. |

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`subscribe`, `confirm-subscription`, `set-subscription-attributes`,
  `unsubscribe`), emit: `CONFIRM: About to <operation> on SNS topic
  <topic-arn> (subscription <sub-arn>). This will <consequence>. Proceed?
  (yes/no)`. Do NOT execute until the operator confirms.

- **Capture pre-state for audit.** Before any subscription operation:
  `aws sns get-subscription-attributes --subscription-arn <arn>
  --output json > /tmp/<sub-id>-pre-$(date +%s).json`.

- **Verify topic policy before cross-account subscription.** The topic
  policy must explicitly allow `sns:Subscribe` for the subscriber's
  account. A missing permission produces `AuthorizationError`.

- **Verify endpoint policy before creating the subscription.** For SQS
  endpoints: the queue policy must allow `sqs:SendMessage` from the
  topic ARN. For Lambda: the resource policy must allow
  `lambda:InvokeFunction` from the topic ARN.

- **Verify the DLQ is not the same as the endpoint.** A redrive policy
  pointing to the same SQS queue as the subscription endpoint creates
  an infinite retry loop.

- **Verify the filter policy JSON before applying.** Malformed JSON or
  attribute names that don't match the publisher produce silent non-
  delivery. Run a test publish after applying.

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

## Domain

AWS CloudOps / SNS Subscription Operations & App Integration.

## AWS documentation

- **Amazon SNS Developer Guide** — https://docs.aws.amazon.com/sns/latest/dg/
- **SNS subscription operations** — https://docs.aws.amazon.com/sns/latest/dg/sns-subscription-operations.html
- **SNS filter policies** — https://docs.aws.amazon.com/sns/latest/dg/sns-message-filtering.html
- **SNS delivery policies** — https://docs.aws.amazon.com/sns/latest/dg/sns-message-delivery-retries.html
- **SNS dead-letter queues** — https://docs.aws.amazon.com/sns/latest/dg/sns-dead-letter-queues.html
- **SNS message data protection** — https://docs.aws.amazon.com/sns/latest/dg/sns-data-protection.html
- **SNS FIFO topics** — https://docs.aws.amazon.com/sns/latest/dg/fifo-message-delivery.html
