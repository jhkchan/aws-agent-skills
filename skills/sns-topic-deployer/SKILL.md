---
name: sns-topic-deployer
description: >-
  Provisions AWS SNS topics with production-grade configuration: correct topic
  type (Standard vs FIFO), subscriptions (HTTP/S, SQS, Lambda, Email, Firehose,
  mobile push), subscription filter policies (MessageAttributes and MessageBody
  scope), cross-account access policy, SSE-KMS encryption with subscriber
  decrypt requirements, delivery status logging per protocol, subscription-level
  dead-letter queues, FIFO deduplication and ordering, mobile push (APNS, FCM,
  Baidu), and latest features (message archiving, SNS-to-EventBridge). Emits a
  READY_TO_DEPLOY checklist with every configuration item verified. Use when
  creating a new SNS topic, deploying a topic to production, configuring
  subscriptions, or generating deployment CLI commands. Triggers: create SNS
  topic, deploy topic, FIFO topic, subscription filter policy, delivery status
  logging, SNS DLQ, mobile push, cross-account publishing.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini).
  For live deployment: AWS CLI v2 with sns, iam, kms, sqs, lambda, firehose, and
  logs access. Works with Terraform aws_sns_topic resources, CloudFormation
  AWS::SNS::Topic, and SAM templates.
keywords:
  - aws
  - sns
  - cloudops
  - deploy
  - provisioning
  - messaging
  - app-integration
  - pub-sub
  - fanout
  - standard topic
  - fifo topic
  - subscription
  - filter policy
  - delivery status logging
  - SSE-KMS
  - cross-account
  - mobile push
  - APNS
  - FCM
  - message archiving
  - SNS-to-EventBridge
tags:
  - aws
  - sns
  - cloudops
  - deploy
  - messaging
  - app-integration
  - pub-sub
  - fifo
  - encryption
  - delivery-logging
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: AppIntegration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags:
    - aws
    - sns
    - cloudops
    - deploy
    - messaging
    - app-integration
    - pub-sub
    - fifo
    - encryption
  dependencies:
    - aws-orchestrator
  keywords:
    - create sns topic
    - deploy sns topic
    - fifo topic
    - subscription filter policy
    - delivery status logging
    - sns dlq
    - mobile push
    - cross-account publishing
    - message archiving
    - sns to eventbridge
  when_to_use: >-
    Invoke when the user wants to create a new SNS topic, deploy a topic to
    production, configure subscriptions and filter policies, set up delivery
    status logging, enable mobile push notifications, or generate deployment CLI
    commands and IaC templates. Do NOT invoke for SNS security audits (use
    sns-topic-public-subscription-auditor) or for SQS queue deployment (use
    sqs-queue-deployer).
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

Cross-account KMS key policy requirement:
```json
{
  "Sid": "Allow cross-account SNS subscribers",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::222222222222:root" },
  "Action": ["kms:Decrypt", "kms:GenerateDataKey*"],
  "Resource": "*",
  "Condition": { "StringEquals": { "kms:ViaService": "sns.us-east-1.amazonaws.com" } }
}
```

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

```bash
# Create platform application
aws sns create-platform-application \
  --name MyAppAPNS --platform APNS \
  --attributes PlatformCredential=<private-key>,PlatformPrincipal=<certificate>

# Register device endpoint
aws sns create-platform-endpoint \
  --platform-application-arn arn:aws:sns:us-east-1:111111111111:app/APNS/MyAppAPNS \
  --token <device-token> \
  --custom-user-data '{"userId": "12345"}'

# Publish to mobile endpoint (use --message-structure json with default key)
aws sns publish \
  --target-arn <endpoint-arn> \
  --message-structure json \
  --message '{"default": "...", "APNS": "{\"aps\":{\"alert\":\"Order shipped\"}}", "FCM": "{\"notification\":{\"title\":\"Order shipped\"}}"}'
```

| Platform | Key | Format |
|---|---|---|
| APNS | `APNS` | `{"aps":{"alert":"message"}}` |
| FCM (Android) | `FCM`/`GCM` | `{"notification":{"title":"...","body":"..."}}` |
| Baidu | `Baidu` | `{"title":"...","description":"..."}` |
| Default | `default` | Fallback for all platforms |

### Step 10: Verification

```bash
aws sns get-topic-attributes --topic-arn <topic-arn>
aws sns list-subscriptions-by-topic --topic-arn <topic-arn>
aws sns get-subscription-attributes --subscription-arn <sub-arn>
aws sns publish --topic-arn <topic-arn> --message '{"test": true}'
# FIFO topic requires --message-group-id
```

## Latest SNS features (2024-2026)

- **SNS message archiving (Direct Messaging):** Archive messages to S3 via
  Kinesis Data Firehose for long-term storage and replay.
- **SNS-to-EventBridge integration:** Route messages directly to EventBridge
  event buses for event-driven architectures.
- **Message body filter policy (GA):** `FilterPolicyScope=MessageBody` for
  payload-based subscription filtering. Requires JSON message bodies.
- **SNS message data protection (2024):** Detect and block sensitive data
  (PII, financial) in published messages. Per-topic deny/redact actions.
- **FIFO topic delivery status logging (2024-2025):** Enhanced per-protocol
  failure logging for FIFO topics.
- **SNS-to-SQS SSE-KMS consistency (2024):** Topic KMS key policy must grant
  `kms:Decrypt` to the SQS queue's consumer role.

## Workload-specific deployment matrix

| Workload | Topic type | Encryption | Subscribers | Filter | DLQ | Delivery logging |
|---|---|---|---|---|---|---|
| **Event fan-out** | Standard | AWS-managed | SQS (multiple) | Per-service attributes | Per-subscription | SQS failure |
| **Ordered processing** | FIFO | AWS-managed | SQS FIFO | N/A | Per-subscription | SQS failure |
| **Webhook delivery** | Standard | AWS-managed | HTTP/HTTPS | N/A | Per-subscription | HTTP failure (REQUIRED) |
| **Cross-account fan-out** | Standard | Customer CMK | SQS (cross-account) | MessageAttributes | Per-subscription | SQS failure |
| **Mobile push** | Standard | AWS-managed | Application | N/A | Per-subscription | Application failure |
| **S3 Event fan-out** | Standard | AWS-managed | SQS, Lambda | Per-event-type | Per-subscription | SQS failure |

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

| Error | Cause | Fix |
|---|---|---|
| `InvalidParameter: FIFO topic name must end with .fifo` | FIFO without suffix | Rename with `.fifo` |
| `InvalidParameter: Subscription to FIFO topic requires FIFO SQS queue` | Non-SQS endpoint on FIFO | Use SQS FIFO queue, or Standard topic |
| `KMSAccessDeniedException` | Subscriber lacks `kms:Decrypt` on CMK | Add `kms:Decrypt` + `kms:GenerateDataKey*` to subscriber key policy |
| `AuthorizationError: sns:Subscribe` | Topic policy blocks cross-account | Add foreign account to topic policy |
| Messages not delivered to cross-account SQS | AWS-managed key blocks decrypt | Switch to customer-managed CMK |
| HTTP subscription in `PendingConfirmation` | Endpoint did not confirm within 3 days | Re-subscribe; endpoint must GET SubscribeURL |
| Filter policy silently dropping messages | Non-JSON body with `FilterPolicyScope=MessageBody` | Ensure JSON bodies, or use MessageAttributes |
| Delivery logs not in CloudWatch | Missing CloudWatch Logs resource policy | Add resource policy granting SNS logs permissions |

Full subscription troubleshooting decision tree, per-protocol retry/dead-letter
behavior, and edge-case handling are in `references/troubleshooting-and-error-handling.md`.

## Pre-flight safety checks (run before any deployment CLI)

- **Confirm the topic name is available:** `create-topic` is idempotent —
  returns the ARN if it exists.
- **For FIFO topics, confirm name ends in `.fifo`.** Suffix is permanent.
- **For SSE-KMS, confirm the KMS key exists** and the policy grants
  subscriber access: `aws kms describe-key` + `aws kms get-key-policy`.
- **For cross-account topics, confirm BOTH** topic policy AND subscriber
  IAM/key policies allow access (intersection required).
- **For delivery logging, confirm the CloudWatch IAM role exists** with
  trust policy for `sns.amazonaws.com`.
- **For mobile push, confirm the platform application exists:**
  `aws sns list-platform-applications`.
- **Capture existing configuration for rollback** (if updating):
  `aws sns get-topic-attributes --topic-arn <arn> --output json > backup.json`.
  Topic attributes are not versioned — no undo without backup.

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

Every response MUST be the checklist block below — nothing before it,
nothing after `VERIFICATION_COMMANDS`. The labels are case-sensitive
all-caps keywords.

```text
TOPIC: <topic-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗|OPTIONAL]      Topic type — Standard | FIFO
  [✓|✗]               Encryption — SSE-KMS (key, same-account | cross-account)
  [✓|✗]               Access policy — <pattern: S3 notification | cross-account | IAM-only>
  [✓|✗]               Subscriptions — <count> active (<protocols>)
  [✓|✗]               Delivery logging — <protocols> failure (role: <role-arn>)
  [✓|✗|OPTIONAL]      Filter policy — <summary> | N/A
  [✓|✗|OPTIONAL]      Subscription DLQ — <dlq-arn> | N/A
  [✓|✗|OPTIONAL]      FIFO dedup — ContentBasedDeduplication=<true|false> | N/A
  [✓|✗|OPTIONAL]      Mobile push — <platform ARNs> | N/A
VERIFICATION_COMMANDS:
  <one command per [✓] item>
```

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

```text
TOPIC: order-events-cross-account
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Topic type — Standard (cross-account fan-out, no ordering requirement)
  [✗]      Encryption — alias/aws/sns selected but cross-account subscriber in account 222222222222 needs kms:Decrypt — supply customer-managed CMK with cross-account key policy
  [✓]      Access policy — Cross-account publisher (Principal: account 222222222222, Action: sns:Publish)
  [✗]      Subscriptions — 0 active: SQS queue arn in account 222222222222 not yet subscribed — subscribe the cross-account queue and confirm from the subscriber account
  [✗]      Delivery logging — CloudWatch role SNSDeliveryFeedback not found — create IAM role with trust policy for sns.amazonaws.com + logs:PutLogEvents
  [OPTIONAL] Filter policy — N/A (no filtering needed)
  [OPTIONAL] Subscription DLQ — N/A (SQS has own DLQ)
  [OPTIONAL] FIFO dedup — N/A (Standard topic)
  [OPTIONAL] Mobile push — N/A (no mobile subscribers)
VERIFICATION_COMMANDS:
  aws kms describe-key --key-id alias/my-sns-cross-account-key
  aws kms get-key-policy --key-id alias/my-sns-cross-account-key --policy-name default
  aws sns list-subscriptions-by-topic --topic-arn arn:aws:sns:us-east-1:111111111111:order-events-cross-account
  aws iam get-role --role-name SNSDeliveryFeedback
```

**Self-check before emit:**
- [ ] All 9 checklist rows present (REQUIRED + OPTIONAL)?
- [ ] Cross-account topic uses customer-managed CMK (not alias/aws/sns)?
- [ ] Delivery logging cites BOTH role ARN AND CW Logs resource policy?
- [ ] No subscription in PendingConfirmation marked as active?
- [ ] FIFO topic has `.fifo` suffix and only SQS FIFO subscribers?
- [ ] Every `[✗]` cites the specific gap and what the operator must provide?
- [ ] Literal labels used exactly (no markdown variants)?

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
