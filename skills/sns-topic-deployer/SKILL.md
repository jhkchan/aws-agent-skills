---
name: sns-topic-deployer
description: 'Provisions AWS SNS topics with production-grade configuration: correct topic type (Standard vs FIFO), subscriptions (HTTP/S, SQS, Lambda, Email, Firehose, mobile push), subscription filter policies (MessageAttributes and MessageBody scope), cross-account access policy, SSE-KMS encryption with subscriber decrypt requirements, delivery status logging per protocol, subscription-level dead-letter queues, FIFO deduplication and ordering, mobile push (APNS, FCM, Baidu), and latest features (message archiving, SNS-to-EventBridge). Emits a READY_TO_DEPLOY checklist with every configuration item verified. Use when creating a new SNS topic, deploying a topic to production, configuring subscriptions, or generating deployment CLI commands. Triggers: create SNS topic, deploy topic, FIFO topic, subscription filter policy, delivery status logging, SNS DLQ, mobile push, cross-account publishing.'
license: Apache-2.0
compatibility: 'Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with sns, iam, kms, sqs, lambda, firehose, and logs access. Works with Terraform aws_sns_topic resources, CloudFormation AWS::SNS::Topic, and SAM templates.'
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AppIntegration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, sns, cloudops, deploy, messaging, app-integration, pub-sub, fifo, encryption, delivery-logging
  dependencies: aws-orchestrator
  keywords: aws, sns, cloudops, deploy, provisioning, messaging, app-integration, pub-sub, fanout, standard topic, fifo topic, subscription, filter policy, delivery status logging, SSE-KMS, cross-account, mobile push, APNS, FCM, message archiving, SNS-to-EventBridge
  when_to_use: Invoke when the user wants to create a new SNS topic, deploy a topic to production, configure subscriptions and filter policies, set up delivery status logging, enable mobile push notifications, or generate deployment CLI commands and IaC templates. Do NOT invoke for SNS security audits (use sns-topic-public-subscription-auditor) or for SQS queue deployment (use sqs-queue-deployer).
---

# SNS Topic Deployer

An AWS CloudOps agent skill that provisions Amazon SNS topics with correct
production defaults. The skill walks the operator through a 10-step
deployment procedure, explains why each default matters, and emits a
READY_TO_DEPLOY checklist verifying every configuration item. SNS is a
push-based fan-out bus — wrong defaults silently cause message loss and
invisible failures.

## Quick navigation

| Section | What it covers | When to read |
|---|---|---|
| [Invocation contract](#invocation-contract-hard-requirement) | Mandatory output format labels | Every invocation |
| [Reasoning framework](#reasoning-framework-why-deployment-order-matters) | Why deployment order matters | Understanding dependencies |
| [Prerequisites](#prerequisites-verify-before-deployment) | What to verify before deploying | Before any CLI command |
| [Step 1: Topic type](#step-1-topic-type-selection-standard-vs-fifo) | Standard vs FIFO decision | Choosing topic type |
| [Step 2: Subscriptions](#step-2-subscriptions) | HTTP/S, SQS, Lambda, Email, Firehose, mobile push | Wiring subscribers |
| [Step 3: Filter policy](#step-3-subscription-filter-policy) | MessageAttributes vs MessageBody scope | Message routing |
| [Step 4: Access policy](#step-4-access-policy-least-privilege) | Cross-account, S3, CloudWatch, publisher scoping | Security config |
| [Step 5: Encryption](#step-5-encryption-sse-kms) | SSE-KMS, cross-account decrypt, KMS key policy | Security config |
| [Step 6: Delivery logging](#step-6-delivery-status-logging) | Per-protocol CloudWatch Logs, resource policy | Observability |
| [Step 7: Subscription DLQ](#step-7-subscription-level-dead-letter-queue) | RedrivePolicy on subscriptions | Reliability |
| [Step 8: FIFO specifics](#step-8-fifo-specifics-dedup--ordering) | Dedup, MessageGroupId, .fifo suffix | FIFO topics only |
| [Step 9: Mobile push](#step-9-mobile-push-notifications) | APNS, FCM, Baidu, platform application | Mobile push only |
| [Step 10: Verification](#step-10-verification) | Post-deployment checks | After deployment |
| [NEVER (anti-patterns)](#never-things-to-never-do) | Common deployment mistakes | Avoid these |
| [Output format](#output-format-mandatory-literal-labels) | Checklist report shape | Every invocation |

## Activation keywords

create SNS topic, deploy SNS topic, standard topic, FIFO topic, subscription,
HTTP/S subscription, SQS subscription, Lambda subscription, Email subscription,
Firehose subscription, mobile push, platform application, APNS, FCM, Baidu,
filter policy, subscription filter, MessageAttributes, MessageBody, delivery
status logging, CloudWatch Logs, SSE-KMS, cross-account publishing, S3 Event
Notification, CloudWatch Alarm, subscription DLQ, RedrivePolicy,
ContentBasedDeduplication, MessageDeduplicationId, MessageGroupId, message
archiving, SNS-to-EventBridge.

## Invocation contract (hard requirement)

When this skill is invoked with an SNS deployment request (topic name,
topic type, subscription list, workload pattern, or a partial existing
configuration), the agent MUST respond with the READY_TO_DEPLOY checklist
defined in the "Output format" section using the literal all-caps labels
`TOPIC:`, `VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT
preface the checklist with prose, headings, or disclaimers — emit the
block as the first lines of the response.

## Reasoning framework (why deployment order matters)

SNS deployment has **dependency and ordering constraints**:

1. **Topic type FIRST** — Standard vs FIFO is set at creation via the
   `.fifo` suffix. Immutable after creation. FIFO requires SQS FIFO queue
   subscribers only.
2. **KMS key BEFORE subscriptions** — if SSE-KMS is enabled, every
   subscriber needs `kms:Decrypt` and `kms:GenerateDataKey*` on the key.
3. **Access policy BEFORE cross-account subscriptions** — cross-account
   requires BOTH the topic policy AND the subscriber IAM/key policy.
4. **Delivery logging BEFORE production traffic** — per-protocol; requires
   a CloudWatch IAM role + Logs resource policy. Without it, delivery
   failures are invisible (SNS retries HTTP for 4 hours then silently drops).
5. **Filter policy AFTER subscription** — attached to the subscription,
   not the topic.
6. **Subscription DLQ AFTER subscription** — subscription-level via
   RedrivePolicy, not topic-level.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **Topic name** | Unique within account/region. FIFO requires `.fifo` suffix. | `aws sns list-topics` |
| **Topic type decided** | Standard (unlimited TPS) vs FIFO (300 TPS, `.fifo`). Immutable. | Workload requirements |
| **KMS key (if SSE-KMS)** | Customer-managed CMK with key policy granting SNS + all subscribers `kms:Decrypt` + `kms:GenerateDataKey*`. | `aws kms describe-key --key-id <alias>` |
| **Subscriber endpoints** | SQS ARNs, Lambda ARNs, HTTPS URLs, emails, Firehose ARNs, platform app ARNs. | Depends on protocol |
| **DLQ ARN (if subscription DLQ)** | SQS queue must exist before subscription RedrivePolicy. | `aws sqs get-queue-url --queue-name <dlq>` |
| **CloudWatch role (if delivery logging)** | IAM role with `logs:CreateLogStream` + `logs:PutLogEvents` + trust for `sns.amazonaws.com`. | `aws iam get-role --role-name <role>` |
| **Platform application ARN (if mobile push)** | Platform app with credentials for APNS/FCM/Baidu. | `aws sns list-platform-applications` |

## Deployment procedure (apply in order)

### Step 1: Topic type selection (Standard vs FIFO)

The topic type is **immutable** — cannot be changed after creation.

| Attribute | Standard | FIFO |
|---|---|---|
| Ordering | Best-effort | Per message group (strict) |
| Deduplication | N/A | ContentBasedDeduplication or explicit DeduplicationId (5-min window) |
| Throughput | Unlimited | 300 TPS |
| Name suffix | None | `.fifo` (mandatory) |
| Supported subscribers | HTTP/S, SQS, Lambda, Email, Firehose, Application | **SQS FIFO queues only** |
| Cost (per million requests) | $0.50 | $0.60 |

```bash
# Standard topic
aws sns create-topic --name order-events

# FIFO topic (name MUST end in .fifo)
aws sns create-topic --name order-events.fifo \
  --attributes FifoTopic=true,ContentBasedDeduplication=true
```

**IMPORTANT:** FIFO topics ONLY support SQS FIFO queue subscribers. HTTP,
email, Lambda, and mobile push subscriptions are rejected. If you need
ordering AND Lambda, use a Standard topic fanning out to an SQS FIFO
queue with Lambda consuming the queue.

### Step 2: Subscriptions

| Protocol | Endpoint format | Delivery | Retry |
|---|---|---|---|
| `http`/`https` | URL | POST to URL | Up to 4 hours (100,010 attempts) |
| `email`/`email-json` | Email address | Email | One-time confirmation, no retry |
| `sqs` | SQS queue ARN | SendMessage | Immediate (SQS handles retry) |
| `lambda` | Lambda function ARN | Invoke (async) | Lambda async retry (2 retries) |
| `firehose` | Firehose delivery stream ARN | PutRecordBatch | Firehose handles retry |
| `application` | Platform endpoint ARN | Mobile push | SNS retry (varies by platform) |

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:111111111111:order-queue \
  --return-subscription-arn
```

HTTP/HTTPS subscriptions require confirmation — SNS sends a
`SubscriptionConfirmation` message with a token. Use `--return-subscription-arn`
for non-HTTP protocols (auto-confirms same-account subscriptions). Full
per-protocol CLI is in `references/deployment-cli-commands.md`.

### Step 3: Subscription filter policy

Filter policies route messages to specific subscriptions based on message
attributes or body content.

| Scope | How it works | Use when |
|---|---|---|
| `MessageAttributes` (default) | Filters on message attributes | Most common — structured metadata |
| `MessageBody` | Filters on JSON properties in body | Publishers don't set attributes; payload-based routing |

```bash
aws sns set-subscription-attributes \
  --subscription-arn <sub-arn> \
  --attribute-name FilterPolicy \
  --attribute-value '{"event_type": ["order_created"], "region": [{"prefix": "us-"}]}'

# For body-based filtering:
aws sns set-subscription-attributes \
  --subscription-arn <sub-arn> \
  --attribute-name FilterPolicyScope \
  --attribute-value MessageBody
```

**Filter operators:** exact match (`["value"]`), prefix (`[{"prefix":"ord"}]`),
anything-but (`[{"anything-but":["cancelled"]}]`), numeric range
(`[{"numeric":[">=",100]}]`), exists (`[{"exists":true}]`).

**IMPORTANT:** with `FilterPolicyScope=MessageBody`, message body MUST be
valid JSON. Non-JSON bodies cause the filter to fail silently.

### Step 4: Access policy (least-privilege)

The SECURE default is **no resource-based policy** — access governed by IAM.
A topic policy is needed for:

| Scenario | Policy pattern |
|---|---|
| S3 Event Notification to SNS | `Principal: "*" + Condition: aws:SourceArn: <bucket-arn>` |
| CloudWatch Alarm to SNS | `Principal: {"Service": "cloudwatch.amazonaws.com"}` + `sns:Publish` |
| Cross-account publisher | `Principal: {"AWS": "<account-id>"}` + `sns:Publish` |
| Cross-account subscriber | `Principal: {"AWS": "<account-id>"}` + `sns:Subscribe` |
| Same-account only | NO resource-based policy needed — IAM is sufficient |

**NEVER use `Principal: "*"` with `sns:Subscribe` without a STRONG
condition.** SNS is push-based — wildcard Subscribe lets anyone register
an HTTPS endpoint and receive all messages (push-based data exfiltration).

```bash
aws sns set-topic-attributes \
  --topic-arn <topic-arn> \
  --attribute-name Policy \
  --attribute-value '<policy-json>'
```

### Step 5: Encryption (SSE-KMS)

SNS only supports SSE-KMS (no free SSE option like SQS).

| Option | Key manager | Cross-account? | Use when |
|---|---|---|---|
| **AWS-managed** (`alias/aws/sns`) | AWS | NO — blocks cross-account | Same-account only |
| **Customer-managed CMK** | You | YES — if key policy grants subscribers | Cross-account or need key control |
| **None** | — | YES | NEVER — plaintext at rest |

**Decision:** same-account subscribers → AWS-managed key. Cross-account
subscribers → customer-managed CMK with key policy granting every
subscriber account `kms:Decrypt` + `kms:GenerateDataKey*`.

```bash
aws sns set-topic-attributes \
  --topic-arn <topic-arn> \
  --attribute-name KmsMasterKeyId \
  --attribute-value alias/my-sns-key
```

> Moved to [references/topic-configuration-guide.md](references/topic-configuration-guide.md#cross-account-kms-key-policy-requirement).
> The cross-account subscriber kms:Decrypt + kms:GenerateDataKey* key-policy JSON with the kms:ViaService condition.

### Step 6: Delivery status logging

Without delivery logging, delivery failures are invisible — SNS retries
HTTP for 4 hours then silently drops messages. Per-protocol configuration:

| Protocol category | Success attribute | Failure attribute |
|---|---|---|
| HTTP/HTTPS | `HTTPSuccessFeedbackRoleArn` | `HTTPFailureFeedbackRoleArn` |
| SQS | `SQSSuccessFeedbackRoleArn` | `SQSFailureFeedbackRoleArn` |
| Application (Lambda, mobile) | `ApplicationSuccessFeedbackRoleArn` | `ApplicationFailureFeedbackRoleArn` |

```bash
aws sns set-topic-attributes \
  --topic-arn <topic-arn> \
  --attribute-name SQSFailureFeedbackRoleArn \
  --attribute-value arn:aws:iam::111111111111:role/SNSDeliveryFeedback
```

**IMPORTANT:** delivery logging also requires a CloudWatch Logs resource
policy granting SNS `logs:CreateLogStream` and `logs:PutLogEvents`. Without
it, SNS silently fails to write logs even if the feedback role is configured.

### Step 7: Subscription-level dead-letter queue

SNS DLQs are **subscription-level** (via RedrivePolicy on the subscription),
NOT topic-level. There is no topic-level DLQ attribute.

| Scenario | DLQ needed? |
|---|---|
| HTTP/HTTPS subscription | YES — SNS drops after 4 hours of retries |
| SQS subscription | OPTIONAL — SQS has own DLQ mechanism |
| Lambda subscription | OPTIONAL — Lambda has on-failure destinations |
| Email subscription | NO — email does not retry |
| Mobile push | YES — failed deliveries otherwise silent |

```bash
aws sns set-subscription-attributes \
  --subscription-arn <sub-arn> \
  --attribute-name RedrivePolicy \
  --attribute-value '{"deadLetterTargetArn":"arn:aws:sqs:us-east-1:111111111111:sns-dlq"}'
```

### Step 8: FIFO specifics (dedup + ordering)

- **ContentBasedDeduplication:** `true` → SNS computes SHA-256 hash, dedup
  within 5-min window. `false` → publisher MUST send `MessageDeduplicationId`.
- **MessageGroupId:** required on every FIFO message. Messages with same
  group ID delivered in order to SQS FIFO subscribers.
- **Constraints:** ONLY SQS FIFO queues can subscribe. Throughput: 300 TPS.
  `.fifo` suffix mandatory.

```bash
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events.fifo \
  --message '{"orderId": "12345"}' \
  --message-group-id "customer-67890" \
  --message-deduplication-id "order-12345-v1"
```

### Step 9: Mobile push notifications

> Moved to [references/topic-configuration-guide.md](references/topic-configuration-guide.md#mobile-push-notifications-step-9).
> create-platform-application, create-platform-endpoint, and target-arn publish CLI plus the APNS/FCM/Baidu/default message-format table.

### Step 10: Verification

```bash
aws sns get-topic-attributes --topic-arn <topic-arn>
aws sns list-subscriptions-by-topic --topic-arn <topic-arn>
aws sns get-subscription-attributes --subscription-arn <sub-arn>
aws sns publish --topic-arn <topic-arn> --message '{"test": true}'
# FIFO topic requires --message-group-id
```

## Latest SNS features (2024-2026)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#latest-sns-features-2024-2026).
> Message archiving, SNS-to-EventBridge, MessageBody filter GA, message data protection, FIFO delivery logging, SSE-KMS consistency.

## Workload-specific deployment matrix

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#workload-specific-deployment-matrix).
> Six workload rows (event fan-out, ordered, webhook, cross-account, mobile push, S3 event) with topic-type, encryption, subscriber, filter, DLQ, and logging defaults.

## NEVER (things to never do)

1. **NEVER create a FIFO topic without the `.fifo` suffix.** SNS rejects
   the create call. The suffix is mandatory and immutable.

2. **NEVER subscribe a non-SQS endpoint to a FIFO topic.** FIFO topics
   ONLY support SQS FIFO queue subscribers. For ordering + Lambda, use a
   FIFO topic fanning out to an SQS FIFO queue with Lambda consuming it.

3. **NEVER use `Principal: "*"` with `sns:Subscribe` without a STRONG
   condition.** SNS is push-based — wildcard Subscribe lets anyone register
   an HTTPS endpoint and passively receive all messages (push-based data
   exfiltration). Only `aws:SourceOwner`, `aws:SourceAccount`, and
   `aws:SourceArn` are STRONG.

4. **NEVER use the AWS-managed key (`alias/aws/sns`) for a topic with
   cross-account subscribers.** Cross-account SQS subscribers silently fail
   to decrypt. Use a customer-managed CMK with subscriber accounts granted
   `kms:Decrypt`.

5. **NEVER deploy a topic with HTTP/HTTPS subscriptions and no delivery
   status logging.** SNS retries HTTP for 4 hours then silently drops
   messages. Without failure logging, dropped messages are invisible. This
   is the #1 SNS reliability issue.

Extended anti-patterns (delivery logging gaps, MessageBody filter,
FIFO dedup, topic-level DLQ, unencrypted topics, PendingConfirmation)
are in `references/troubleshooting-and-error-handling.md`.

## Error-handling branches


Full subscription troubleshooting decision tree, per-protocol retry/dead-letter
behavior, and edge-case handling are in `references/troubleshooting-and-error-handling.md`.

## Pre-flight safety checks (run before any deployment CLI)

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#pre-flight-safety-checks-run-before-any-deployment-cli).
> Topic-name availability, FIFO suffix, KMS key policy, cross-account both-sides, CloudWatch role, platform app, and rollback-backup checks with verify commands.

## Output format — MANDATORY literal labels

When invoked with a topic deployment request, your ENTIRE response MUST
be the checklist block below. The labels are **case-sensitive all-caps
keywords** — write them EXACTLY as shown. Do NOT substitute `Verdict`,
`**VERDICT**`, `### Verdict`, or any markdown variant. Do NOT write a
preamble. Start with `TOPIC:` and stop after the `VERIFICATION_COMMANDS:` block.

```text
TOPIC: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Topic type — Standard (best-effort ordering, unlimited TPS)
  [✓]      Encryption — SSE-KMS (alias/aws/sns, same-account)
  [✓]      Access policy — S3 notification pattern (Principal:* + aws:SourceArn)
  [✓]      Subscriptions — 2 active (SQS: order-queue, Lambda: order-handler)
  [✓]      Delivery logging — SQS failure + HTTP failure (CloudWatch role)
  [OPTIONAL] Filter policy — N/A (no filtering needed)
  [OPTIONAL] Subscription DLQ — N/A (SQS has own DLQ)
  [OPTIONAL] FIFO dedup — N/A (Standard topic)
  [OPTIONAL] Mobile push — N/A (no mobile subscribers)
VERIFICATION_COMMANDS:
  aws sns get-topic-attributes --topic-arn <arn>
  aws sns list-subscriptions-by-topic --topic-arn <arn>
  aws sns get-topic-attributes --topic-arn <arn> --query 'Attributes.KmsMasterKeyId'
  aws sns publish --topic-arn <arn> --message '{"test": true}'
```

**Status marker semantics:**
- `[✓]` — configuration is applied and verified.
- `[✗]` — configuration is NOT applied or is misconfigured. Cite the gap.
- `[OPTIONAL]` — recommended but not required for the workload type.
- `[INPUT NEEDED]` — a prerequisite value is missing and must be provided.

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
checklist that looks deployable but contains a silent configuration defect.
Self-check EVERY emitted block before returning.

### Required output structure

> Moved to [references/worked-examples.md](references/worked-examples.md#required-output-structure).
> The literal TOPIC/VERDICT/CHECKLIST/VERIFICATION_COMMANDS template — identical in shape to the Output format section above.

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: READY_TO_DEPLOY` without showing ALL checklist
   items.** Every REQUIRED row MUST appear with `[✓]` or `[✗]`. Every
   OPTIONAL row MUST appear with `[✓]`, `[✗]`, or `[OPTIONAL]`.

2. **NEVER mark Encryption `[✓]` for a cross-account topic using
   `alias/aws/sns`.** The AWS-managed key only allows the owning account
   to decrypt. For cross-account, the checklist MUST show a customer-
   managed CMK with subscriber accounts granted `kms:Decrypt`.

3. **NEVER mark Delivery logging `[✓]` without confirming BOTH the
   feedback role ARN AND the CloudWatch Logs resource policy.** The
   checklist line MUST cite both.

4. **NEVER mark Subscriptions `[✓]` if any subscription is in
   `PendingConfirmation` status.** Show `(N active, M pending)` and if
   M > 0, mark `[✗]`.

5. **NEVER emit `VERDICT: PREREQUISITES_MISSING` without citing each
   specific gap.** Every `[✗]` MUST have a one-line reason.

6. **NEVER mark a FIFO topic `[✓]` without the `.fifo` suffix AND
   confirmation that all subscribers are SQS FIFO queues.**

7. **NEVER omit the Filter policy row.** If no filter is needed, mark
   `[OPTIONAL] Filter policy — N/A`.

8. **NEVER deviate from the literal labels `TOPIC:`, `VERDICT:`,
   `CHECKLIST:`, `VERIFICATION_COMMANDS:`.**

### Perfect example output — READY_TO_DEPLOY (Standard topic, same-account)

```text
TOPIC: order-events
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Topic type — Standard (best-effort ordering, unlimited TPS)
  [✓]      Encryption — SSE-KMS (alias/aws/sns, same-account)
  [✓]      Access policy — S3 notification pattern (Principal:* + aws:SourceArn: order-uploads)
  [✓]      Subscriptions — 2 active (SQS: order-queue [Confirmed], Lambda: order-handler [Confirmed])
  [✓]      Delivery logging — SQS failure + Lambda failure (role: arn:aws:iam::111111111111:role/SNSDeliveryFeedback + CW Logs resource policy granted)
  [✓]      Filter policy — event_type: ["order_created"] on SQS subscription (MessageAttributes scope)
  [OPTIONAL] Subscription DLQ — N/A (SQS has own DLQ)
  [OPTIONAL] FIFO dedup — N/A (Standard topic)
  [OPTIONAL] Mobile push — N/A (no mobile subscribers)
VERIFICATION_COMMANDS:
  aws sns get-topic-attributes --topic-arn arn:aws:sns:us-east-1:111111111111:order-events --query 'Attributes.FifoTopic'
  aws sns get-topic-attributes --topic-arn arn:aws:sns:us-east-1:111111111111:order-events --query 'Attributes.KmsMasterKeyId'
  aws sns get-topic-attributes --topic-arn arn:aws:sns:us-east-1:111111111111:order-events --query 'Attributes.Policy'
  aws sns list-subscriptions-by-topic --topic-arn arn:aws:sns:us-east-1:111111111111:order-events
  aws sns get-topic-attributes --topic-arn arn:aws:sns:us-east-1:111111111111:order-events --query 'Attributes.SQSFailureFeedbackRoleArn'
  aws sns get-subscription-attributes --subscription-arn <sqs-sub-arn> --query 'Attributes.FilterPolicy'
```

### Perfect example output — PREREQUISITES_MISSING

> Moved to [references/worked-examples.md](references/worked-examples.md#perfect-example-output--prerequisites_missing).
> PREREQUISITES_MISSING example with [✗] encryption (AWS-managed key + cross-account subscriber), unsubscribed queue, and missing delivery-logging role citations.

> Moved to [references/worked-examples.md](references/worked-examples.md#self-check-before-emit).
> Eight-item emit self-check: all rows present, customer-managed CMK, logging citations, no pending subscriptions, FIFO suffix and SQS FIFO subscribers, gap citations, literal labels.

## References

- `references/topic-configuration-guide.md` — deep reference on topic type
  internals, delivery retry semantics, subscription confirmation flow,
  filter policy operators, cross-account KMS key policy requirements,
  and mobile push platform-specific message formats.
- `references/deployment-cli-commands.md` — full copy-pasteable CLI command
  sequence for all 10 deployment steps, including Terraform equivalents.
- `references/troubleshooting-and-error-handling.md` — subscription
  troubleshooting decision tree, per-protocol error handling and retry
  behavior, and production edge cases (cross-account KMS, high-fanout,
  FIFO compatibility).
- `references/worked-example-multi-protocol.md` — step-by-step multi-protocol
  topic configuration (HTTPS + SQS + cross-account Lambda + mobile push).

## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — Latest SNS features (2024-2026) and the workload-specific deployment matrix moved from SKILL.md
- [deployment-cli-commands](references/deployment-cli-commands.md) — full copy-pasteable CLI sequence for all 10 deployment steps, including Terraform equivalents
- [diagnostic-commands](references/diagnostic-commands.md) — pre-flight safety checks and rollback capture moved from SKILL.md
- [topic-configuration-guide](references/topic-configuration-guide.md) — topic type internals, filter operators, cross-account KMS key policy, mobile push message formats
- [troubleshooting-and-error-handling](references/troubleshooting-and-error-handling.md) — subscription troubleshooting decision tree, per-protocol error handling, and the error-handling branches table moved from SKILL.md
- [worked-example-multi-protocol](references/worked-example-multi-protocol.md) — step-by-step multi-protocol topic configuration walkthrough
- [worked-examples](references/worked-examples.md) — required output structure template, PREREQUISITES_MISSING example, and emit self-check moved from SKILL.md

## Domain

AWS CloudOps / App Integration — SNS Messaging Provisioning.

## AWS documentation

- **Amazon SNS Developer Guide** — https://docs.aws.amazon.com/sns/latest/dg/welcome.html
- **SNS Topic Configuration** — https://docs.aws.amazon.com/sns/latest/dg/sns-create-topic.html
- **SNS Encryption** — https://docs.aws.amazon.com/sns/latest/dg/sns-server-side-encryption.html
- **SNS Subscription Filter Policies** — https://docs.aws.amazon.com/sns/latest/dg/sns-subscription-filter-policies.html
- **SNS Delivery Status Logging** — https://docs.aws.amazon.com/sns/latest/dg/sns-topic-attributes.html#delivery-status
- **SNS FIFO Topics** — https://docs.aws.amazon.com/sns/latest/dg/fifo-topics.html
- **SNS Mobile Push** — https://docs.aws.amazon.com/sns/latest/dg/sns-mobile-push.html
- **SNS Message Data Protection** — https://docs.aws.amazon.com/sns/latest/dg/sns-message-data-protection.html
- **SNS CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/sns/
