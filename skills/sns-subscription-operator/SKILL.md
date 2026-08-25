---
name: sns-subscription-operator
description: Operates AWS SNS subscription workflows end-to-end — subscription creation (HTTP/HTTPS/SQS/Lambda/email/sms/firehose), subscription confirmation (PendingConfirmation to Confirmed via token or auto-confirm for SQS/Lambda), filter-policy design (message attributes, FilterPolicyScope), delivery policies (retry backoff, dead-letter queue via redrive), subscription attributes (RawMessageDelivery), and diagnostic loops (list-subscriptions-by-topic, get-subscription-attributes, CloudTrail events). Runs deterministic pre-checks (topic exists, endpoint reachable, topic policy permits subscription, protocol valid, filter-policy JSON valid, DLQ target exists for redrive) behind a CONFIRM gate and emits a READY, BLOCKED, or COMPLETED verdict per operation. Use when creating subscriptions, confirming pending subscriptions, debugging filter-policy matches, configuring delivery retry and DLQ, or diagnosing why messages are not delivered.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws sns subscribe, confirm-subscription, list-subscriptions-by-topic, get-subscription-attributes, set-subscription-attributes, unsubscribe, aws sqs get-queue-attributes / set-queue-attributes (for SQS-backed subscriptions and DLQ), aws lambda get-policy (for Lambda-backed subscriptions), aws firehose describe-delivery-stream (for...
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AppIntegration
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  when_to_use: Creating an SNS subscription to a topic (HTTP/HTTPS/SQS/Lambda/ email/sms/firehose/application), confirming a subscription stuck in PendingConfirmation, designing or debugging a subscription filter policy, configuring delivery retry policy and dead-letter queue (DLQ), setting subscription attributes (RawMessageDelivery), diagnosing why messages are not delivered to a subscription, or validating SNS message data protection posture for a subscription.
  activation_triggers: create SNS subscription, confirm SNS subscription, PendingConfirmation, SNS filter policy, SNS delivery policy, SNS dead-letter queue, SNS subscription redrive, SNS retry backoff, RawMessageDelivery, subscribe to SNS topic, SNS subscription not receiving messages, SNS message data protection, cross-account SNS subscription, SNS firehose subscription, get-subscription-attributes
  invocation_schema: 'Input: either (a) an SNS subscription configuration (topic ARN, protocol, endpoint, filter policy, delivery policy, subscription attributes) plus the intended operation (create, confirm, set-filter-policy, set-delivery-policy, set-attributes, delete, diagnose), OR (b) a subscription ARN + operation for live-account execution. Output: deterministic OPERATION / VERDICT / TARGET / PRE_CHECKS / STEPS / POST_VERIFY / NOTES block per operation, where VERDICT is one of READY, BLOCKED, COMPLETED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: SNS, subscription, PendingConfirmation, ConfirmSubscription, filter policy, FilterPolicyScope, message attributes, delivery policy, retry backoff, dead-letter queue, DLQ, redrive policy, RawMessageDelivery, HTTP subscription, HTTPS subscription, SQS subscription, Lambda subscription, email subscription, firehose subscription, subscription attributes, SNS message data protection, cross-account subscription
  tags: aws, sns, app-integration, subscription, messaging, filter-policy, delivery-policy, operate
  keywords_tags: aws, sns, app-integration, subscription, messaging, operate
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

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic--the-non-obvious-rules).
> Seven rules: auto-confirm when caller owns the endpoint, token confirmation for HTTP/HTTPS/email/sms, attribute matching, FilterPolicyScope default, RawMessageDelivery, per-subscription retry override, subscription-level redrive.

## Pre-flight: subscription metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `list-subscriptions-by-topic` paginates at 100/page —
drain `--next-token` to completion. `list-topics` paginates at 100/page.

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#live-account-pre-flight).
> get-topic-attributes, list-subscriptions-by-topic, per-protocol endpoint policy checks (SQS/Lambda/Firehose/HTTP), filter-policy JSON, and DLQ validation.

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

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-0-expert-knowledge--non-obvious-sns-subscription-behaviors).
> 13 behaviors: two-phase confirmation, both-sides cross-account permission, silent filter drops, filter operators, body scope, raw payload shape, policy override, backoff, SQS-only DLQ, FIFO queue-only, data protection, Firehose ACTIVE, eventual consistency.

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

> Moved to [references/worked-examples.md](references/worked-examples.md#worked-example--diagnose-subscription-not-receiving-messages).
> COMPLETED diagnose block: attribute-name mismatch (filter 'event_type' vs publisher 'type'), fixed FilterPolicy plus test publish.

### Worked example — set delivery policy with DLQ

> Moved to [references/worked-examples.md](references/worked-examples.md#worked-example--set-delivery-policy-with-dlq).
> READY block: 5-retry exponential DeliveryPolicy plus RedrivePolicy DLQ with same-queue loop check.

### Worked example — cross-account subscription BLOCKED

> Moved to [references/worked-examples.md](references/worked-examples.md#worked-example--cross-account-subscription-blocked).
> BLOCKED block: cross-account missing sns:Subscribe on the topic and sqs:SendMessage on the queue — both sides must be fixed.

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

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#edge-case-handling).
> 403 on confirmation POST, FIFO+Lambda unsupported, Firehose stream CREATING, data-protection Deny.

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

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#recent-aws-features-2024-2026).
> Firehose protocol, message data protection, MessageBody filter scope, FIFO expansion, PublishBatch, cross-account CloudTrail delivery logging.

## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — Expert heuristic seven rules, Step 0 expert knowledge, edge-case handling, Recent AWS features
- [diagnostic-commands](references/diagnostic-commands.md) — live-account pre-flight commands moved from SKILL.md
- [subscription-confirmation-and-delivery](references/subscription-confirmation-and-delivery.md) — confirmation flows and delivery retry detail
- [subscription-protocols-and-attributes](references/subscription-protocols-and-attributes.md) — per-protocol endpoint formats and subscription attributes
- [worked-examples](references/worked-examples.md) — diagnose, delivery-policy-with-DLQ, and cross-account BLOCKED worked examples moved from SKILL.md

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
