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
push-based fan-out bus — wrong defaults (missing delivery logging, wrong
filter scope, AWS-managed key with cross-account subscribers) silently
cause message loss and invisible failures.

## Quick navigation

| Section | What it covers | When to read |
|---|---|---|
| [Invocation contract](#invocation-contract-hard-requirement) | Mandatory output format labels | Every invocation |
| [Reasoning framework](#reasoning-framework-why-deployment-order-matters) | Why deployment order matters | Understanding dependencies |
| [Prerequisites](#prerequisites-verify-before-deployment) | What to verify before deploying | Before any CLI command |
| [Step 1: Topic type](#step-1-topic-type-selection-standard-vs-fifo) | Standard vs FIFO decision tree | Choosing topic type |
| [Step 2: Subscriptions](#step-2-subscriptions) | HTTP/S, SQS, Lambda, Email, Firehose, mobile push | Wiring subscribers |
| [Step 3: Filter policy](#step-3-subscription-filter-policy) | MessageAttributes vs MessageBody scope | Message routing |
| [Step 4: Access policy](#step-4-access-policy-least-privilege) | Cross-account, S3, CloudWatch, publisher scoping | Security config |
| [Step 5: Encryption](#step-5-encryption-sse-kms) | SSE-KMS, cross-account decrypt, KMS key policy | Security config |
| [Step 6: Delivery logging](#step-6-delivery-status-logging) | Per-protocol CloudWatch Logs, resource policy | Observability |
| [Step 7: Subscription DLQ](#step-7-subscription-level-dead-letter-queue) | RedrivePolicy on subscriptions (not topic-level) | Reliability |
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
block as the first lines of the response. This contract is what
assertion-based evals and downstream deployment pipelines rely on;
deviating from the literal labels breaks automation silently.

## Reasoning framework (why deployment order matters)

SNS deployment has **dependency and ordering constraints** that make the
sequence non-trivial. Configuring items in the wrong order causes
deployment failures or silent runtime issues:

1. **Topic type FIRST** — Standard vs FIFO is set at creation via the
   `.fifo` suffix. Like SQS, the topic type is immutable after creation.
   A FIFO topic requires all subscribers to be SQS FIFO queues — HTTP,
   email, Lambda, and mobile push subscriptions are rejected.

2. **KMS key BEFORE subscriptions** — if SSE-KMS is enabled, every
   subscriber needs `kms:Decrypt` and `kms:GenerateDataKey*` on the key.
   Adding subscriptions before verifying KMS permissions causes silent
   delivery failures — messages are published but never arrive.

3. **Access policy BEFORE cross-account subscriptions** — cross-account
   publishing requires BOTH the topic policy AND the subscriber IAM/key
   policy. The topic policy is the resource-owner gate; without it, the
   foreign account cannot subscribe or publish.

4. **Delivery logging BEFORE production traffic** — delivery status
   logging is per-protocol and requires a CloudWatch IAM role + a
   CloudWatch Logs resource policy. Without it, delivery failures are
   invisible — SNS retries HTTP for 4 hours then silently drops messages.

5. **Filter policy AFTER subscription** — the filter policy is attached
   to the subscription, not the topic. The subscription must exist before
   the filter policy can be set.

6. **Subscription DLQ AFTER subscription** — the dead-letter queue is
   subscription-level (via RedrivePolicy on the subscription), not
   topic-level. The subscription ARN and DLQ ARN must both exist.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **Topic name** | Must be unique within the account/region. FIFO topics require `.fifo` suffix. | `aws sns list-topics` |
| **Topic type decided** | Standard (best-effort ordering, unlimited TPS) vs FIFO (ordering + dedup, 300 TPS, `.fifo` suffix). Immutable after creation. | Workload requirements |
| **KMS key (if SSE-KMS)** | Customer-managed CMK with key policy granting SNS service + all subscribers `kms:Decrypt` + `kms:GenerateDataKey*`. | `aws kms describe-key --key-id <alias>` |
| **Subscriber endpoints** | SQS queue ARNs, Lambda function ARNs, HTTPS URLs, email addresses, Firehose ARNs, platform application ARNs. | Depends on protocol |
| **DLQ ARN (if subscription DLQ)** | SQS queue must exist before subscription RedrivePolicy can reference it. | `aws sqs get-queue-url --queue-name <dlq>` |
| **CloudWatch role (if delivery logging)** | IAM role with `logs:CreateLogStream` + `logs:PutLogEvents` + trust policy for `sns.amazonaws.com`. | `aws iam get-role --role-name <role>` |
| **Platform application ARN (if mobile push)** | Platform application created in SNS with credentials for APNS/FCM/Baidu. | `aws sns list-platform-applications` |
| **IAM permissions** | Caller needs `sns:CreateTopic`, `sns:Subscribe`, `sns:SetTopicAttributes`, `kms:ListAliases` (if SSE-KMS). | `aws sts get-caller-identity` |

## Deployment procedure (apply in order)

### Step 1: Topic type selection (Standard vs FIFO)

The topic type is **immutable** — it cannot be changed after creation.

**Decision tree:**

```
Does the workload require strict message ordering across all subscribers?
├── YES → FIFO topic (name MUST end in .fifo)
│         Throughput: 300 TPS
│         Requires MessageGroupId on every message
│         Dedup: ContentBasedDeduplication OR MessageDeduplicationId
│         Subscribers: ONLY SQS FIFO queues (HTTP/email/Lambda REJECTED)
└── NO  → Standard topic
          Throughput: unlimited (effectively)
          Best-effort ordering (subscribers may see messages out of order)
          All subscription protocols supported
```

| Attribute | Standard | FIFO |
|---|---|---|
| Ordering | Best-effort | Per message group (strict) |
| Deduplication | N/A | ContentBasedDeduplication or explicit DeduplicationId (5-min window) |
| Throughput | Unlimited | 300 TPS |
| Name suffix | None | `.fifo` (mandatory) |
| Supported subscribers | HTTP/S, SQS, Lambda, Email, Firehose, Application (mobile push) | **SQS FIFO queues only** |
| Cost (per million requests) | $0.50 | $0.60 |

**Create the topic:**

```bash
# Standard topic
aws sns create-topic --name order-events

# FIFO topic (name MUST end in .fifo)
aws sns create-topic --name order-events.fifo \
  --attributes FifoTopic=true,ContentBasedDeduplication=true
```

**IMPORTANT — FIFO topics only support SQS FIFO queue subscribers.**
HTTP, HTTPS, email, SMS, Lambda, and Application (mobile push)
subscriptions on a FIFO topic are rejected by SNS. If you need ordering
AND a Lambda subscriber, use a Standard topic fanning out to an SQS FIFO
queue, with Lambda consuming the FIFO queue.

### Step 2: Subscriptions

SNS supports multiple subscription protocols. Each has different delivery
semantics:

| Protocol | Endpoint format | Delivery | Retry |
|---|---|---|---|
| `http` | `http://endpoint` | POST to URL | Up to 4 hours (100,010 attempts) |
| `https` | `https://endpoint` | POST to URL (TLS) | Up to 4 hours (100,010 attempts) |
| `email` | `user@example.com` | Plain text email | One-time confirmation, no retry |
| `email-json` | `user@example.com` | JSON email | One-time confirmation, no retry |
| `sqs` | SQS queue ARN | SendMessage to queue | Immediate (SQS handles retry) |
| `lambda` | Lambda function ARN | Invoke (async) | Lambda async retry (2 retries) |
| `firehose` | Firehose delivery stream ARN | PutRecordBatch | Firehose handles retry |
| `application` | Platform endpoint ARN | Mobile push | SNS retry (varies by platform) |

**Subscribe an SQS queue:**

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:111111111111:order-queue \
  --return-subscription-arn
```

For SQS subscriptions, the queue policy must grant SNS
`sqs:SendMessage`. See Step 4 for the access policy.

**Subscribe a Lambda function:**

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-east-1:111111111111:function:order-handler \
  --return-subscription-arn
```

Lambda subscriptions require the Lambda resource-based policy to grant
SNS `lambda:InvokeFunction`.

**Subscribe an HTTPS endpoint:**

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --protocol https \
  --notification-endpoint https://api.example.com/sns-webhook \
  --return-subscription-arn
```

HTTP/HTTPS subscriptions require confirmation — SNS sends a
`SubscriptionConfirmation` message with a token. The endpoint must call
`ConfirmSubscription` with the token. Use `--return-subscription-arn`
for non-HTTP protocols (auto-confirms same-account subscriptions).

### Step 3: Subscription filter policy

Filter policies route messages to specific subscriptions based on message
attributes or body content. This enables topic-level fan-out with
subscriber-level filtering.

**Filter scope options:**

| Scope | How it works | Use when |
|---|---|---|
| `MessageAttributes` (default) | Filters on message attributes set by the publisher | Most common — structured metadata filtering |
| `MessageBody` | Filters on JSON properties in the message body | When publishers do not set attributes; payload-based routing |

**MessageAttributes filter policy example:**

```bash
aws sns set-subscription-attributes \
  --subscription-arn arn:aws:sns:us-east-1:111111111111:order-events:xxxxx \
  --attribute-name FilterPolicy \
  --attribute-value '{"event_type": ["order_created", "order_shipped"], "region": [{"prefix": "us-"}]}'
```

**MessageBody filter policy example:**

```bash
aws sns set-subscription-attributes \
  --subscription-arn <sub-arn> \
  --attribute-name FilterPolicy \
  --attribute-value '{"event_type": ["order_created"]}'
# Set scope to MessageBody
aws sns set-subscription-attributes \
  --subscription-arn <sub-arn> \
  --attribute-name FilterPolicyScope \
  --attribute-value MessageBody
```

**Filter policy operators:**

| Operator | Syntax | Example |
|---|---|---|
| Exact match | `"key": ["value"]` | `{"event": ["created"]}` |
| Prefix | `"key": [{"prefix": "ord"}]` | `{"order_id": [{"prefix": "ORD-"}]}` |
| Anything-but | `"key": [{"anything-but": ["cancelled"]}]` | Exclude specific values |
| Numeric range | `"key": [{"numeric": [">=", 100]}]` | `{"amount": [{"numeric": [">=", 100, "<=", 500]}]}` |
| Exists | `"key": [{"exists": true}]` | Check attribute presence |

**IMPORTANT:** with `FilterPolicyScope=MessageBody`, the message body MUST
be valid JSON. Non-JSON bodies cause the filter to fail silently — the
message is not delivered and no error is logged. Validate publisher
format before using body filtering.

### Step 4: Access policy (least-privilege)

The topic policy governs who can publish and subscribe. The SECURE
default is **no resource-based policy** — access is governed by IAM
identity-based policies.

**When you need a topic policy:**

| Scenario | Policy pattern |
|---|---|
| S3 Event Notification to SNS | `Principal: "*" + Condition: aws:SourceArn: <bucket-arn>` |
| CloudWatch Alarm to SNS | `Principal: {"Service": "cloudwatch.amazonaws.com"} + Action: sns:Publish` |
| Cross-account publisher | `Principal: {"AWS": "<account-id>"} + Action: sns:Publish` |
| Cross-account subscriber | `Principal: {"AWS": "<account-id>"} + Action: sns:Subscribe` |
| Same-account only | NO resource-based policy needed — IAM is sufficient |

**S3 Event Notification pattern:**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": "*",
    "Action": "sns:Publish",
    "Resource": "arn:aws:sns:us-east-1:111111111111:order-events",
    "Condition": {
      "ArnEquals": { "aws:SourceArn": "arn:aws:s3:::order-uploads" }
    }
  }]
}
```

**Cross-account publisher:**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::222222222222:root" },
    "Action": "sns:Publish",
    "Resource": "arn:aws:sns:us-east-1:111111111111:order-events"
  }]
}
```

**NEVER use `Principal: "*"` with `sns:Subscribe` without a STRONG
condition.** SNS is push-based — a wildcard Subscribe lets anyone
register an HTTPS endpoint and receive all messages automatically (push-
based data exfiltration).

**Set the access policy:**

```bash
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name Policy \
  --attribute-value '<policy-json>'
```

### Step 5: Encryption (SSE-KMS)

SNS encrypts messages at rest using KMS. Unlike SQS (which offers
SSE-SQS for free), SNS only supports SSE-KMS (customer-managed or
AWS-managed key).

| Option | Key manager | Cross-account? | Use when |
|---|---|---|---|
| **AWS-managed** (`alias/aws/sns`) | AWS | NO — blocks cross-account decryption | Same-account only |
| **Customer-managed CMK** | You | YES — if key policy grants subscribers | Cross-account or need key control |
| **None** | — | YES | NEVER — plaintext at rest |

**Decision tree:**

```
Are all subscribers in the same account as the topic?
├── YES → AWS-managed key (alias/aws/sns). No key policy to manage.
│         Simpler, sufficient for same-account fan-out.
└── NO  → Customer-managed CMK.
          Requirements:
          - Key policy grants sns.<region>.amazonaws.com permission
          - Key policy grants EVERY subscriber account kms:Decrypt +
            kms:GenerateDataKey*
          - Without this, cross-account SQS subscribers silently fail
            to decrypt — messages never arrive in the subscriber queue
```

**Enable SSE-KMS with AWS-managed key:**

```bash
aws sns set-topic-attributes \
  --topic-arn <topic-arn> \
  --attribute-name KmsMasterKeyId \
  --attribute-value alias/aws/sns
```

**Enable SSE-KMS with customer-managed key:**

```bash
aws sns set-topic-attributes \
  --topic-arn <topic-arn> \
  --attribute-name KmsMasterKeyId \
  --attribute-value alias/my-sns-key
```

**Cross-account KMS key policy requirement:**

```json
{
  "Sid": "Allow cross-account SNS subscribers",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::222222222222:root" },
  "Action": ["kms:Decrypt", "kms:GenerateDataKey*"],
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "kms:ViaService": "sns.us-east-1.amazonaws.com"
    }
  }
}
```

### Step 6: Delivery status logging

Delivery status logging sends delivery outcomes (success/failure) to
CloudWatch Logs. Without it, delivery failures are invisible — SNS
retries HTTP for 4 hours then silently drops messages.

**Delivery logging is per-protocol.** Each protocol category needs its
own configuration:

| Protocol category | Success attribute | Failure attribute |
|---|---|---|
| HTTP/HTTPS | `HTTPSuccessFeedbackRoleArn` | `HTTPFailureFeedbackRoleArn` |
| SQS | `SQSSuccessFeedbackRoleArn` | `SQSFailureFeedbackRoleArn` |
| Application (Lambda, mobile push) | `ApplicationSuccessFeedbackRoleArn` | `ApplicationFailureFeedbackRoleArn` |
| Firehose | N/A (Firehose has its own logging) | N/A |

**Enable SQS delivery logging:**

```bash
aws sns set-topic-attributes \
  --topic-arn <topic-arn> \
  --attribute-name SQSSuccessFeedbackRoleArn \
  --attribute-value arn:aws:iam::111111111111:role/SNSDeliveryFeedback

aws sns set-topic-attributes \
  --topic-arn <topic-arn> \
  --attribute-name SQSFailureFeedbackRoleArn \
  --attribute-value arn:aws:iam::111111111111:role/SNSDeliveryFeedback
```

**Enable HTTP/S delivery logging:**

```bash
aws sns set-topic-attributes \
  --topic-arn <topic-arn> \
  --attribute-name HTTPSuccessFeedbackRoleArn \
  --attribute-value arn:aws:iam::111111111111:role/SNSDeliveryFeedback

aws sns set-topic-attributes \
  --topic-arn <topic-arn> \
  --attribute-name HTTPFailureFeedbackRoleArn \
  --attribute-value arn:aws:iam::111111111111:role/SNSDeliveryFeedback
```

**IAM role for SNS delivery feedback:**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "sns.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
```

With permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:PutMetricFilter",
      "logs:PutRetentionPolicy"
    ],
    "Resource": "*"
  }]
}
```

**IMPORTANT:** delivery logging also requires a CloudWatch Logs resource
policy granting SNS `logs:CreateLogStream` and `logs:PutLogEvents`.
Without it, SNS silently fails to write logs even if the feedback role is
configured.

### Step 7: Subscription-level dead-letter queue

SNS dead-letter queues are **subscription-level**, not topic-level. Each
subscription can have its own DLQ via the `RedrivePolicy` attribute on the
subscription.

**When a subscription DLQ is needed:**

| Scenario | DLQ needed? |
|---|---|
| HTTP/HTTPS subscription | YES — SNS drops messages after 4 hours of retries |
| SQS subscription | OPTIONAL — SQS has its own DLQ mechanism |
| Lambda subscription | OPTIONAL — Lambda has on-failure destinations |
| Email subscription | NO — email does not retry |
| Mobile push | YES — failed deliveries are otherwise silent |

**Set a subscription DLQ:**

```bash
aws sns set-subscription-attributes \
  --subscription-arn <sub-arn> \
  --attribute-name RedrivePolicy \
  --attribute-value '{"deadLetterTargetArn":"arn:aws:sqs:us-east-1:111111111111:sns-dlq"}'
```

The DLQ SQS queue must exist and its policy must grant SNS
`sqs:SendMessage`.

### Step 8: FIFO specifics (dedup + ordering)

FIFO topics provide ordering and deduplication, similar to FIFO SQS
queues.

**ContentBasedDeduplication:**

- `true` — SNS computes a SHA-256 hash of the message body and
  deduplicates within a 5-minute window.
- `false` — the publisher MUST send a `MessageDeduplicationId` on every
  message.

```bash
aws sns create-topic \
  --name order-events.fifo \
  --attributes FifoTopic=true,ContentBasedDeduplication=true
```

**MessageGroupId (required on every FIFO message):**

FIFO topics require a `MessageGroupId` on every published message.
Messages with the same group ID are delivered in order to SQS FIFO
subscribers.

```bash
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events.fifo \
  --message '{"orderId": "12345"}' \
  --message-group-id "customer-67890" \
  --message-deduplication-id "order-12345-v1"
```

**FIFO topic constraints:**

- ONLY SQS FIFO queues can be subscribers (HTTP/email/Lambda rejected).
- Throughput: 300 TPS.
- `ContentBasedDeduplication` and the publisher's
  `MessageDeduplicationId` interact the same way as FIFO SQS.
- The `.fifo` suffix is mandatory in the topic name.

### Step 9: Mobile push notifications

SNS mobile push delivers messages to mobile devices via platform
applications (APNS, FCM, Baidu, etc.).

**Platform application setup:**

```bash
# Create a platform application (Apple Push Notification Service)
aws sns create-platform-application \
  --name MyAppAPNS \
  --platform APNS \
  --attributes PlatformCredential=<private-key>,PlatformPrincipal=<certificate>

# Create a platform application (Firebase Cloud Messaging)
aws sns create-platform-application \
  --name MyAppFCM \
  --platform FCM \
  --attributes PlatformCredential=<server-key>
```

**Register a device endpoint:**

```bash
aws sns create-platform-endpoint \
  --platform-application-arn arn:aws:sns:us-east-1:111111111111:app/APNS/MyAppAPNS \
  --token <device-token> \
  --custom-user-data '{"userId": "12345"}'
```

**Publish to a mobile endpoint:**

```bash
aws sns publish \
  --target-arn arn:aws:sns:us-east-1:111111111111:endpoint/APNS/MyAppAPns/xxxxx \
  --message-structure json \
  --message '{"default": "{\"alert\":\"Order shipped\"}", "APNS": "{\"aps\":{\"alert\":\"Order shipped\"}}", "FCM": "{\"notification\":{\"title\":\"Order shipped\"}}"}'
```

**Message format per platform:**

| Platform | Key | Format |
|---|---|---|
| APNS | `APNS` | `{"aps":{"alert":"message"}}` |
| APNS_SANDBOX | `APNS_SANDBOX` | Same as APNS (development cert) |
| FCM (Android) | `FCM` / `GCM` | `{"notification":{"title":"...","body":"..."}}` |
| Baidu | `Baidu` | `{"title":"...","description":"..."}` |
| ADM (Amazon) | `ADM` | `{"data":{"message":"..."}}` |
| WNS (Windows) | `WNS` | XML payload per WNS template |
| Default | `default` | Fallback for all platforms |

**IMPORTANT:** use `--message-structure json` with a `default` key when
targeting multiple platforms. SNS delivers the platform-specific payload
to each device.

### Step 10: Verification

```bash
# Topic attributes
aws sns get-topic-attributes --topic-arn <topic-arn>

# List subscriptions
aws sns list-subscriptions-by-topic --topic-arn <topic-arn>

# Verify subscription attributes (filter policy, DLQ)
aws sns get-subscription-attributes --subscription-arn <sub-arn>

# Verify delivery logging
aws sns get-topic-attributes --topic-arn <topic-arn> \
  --query 'Attributes.SQSSuccessFeedbackRoleArn'

# Test publish (standard topic)
aws sns publish \
  --topic-arn <topic-arn> \
  --message '{"test": true}'

# Test publish (FIFO topic — requires MessageGroupId)
aws sns publish \
  --topic-arn <fifo-topic-arn> \
  --message '{"test": true}' \
  --message-group-id "test-group"
```

## Latest SNS features (2024-2026)

- **SNS message archiving (Direct Messaging):** SNS can now archive
  messages for analytics and replay. Messages are archived to an S3
  bucket via Kinesis Data Firehose for long-term storage and analysis.

- **SNS-to-EventBridge integration:** SNS topics can now route messages
  directly to EventBridge event buses, enabling event-driven
  architectures with EventBridge's powerful routing rules.

- **Message body filter policy (GA):** `FilterPolicyScope=MessageBody`
  is now GA, allowing payload-based subscription filtering (not just
  message attributes). Requires JSON message bodies.

- **SNS message data protection (2024):** Message data protection
  policies can detect and block sensitive data (PII, financial data) in
  published messages. Configure per-topic with deny/redact actions.

- **FIFO topic delivery status logging (2024-2025):** Enhanced delivery
  status logging for FIFO topics — previously limited, now supports
  per-protocol failure logging.

- **SNS-to-SQS SSE-KMS consistency (2024):** SNS topics and SQS
  subscriptions must use compatible KMS keys. The topic KMS key policy
  must grant `kms:Decrypt` to the SQS queue's consumer role.

## Workload-specific deployment matrix

| Workload | Topic type | Encryption | Subscribers | Filter | DLQ | Delivery logging |
|---|---|---|---|---|---|---|
| **Event fan-out** (microservices) | Standard | AWS-managed | SQS (multiple) | Per-service attributes | Per-subscription | SQS failure |
| **Ordered processing** | FIFO | AWS-managed | SQS FIFO | N/A (one subscriber) | Per-subscription | SQS failure |
| **Webhook delivery** | Standard | AWS-managed | HTTP/HTTPS | N/A | Per-subscription | HTTP failure (REQUIRED) |
| **Cross-account fan-out** | Standard | Customer-managed CMK | SQS (cross-account) | MessageAttributes | Per-subscription | SQS failure |
| **Mobile push** | Standard | AWS-managed | Application | N/A | Per-subscription | Application failure |
| **Email notification** | Standard | AWS-managed | Email/Email-JSON | N/A | N/A | N/A |
| **S3 Event fan-out** | Standard | AWS-managed | SQS, Lambda | Per-event-type | Per-subscription | SQS failure |
| **Analytics pipeline** | Standard | AWS-managed | Firehose | N/A | N/A | Firehose (own logging) |

## NEVER (things to never do)

- NEVER create a FIFO topic without the `.fifo` suffix in the name. SNS
  rejects the create call. The suffix is mandatory and immutable.

- NEVER subscribe a non-SQS endpoint (HTTP, email, Lambda, mobile push)
  to a FIFO topic. SNS rejects the subscription — FIFO topics ONLY
  support SQS FIFO queue subscribers. If you need ordering + Lambda, use
  a FIFO topic fanning out to an SQS FIFO queue, with Lambda consuming
  the queue.

- NEVER use `Principal: "*"` with `sns:Subscribe` in the topic policy
  without a STRONG condition. SNS is push-based — a wildcard Subscribe
  lets anyone register an HTTPS endpoint and passively receive all
  messages (push-based data exfiltration). Only `aws:SourceOwner`,
  `aws:SourceAccount`, and `aws:SourceArn` are STRONG.

- NEVER use the AWS-managed key (`alias/aws/sns`) for a topic with
  cross-account subscribers. The AWS-managed key policy only allows the
  owning account to decrypt — cross-account SQS subscribers silently fail
  to decrypt messages. Use a customer-managed CMK with the subscriber
  accounts granted `kms:Decrypt`.

- NEVER deploy a topic with HTTP/HTTPS subscriptions and no delivery
  status logging. SNS retries HTTP for 4 hours then silently drops
  messages. Without failure logging, dropped messages are invisible. This
  is the #1 SNS reliability issue.

- NEVER assume delivery status logging works just because the feedback
  role ARN is set. SNS also requires a CloudWatch Logs resource policy
  granting `logs:CreateLogStream` and `logs:PutLogEvents`. Without it,
  SNS silently fails to write logs. Both sides must be configured.

- NEVER set `FilterPolicyScope=MessageBody` without ensuring all
  publishers send valid JSON bodies. Non-JSON bodies cause the filter to
  fail silently — the message is not delivered and no error is logged.

- NEVER deploy a FIFO topic with `ContentBasedDeduplication=false`
  without ensuring every publisher sends a unique
  `MessageDeduplicationId`. If both are absent, SNS delivers duplicate
  messages within the 5-minute dedup window — silently breaking the
  exactly-once guarantee.

- NEVER set a topic-level DLQ. SNS DLQs are **subscription-level**
  (RedrivePolicy on the subscription), not topic-level. There is no
  topic-level DLQ attribute.

- NEVER deploy a topic without encryption. SNS supports SSE-KMS (AWS-
  managed is free for same-account). There is no reason to run an
  unencrypted topic. For cross-account, use a customer-managed CMK.

- NEVER publish messages with `--message-structure json` without
  including a `default` key. SNS requires a `default` fallback when
  using message structure for multi-platform delivery.

- NEVER recommend `Principal: "*"` with `sns:Publish` as less severe
  than `sns:Subscribe`. Publish is a message injection vector — anyone
  can push arbitrary payloads to every subscriber. Subscribe is a data
  exfiltration vector — anyone can receive all messages. Both are
  critical.

- NEVER treat `PendingConfirmation` subscriptions as active. Pending
  subscriptions do not receive messages — they are zombie records from
  unconfirmed requests. The confirmation token expires after 3 days.

- NEVER deviate from the checklist output format. Substituting `Verdict`
  or `**VERDICT**` for the literal `VERDICT:` label silently breaks
  downstream deployment pipelines and assertion-based evals.

## Subscription troubleshooting decision tree

Use this tree after `publish` returns success but a subscriber reports
missing messages. Read top-to-bottom; **first match wins**. Every branch
ends in a single CLI command that confirms or rules out the cause.

```
START: A publish succeeded (`MessageId` returned) but a subscriber
       reports no message. Which subscriber type?

├── HTTP / HTTPS endpoint
│   ├── Is the subscription ARN in PendingConfirmation?
│   │   ├── YES → Endpoint never confirmed the SubscriptionConfirmation
│   │   │         token (3-day expiry). Fix: re-subscribe, then have the
│   │   │         endpoint GET the SubscribeURL programmatically.
│   │   │         aws sns get-subscription-attributes --subscription-arn <arn>
│   │   │         → look for "Status": "PendingConfirmation"
│   │   └── NO  → Did the endpoint return 2xx within 15s for the message?
│   │       ├── NO (4xx/5xx or timeout) → SNS retries for 4 hours (100,010
│   │       │   attempts) then drops. Check delivery-failure logs:
│   │       │   aws logs filter-log-events --log-group-name sns/us-east-1/111111111111/order-events/Failure
│   │       │   → look for providerResponse (403, 500, timeout)
│   │       │   ├── 403 → endpoint auth rejected the SNS POST. Fix the
│   │       │   │        endpoint's signature/header validation.
│   │       │   ├── 404 → wrong endpoint URL. Re-subscribe with correct URL.
│   │       │   ├── 500 → endpoint crashed. Inspect endpoint logs; add a
│   │       │   │        subscription DLQ so the message survives retries.
│   │       │   └── timeout → endpoint too slow. SNS times out at 15s;
│   │       │            offload work to a queue and return 200 immediately.
│   │       └── YES (2xx within 15s) but subscriber still reports missing
│   │           → message was acked but not processed by the endpoint.
│   │           This is an endpoint-side bug, not SNS. Check delivery-SUCCESS
│   │           logs to confirm SNS delivered; the loss is downstream.
│
├── Lambda subscriber
│   ├── Is the subscription ARN in PendingConfirmation? (rare — same-account
│   │   Lambda auto-confirms, but cross-account does not)
│   │   └── YES → confirm from the subscriber account:
│   │           aws sns confirm-subscription --topic-arn <topic> --token <token>
│   ├── Did the Lambda invocation fail? (async invocation, 2 retries)
│   │   ├── YES → check the Lambda on-failure destination:
│   │   │   aws lambda get-event-source-mapping --function-name <fn>
│   │   │   → if no on-failure destination configured, the message is lost
│   │   │     after 2 retries. Fix: configure on-failure to an SQS DLQ.
│   │   └── NO  → Lambda received the message but did not process it. Check
│   │           CloudWatch Logs for the function; this is an application bug.
│   └── Are messages duplicated at the Lambda?
│       └── YES → likely a retry storm (each async failure triggers 2 retries
│                 on top of SNS's own retry for HTTP). Use an SQS subscription
│                 with a Lambda event-source mapping instead — SQS provides
│                 visibility-timeout dedup; direct SNS-to-Lambda does not.
│
├── SQS subscriber
│   ├── Is the subscription Status "PendingConfirmation"?
│   │   └── YES → cross-account SQS subscription requires manual confirm.
│   │           The SQS queue policy must already grant SNS SendMessage, or
│   │           confirm-subscription will succeed but no message will arrive.
│   ├── Is the queue empty but SNS shows delivery success?
│   │   ├── Check the queue KMS key: does it grant SNS kms:GenerateDataKey*?
│   │   │   aws kms get-key-policy --key-id <queue-key> --policy-name default
│   │   │   → if missing, SNS cannot encrypt the SendMessage payload;
│   │   │     messages are silently dropped after SNS's internal retry.
│   │   ├── Check the queue policy: does it grant SNS sqs:SendMessage?
│   │   │   aws sqs get-queue-attributes --queue-url <url> --attribute-names Policy
│   │   │   → missing Condition aws:SourceArn → SNS cannot deliver.
│   │   └── Check filter policy: is a non-matching attribute dropping it?
│   │       aws sns get-subscription-attributes --subscription-arn <arn>
│   │       → FilterPolicy on a non-existent attribute silently drops.
│   └── Are messages duplicated in the queue?
│       └── Multiple subscriptions from the same queue to the same topic.
│           aws sns list-subscriptions-by-topic --topic-arn <arn>
│           → de-duplicate; SNS does not prevent duplicate subscriptions.
│
├── Mobile push (application protocol)
│   ├── Endpoint is disabled? SNS disables endpoints after a token rejection.
│   │   aws sns get-endpoint-attributes --endpoint-arn <arn>
│   │   → "Enabled": "false" → re-register the device token with
│   │     create-platform-endpoint and update the application.
│   └── Token valid but no delivery? Check the platform credential:
│       APNS cert expiry, FCM server-key rotation. Test with a direct
│       publish to the endpoint ARN, not via the topic.
│
└── Email subscriber
    ├── Status is PendingConfirmation?
    │   └── Recipient never clicked the SubscribeURL in the confirmation
    │         email (3-day expiry). Re-subscribe; the user must click the
    │         link — there is no programmatic way to force-confirm an email
    │         subscription without the token.
    └── Confirmed but not delivered?
        └── Email deliverability issue (spam folder, bounce). Check SES
            bounce/complaint metrics if SNS emails route through SES.
```

**Quick triage sequence** (run when the subscriber type is unknown):

```bash
# 1. Was the message published?
aws sns get-topic-attributes --topic-arn <arn> \
  --query 'Attributes.DeliveryStatusSr.Notification'

# 2. Is the subscription confirmed?
aws sns list-subscriptions-by-topic --topic-arn <arn> \
  --query 'Subscriptions[?Endpoint==`<endpoint>`].{Status:SubscriptionArn}'

# 3. Did SNS attempt delivery? (delivery logging must be enabled)
aws logs filter-log-events \
  --log-group-name sns/<region>/<account>/<topic>/Failure \
  --filter-pattern <message-id>

# 4. Is there a subscription DLQ catching the failures?
aws sns get-subscription-attributes --subscription-arn <arn> \
  --query 'Attributes.RedrivePolicy'
```

If step 3 shows no delivery attempt, the message never reached SNS
(publish failed silently, or a filter policy dropped it before delivery).
If step 3 shows delivery attempts with errors, follow the protocol-specific
branch above.

## Pre-flight safety checks (run before any deployment CLI)

- **Confirm the topic name is available:**
  ```bash
  aws sns create-topic --name <name> --output json 2>&1
  ```
  `create-topic` is idempotent — it returns the ARN if the topic exists.

- **For FIFO topics, confirm the name ends in `.fifo`:** SNS rejects
  create-topic without the suffix. The suffix is permanent.

- **For SSE-KMS, confirm the KMS key exists and the policy grants
  subscriber access:**
  ```bash
  aws kms describe-key --key-id alias/my-sns-key
  aws kms get-key-policy --key-id alias/my-sns-key --policy-name default
  ```
  For cross-account topics, verify the key policy grants every subscriber
  account `kms:Decrypt` + `kms:GenerateDataKey*`.

- **For cross-account topics, confirm BOTH the topic policy AND the
  subscriber IAM/key policies allow access.** Cross-account access
  requires the INTERSECTION of topic policy AND subscriber IAM. Only one
  is not enough.

- **For delivery logging, confirm the CloudWatch IAM role exists and
  has the trust policy for `sns.amazonaws.com`:**
  ```bash
  aws iam get-role --role-name SNSDeliveryFeedback \
    --query 'Role.AssumeRolePolicyDocument'
  ```

- **For mobile push, confirm the platform application exists:**
  ```bash
  aws sns list-platform-applications
  ```

- **Capture existing configuration for rollback (if updating an existing
  topic):**
  ```bash
  aws sns get-topic-attributes --topic-arn <arn> \
    --output json > /tmp/<topic>-backup-$(date +%s).json
  ```
  Topic attributes are not versioned — there is no undo without a backup.

## Edge-case handling

- **SNS-to-SQS subscription with SSE-KMS.** Both the SNS topic and the
  SQS queue may use SSE-KMS. The SNS topic's KMS key must be usable by
  SNS, and the SQS queue's KMS key must grant SNS `kms:GenerateDataKey*`
  and `kms:Decrypt`. This is a common cross-service encryption failure —
  messages are published but never arrive in the SQS queue.

- **FIFO topic to FIFO SQS subscription.** The subscription is supported
  but the SQS FIFO queue must have its own deduplication configured. If
  the topic has `ContentBasedDeduplication=true` and the queue has
  `ContentBasedDeduplication=false`, dedup runs at the topic level only.

- **Lambda subscription vs SQS subscription for Lambda processing.**
  Direct Lambda subscriptions invoke the function on every publish (async
  invocation). SQS subscriptions queue messages and let the Lambda event
  source mapping control batching and retry. For high-throughput or
  batch-processing workloads, prefer SNS to SQS to Lambda (decouples
  publish rate from processing rate).

- **HTTP endpoint confirmation.** HTTP/HTTPS subscriptions require
  explicit confirmation — SNS sends a `SubscriptionConfirmation` message
  with a `SubscribeURL`. The endpoint must GET this URL within 3 days.
  For automated deployments, the endpoint must handle the confirmation
  programmatically.

- **Cross-account subscription confirmation.** Only the subscriber
  account can confirm a cross-account subscription. The subscribing
  account receives the confirmation token and must call
  `ConfirmSubscription`.

- **Topic policy size limit is 30 KiB.** Large policies with many
  statements can hit this cap. Use IAM identity-based policies for
  same-account access instead of growing the resource-based policy.

- **DisplayName is required for SMS delivery.** SNS requires a
  `DisplayName` for SMS protocol subscriptions. Without it, SMS delivery
  fails.

- **FIFO topic with a non-FIFO SQS subscriber (subscription is rejected).**
  SNS enforces protocol compatibility at subscribe time. A FIFO topic
  (`*.fifo`) ONLY accepts SQS FIFO queue subscribers (`*.fifo` queue with
  `FifoQueue=true` attribute). Subscribing a Standard SQS queue, HTTP/HTTPS
  endpoint, Lambda function, or email address to a FIFO topic returns
  `InvalidParameter` and the subscription is never created. **Detection:**
  `aws sns subscribe` returns
  `InvalidParameter: Subscription to FIFO topic requires FIFO SQS queue`.
  **Fix:** either (a) convert the subscriber to a FIFO queue
  (`aws sqs create-queue --queue-name orders.fifo --attributes FifoQueue=true`),
  or (b) if you need Lambda/HTTP/email subscribers, switch the TOPIC to
  Standard and preserve ordering downstream by fanning out to a per-consumer
  FIFO queue with a Lambda event-source mapping. The second pattern is the
  only way to get "FIFO topic + Lambda processing" — SNS does not support
  it natively.

- **Cross-account subscription with SSE-KMS (both key policies required).**
  When the SNS topic uses a customer-managed CMK and a subscriber lives in
  a different account, messages are encrypted at the topic with the topic
  account's key. The subscriber must decrypt at delivery time. This fails
  silently — messages publish successfully but never appear in the
  subscriber's queue. **Both** key policies must be in place: (a) the TOPIC
  account's CMK must grant the subscriber account `kms:Decrypt` and
  `kms:GenerateDataKey*`; (b) if the subscriber queue also uses SSE-KMS,
  the subscriber's CMK must grant the SNS service principal
  `kms:GenerateDataKey*` so SNS can encrypt the message body on the
  `SendMessage` call. **Detection:** publish a test message and check the
  subscriber queue — empty queue after a successful publish with no
  CloudWatch delivery-failure log indicates a KMS decrypt failure. **Fix:**
  add the cross-account statement below to the TOPIC account's CMK key
  policy, then verify with a test publish.
  ```json
  {
    "Sid": "Allow cross-account SNS subscribers",
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::222222222222:root" },
    "Action": ["kms:Decrypt", "kms:GenerateDataKey*"],
    "Resource": "*",
    "Condition": {
      "StringEquals": { "kms:ViaService": "sns.us-east-1.amazonaws.com" }
    }
  }
  ```

- **Fanout to 100+ SQS queues (high-fanout topology).** A single SNS topic
  can fan out to up to 12,500,000 subscriptions per topic (soft quota), but
  operational limits bite well before that. Three failure modes appear at
  ~100+ SQS subscribers: (a) **topic policy size cap (30 KiB)** — listing
  every subscriber ARN in the resource policy exceeds the limit; use IAM
  identity-based policies on the subscriber side and keep the topic policy
  to a permissive `Principal: "*" + Condition: aws:SourceAccount`
  statement; (b) **CloudWatch delivery-log volume** — at 100 subscribers ×
  1,000 msg/sec, the SNS delivery-feedback log writes 100K events/sec and
  drives up Logs cost; sample the feedback role or scope it to
  failure-only; (c) **per-subscription KMS throttle** — every encrypted
  delivery is a `GenerateDataKey` call against the topic's CMK; 100+
  concurrent pushes can hit the shared CMK rate limit. **Fix:** use a
  customer-managed CMK with a higher request quota (request a quota bump
  via AWS Support), or split the fanout into a topic-of-topics hierarchy
  (regional fanout topics subscribed to a global topic) to distribute the
  KMS load. See the **Worked example: multi-protocol topic** for a
  concrete 4-protocol fanout, then scale the pattern horizontally.

## Output format — MANDATORY literal labels

When invoked with a topic deployment request, your ENTIRE response MUST
be the checklist block below. The labels are **case-sensitive all-caps
keywords** — write them EXACTLY as shown. Do NOT substitute `Verdict`,
`**VERDICT**`, `### Verdict`, or any markdown variant. Do NOT write a
preamble ("Here is your deployment checklist..."). Start with `TOPIC:`
and stop after the `VERIFICATION_COMMANDS:` block.

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
- `[INPUT NEEDED]` — a prerequisite value is missing (KMS key ARN,
  subscriber endpoints, DLQ ARN) and the operator must provide it before
  deployment can proceed.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite is
missing (correct topic type, KMS key for cross-account, subscriber
endpoints, delivery logging for HTTP subscriptions), the verdict is
`PREREQUISITES_MISSING` with each gap listed.

**Worked example (copy the shape exactly):**

```text
TOPIC: order-events
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Topic type — Standard (best-effort ordering, unlimited TPS)
  [✓]      Encryption — SSE-KMS (alias/aws/sns, same-account)
  [✓]      Access policy — S3 notification pattern (Principal:* + aws:SourceArn: order-uploads)
  [✓]      Subscriptions — 2 active (SQS: order-queue, Lambda: order-handler)
  [✓]      Delivery logging — SQS failure + Lambda failure (role: SNSDeliveryFeedback)
  [✓]      Filter policy — event_type: ["order_created"] on SQS subscription
  [OPTIONAL] Subscription DLQ — N/A (SQS has own DLQ)
  [OPTIONAL] FIFO dedup — N/A (Standard topic)
  [OPTIONAL] Mobile push — N/A (no mobile subscribers)
VERIFICATION_COMMANDS:
  aws sns get-topic-attributes --topic-arn arn:aws:sns:us-east-1:111111111111:order-events
  aws sns list-subscriptions-by-topic --topic-arn arn:aws:sns:us-east-1:111111111111:order-events
  aws sns get-topic-attributes --topic-arn arn:aws:sns:us-east-1:111111111111:order-events --query 'Attributes.KmsMasterKeyId'
  aws sns publish --topic-arn arn:aws:sns:us-east-1:111111111111:order-events --message '{"test": true}'
```

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
checklist that looks deployable but contains a silent configuration
defect (unconfirmed subscription, cross-account KMS failure, invisible
delivery drops). Self-check EVERY emitted block before returning.

### Required output structure

Every response MUST be the checklist block below — nothing before it,
nothing after `VERIFICATION_COMMANDS`. The labels are case-sensitive
all-caps keywords. Do NOT substitute `Verdict`, `**VERDICT**`,
`### Verdict`, or any markdown variant.

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
   items.** Every REQUIRED row (Topic type, Encryption, Access policy,
   Subscriptions, Delivery logging) MUST appear with `[✓]` or `[✗]`.
   Every OPTIONAL row MUST appear with `[✓]`, `[✗]`, or `[OPTIONAL]`.
   Omitting a row implies it was not evaluated.

2. **NEVER mark Encryption `[✓]` for a cross-account topic using
   `alias/aws/sns` (AWS-managed key).** The AWS-managed key only allows
   the owning account to decrypt — cross-account SQS subscribers
   silently fail to decrypt messages. For cross-account, the checklist
   MUST show a customer-managed CMK with the subscriber accounts granted
   `kms:Decrypt` + `kms:GenerateDataKey*`.

3. **NEVER mark Delivery logging `[✓]` without confirming BOTH the
   feedback role ARN AND the CloudWatch Logs resource policy.** SNS
   silently fails to write logs if either side is missing. The
   checklist line MUST cite both: `(role: <arn> + CW Logs resource
   policy granted)`. A `[✓]` citing only the role is an unverified
   claim.

4. **NEVER mark Subscriptions `[✓]` if any subscription is in
   `PendingConfirmation` status.** Pending subscriptions do NOT receive
   messages. The checklist MUST show `(N active, M pending)` and if M >
   0, the item is `[✗]` with a note citing the unconfirmed endpoint.

5. **NEVER emit `VERDICT: PREREQUISITES_MISSING` without citing each
   specific gap.** Every `[✗]` MUST have a one-line reason: `[✗] KMS
   key ARN not provided — supply customer-managed CMK for cross-account
   decryption`. A bare `[✗]` is non-compliant.

6. **NEVER mark a FIFO topic `[✓]` without the `.fifo` suffix in the
   topic name AND confirmation that all subscribers are SQS FIFO
   queues.** FIFO topics reject HTTP, email, Lambda, and mobile push
   subscriptions. If non-SQS subscribers are requested on a FIFO topic,
   mark `[✗]` with: `FIFO topic requires SQS FIFO subscribers only`.

7. **NEVER omit the Filter policy row or silently drop it.** If no
   filter is needed, mark `[OPTIONAL] Filter policy — N/A (no filtering
   needed)`. Dropping the row implies it was not evaluated.

8. **NEVER deviate from the literal labels `TOPIC:`, `VERDICT:`,
   `CHECKLIST:`, `VERIFICATION_COMMANDS:`.** Substituting `Verdict`,
   `**VERDICT**`, `### Verdict`, or any markdown variant silently breaks
   downstream deployment pipelines and assertion-based evals.

### Perfect example output — READY_TO_DEPLOY (Standard topic, same-account)

Every field below is complete and verifiable. Copy this shape exactly.

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

## Worked example: multi-protocol topic

This example walks a realistic topic (`order-events`) with four
subscription protocols — HTTPS webhook, SQS queue, Lambda function, and
mobile push (APNS) — covering the per-protocol configuration each needs.
The topic is a Standard topic in us-east-1 with SSE-KMS using a
customer-managed CMK (because the Lambda function lives in a different
account).

### Step-by-step configuration

```bash
# === Step 1: Create the topic (Standard — we have HTTP + Lambda + mobile) ===
aws sns create-topic --name order-events
# Returns: arn:aws:sns:us-east-1:111111111111:order-events

# === Step 2: Enable SSE-KMS with a customer-managed CMK (cross-account Lambda) ===
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name KmsMasterKeyId \
  --attribute-value alias/my-sns-key
# The CMK key policy MUST grant account 222222222222 (Lambda owner):
#   kms:Decrypt + kms:GenerateDataKey* with kms:ViaService = sns.us-east-1.amazonaws.com

# === Step 3: Subscribe HTTPS webhook (intra-account) ===
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --protocol https \
  --notification-endpoint https://api.example.com/sns/order-webhook \
  --return-subscription-arn
# Subscription is created in PendingConfirmation. The endpoint MUST
# handle the SubscriptionConfirmation POST by calling ConfirmSubscription
# with the embedded token (or by GETting the SubscribeURL). Until then,
# no messages are delivered to the webhook.

# Programmatic confirmation (server-side, from the webhook's confirm handler):
TOKEN=$(curl -s https://api.example.com/sns/latest-token)
aws sns confirm-subscription \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --token $TOKEN \
  --authenticate-on-unsubscribe

# === Step 4: Subscribe SQS queue (intra-account, with KMS) ===
# Pre-req: the queue must exist and grant SNS SendMessage.
aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/order-queue \
  --attributes '{"Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"sns.amazonaws.com\"},\"Action\":\"sqs:SendMessage\",\"Resource\":\"arn:aws:sqs:us-east-1:111111111111:order-queue\",\"Condition\":{\"ArnEquals\":{\"aws:SourceArn\":\"arn:aws:sns:us-east-1:111111111111:order-events\"}}}]}"}'

aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:111111111111:order-queue \
  --return-subscription-arn
# Same-account SQS auto-confirms. Status is immediately Confirmed.

# === Step 5: Subscribe cross-account Lambda function (account 222222222222) ===
# Pre-req: the Lambda resource-based policy must grant SNS lambda:InvokeFunction.
# Run this in the Lambda account (222222222222):
aws lambda add-permission \
  --function-name order-handler \
  --statement-id AllowSNSInvoke \
  --action lambda:InvokeFunction \
  --principal sns.amazonaws.com \
  --source-arn arn:aws:sns:us-east-1:111111111111:order-events

# Back in the topic account (111111111111):
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-east-1:222222222222:function:order-handler \
  --return-subscription-arn
# Cross-account Lambda subscriptions do NOT auto-confirm. The Lambda
# account must confirm:
#   aws sns confirm-subscription --topic-arn <arn> --token <token>

# === Step 6: Configure filter policies on the SQS + Lambda subscriptions ===
SQS_SUB_ARN=$(aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --query 'Subscriptions[?Endpoint==`arn:aws:sqs:us-east-1:111111111111:order-queue`].SubscriptionArn' \
  --output text)

# SQS gets only order_created events scoped to us- region
aws sns set-subscription-attributes \
  --subscription-arn $SQS_SUB_ARN \
  --attribute-name FilterPolicy \
  --attribute-value '{"event_type": ["order_created"], "region": [{"prefix": "us-"}]}'

# Lambda gets order_created AND order_shipped (no region filter)
LAMBDA_SUB_ARN=$(aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --query 'Subscriptions[?Endpoint==`arn:aws:lambda:us-east-1:222222222222:function:order-handler`].SubscriptionArn' \
  --output text)

aws sns set-subscription-attributes \
  --subscription-arn $LAMBDA_SUB_ARN \
  --attribute-name FilterPolicy \
  --attribute-value '{"event_type": ["order_created", "order_shipped"]}'

# === Step 7: Attach subscription DLQs to the HTTPS + Lambda subscriptions ===
# SQS has its own DLQ; Lambda should use on-failure destinations. Only the
# HTTPS subscription needs a subscription-level DLQ here.
HTTPS_SUB_ARN=$(aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --query 'Subscriptions[?Endpoint==`https://api.example.com/sns/order-webhook`].SubscriptionArn' \
  --output text)

aws sns set-subscription-attributes \
  --subscription-arn $HTTPS_SUB_ARN \
  --attribute-name RedrivePolicy \
  --attribute-value '{"deadLetterTargetArn":"arn:aws:sqs:us-east-1:111111111111:order-https-dlq"}'

# === Step 8: Configure mobile push (APNS) subscriber ===
# Pre-req: platform application already created in account 111111111111
aws sns create-platform-endpoint \
  --platform-application-arn arn:aws:sns:us-east-1:111111111111:app/APNS/MyAppAPNS \
  --token <device-token> \
  --custom-user-data '{"userId": "customer-67890"}'
# Returns: arn:aws:sns:us-east-1:111111111111:endpoint/APNS/MyAppAPNS/abcd1234
# Note: mobile push subscribers are NOT subscribed to a topic directly via
# `aws sns subscribe`. Instead, publish with --target-arn for direct push,
# OR use a topic + a separate application fanout. To route topic messages
# to mobile, publish with --message-structure json and include the APNS key.
# This example keeps mobile push as a direct endpoint alongside the topic.

# === Step 9: Enable delivery status logging (HTTP + Lambda + SQS failure) ===
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name HTTPSuccessFeedbackRoleArn \
  --attribute-value arn:aws:iam::111111111111:role/SNSDeliveryFeedback
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name HTTPFailureFeedbackRoleArn \
  --attribute-value arn:aws:iam::111111111111:role/SNSDeliveryFeedback
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name LambdaFailureFeedbackRoleArn \
  --attribute-value arn:aws:iam::111111111111:role/SNSDeliveryFeedback
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name SQSFailureFeedbackRoleArn \
  --attribute-value arn:aws:iam::111111111111:role/SNSDeliveryFeedback
# IMPORTANT: also add the CloudWatch Logs resource policy granting SNS
# logs:CreateLogStream + logs:PutLogEvents. Without it, SNS silently fails
# to write logs even with the feedback role configured.

# === Step 10: Test publish (exercises all protocols) ===
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --subject "Order Created" \
  --message '{"orderId": "ORD-12345", "customerId": "CUST-67890", "total": 99.95}' \
  --message-attributes '{"event_type": {"DataType": "String", "StringValue": "order_created"}, "region": {"DataType": "String", "StringValue": "us-east-1"}}'
# Returns: MessageId. This message should:
#  - hit the HTTPS webhook (filter matches order_created + us- prefix)
#  - land in the SQS queue (filter matches order_created + us- prefix)
#  - invoke the cross-account Lambda (filter matches order_created)
# Mobile push is direct-publish only in this topology.
```

### Verification

```bash
# Confirm all subscriptions are Confirmed (no PendingConfirmation)
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --query 'Subscriptions[].{Endpoint:Endpoint,Status:SubscriptionArn}'

# Verify delivery logs are populated after the test publish
aws logs filter-log-events \
  --log-group-name sns/us-east-1/111111111111/order-events/Failure \
  --log-stream-names $(aws logs describe-log-streams \
    --log-group-name sns/us-east-1/111111111111/order-events/Failure \
    --query 'logStreams[*].logStreamName' --output text)

# Verify the SQS queue received the message
aws sqs receive-message --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/order-queue \
  --max-number-of-messages 10

# Verify the cross-account Lambda was invoked (in account 222222222222)
aws logs filter-log-events \
  --log-group-name /aws/lambda/order-handler \
  --filter-pattern ORD-12345
```

### Per-protocol outcome summary

| Protocol | Subscription ARN | Filter | DLQ | Delivery logging |
|---|---|---|---|---|
| HTTPS webhook | `arn:aws:sns:...:order-events:abc-def` (Confirmed) | `event_type: order_created`, `region: us-*` | order-https-dlq | success + failure |
| SQS queue | `arn:aws:sns:...:order-events:ghi-jkl` (Confirmed) | `event_type: order_created`, `region: us-*` | (SQS own DLQ) | failure only |
| Lambda (cross-account) | `arn:aws:sns:...:order-events:mno-pqr` (Confirmed by 222222222222) | `event_type: [order_created, order_shipped]` | (Lambda on-failure dest) | failure only |
| Mobile push (APNS) | `arn:aws:sns:...:endpoint/APNS/MyAppAPNS/abcd1234` (direct endpoint) | N/A (direct publish) | N/A | failure only |

### Per-protocol retry and dead-letter behavior

| Protocol | Retry policy | Failure mode | Dead-letter target |
|---|---|---|---|
| HTTP/HTTPS | SNS retries for 4 hours (100,010 attempts) with exponential backoff (immediate, then seconds, then minutes) | Endpoint returns 4xx/5xx or times out (>15s) | **Subscription DLQ** (RedrivePolicy on the subscription) — captures the original message after SNS's retry budget is exhausted |
| Lambda (async) | Lambda retries **2 times** on top of SNS delivery — SNS succeeds on Lambda ack, Lambda retries the function | Function throws an exception or times out | **Lambda on-failure destination** (SQS/SNS/EventBridge configured on the function, not the SNS subscription) — the SNS subscription DLQ is NOT invoked for Lambda failures |
| SQS | SNS delivers once; SQS visibility-timeout and redrive policy handle downstream retries | Queue full, KMS decrypt failure, or queue policy missing `sqs:SendMessage` for SNS | **SQS DLQ** (configured on the queue via RedrivePolicy, not the SNS subscription) — use the SQS DLQ, not an SNS subscription DLQ, for SQS subscribers |
| Email/Email-JSON | One delivery attempt, no retry | Bounce, complaint, or pending confirmation | None — email is fire-and-forget |
| Mobile push (application) | SNS retries per platform policy (APNS: immediate retry; FCM: exponential backoff) | Token expired, endpoint disabled, platform credential invalid | **Subscription DLQ** if the endpoint is subscribed via topic; otherwise message is dropped after retries |

### Edge-case callouts for this topology

- **Cross-account Lambda KMS decrypt:** the Lambda function in account
  222222222222 must have a role policy granting `kms:Decrypt` on the topic
  CMK (`alias/my-sns-key` in account 111111111111). Without it, the
  invocation succeeds but the function receives an opaque ciphertext body.
- **Filter policy on HTTPS subscription:** if the webhook cannot tolerate
  `order_shipped` events (only `order_created`), scope the filter at the
  subscription, not the topic. Topic-level filters do not exist.
- **Mobile push is direct-publish, not topic-subscribed:** in this example
  the mobile endpoint receives messages via `publish --target-arn`, not via
  the topic. To fan out topic messages to mobile, use a separate Lambda
  subscriber that calls `publish --target-arn <mobile-endpoint>` for each
  relevant message.
- **PendingConfirmation on the HTTPS subscription:** if the webhook does
  not handle `SubscriptionConfirmation` programmatically, the subscription
  stays PendingConfirmation for 3 days and then expires. Re-subscribing
  generates a new token. There is no programmatic way to force-confirm an
  HTTPS subscription without the token from SNS.

## Error-handling branches

| Error | Cause | Fix |
|---|---|---|
| `InvalidParameter: FIFO topic name must end with .fifo` | FIFO topic created without `.fifo` suffix | Rename with `.fifo` suffix |
| `InvalidParameter: Subscription to FIFO topic requires FIFO SQS queue` | Non-SQS endpoint subscribed to FIFO topic | Use SQS FIFO queue subscriber, or switch to Standard topic |
| `KMSAccessDeniedException` | Subscriber lacks `kms:Decrypt` on topic's CMK | Add `kms:Decrypt` + `kms:GenerateDataKey*` to subscriber's key policy |
| `AuthorizationError: User is not authorized to perform: sns:Subscribe` | Topic policy does not allow cross-account subscribe | Add the foreign account to the topic policy |
| Messages not delivered to cross-account SQS | AWS-managed key blocks cross-account decrypt | Switch to customer-managed CMK with subscriber decrypt grant |
| HTTP subscription in `PendingConfirmation` | Endpoint did not confirm within 3 days | Re-subscribe; the endpoint must GET the SubscribeURL |
| Filter policy silently dropping messages | Non-JSON body with `FilterPolicyScope=MessageBody` | Ensure publishers send valid JSON, or switch to MessageAttributes |
| Delivery logs not appearing in CloudWatch | Missing CloudWatch Logs resource policy | Add resource policy granting SNS `logs:CreateLogStream` + `logs:PutLogEvents` |
| FIFO duplicate delivery | `ContentBasedDeduplication=false` and publisher omits DeduplicationId | Enable ContentBasedDeduplication, or ensure publishers send MessageDeduplicationId |

### Per-protocol subscription error-handling

Each SNS subscription protocol has distinct failure semantics. The table
below covers the dominant failure mode, the recommended retry/backoff
strategy, and the dead-letter target for each protocol. **Read this
together with the Subscription troubleshooting decision tree** — the tree
diagnoses where messages are dropping; this table configures what happens
when they do.

#### HTTP / HTTPS

- **Retry budget:** SNS retries for up to 4 hours (100,010 attempts) with
  exponential backoff (immediate → 1s → 5s → 10s → ... → minutes).
- **Failure detection:** endpoint returns 4xx/5xx, times out at >15s, or
  refuses the connection.
- **Required mitigation:** attach a **subscription-level DLQ** via
  `RedrivePolicy` on the subscription. After SNS exhausts its retry budget,
  the original message lands in the DLQ — without one, the message is
  silently dropped.
- **Recommended backoff on the endpoint side:** return HTTP 429 (Too Many
  Requests) under load — SNS interprets 429 as "back off" and slows
  delivery. Returning 500 triggers the same retry but signals a permanent
  failure pattern. Avoid returning 200 to a message you cannot process —
  SNS will not retry it; instead fail fast and let the DLQ catch it.
- **Signature validation:** if the endpoint validates the SNS signature,
  ensure it accepts both `SignatureVersion=1` and `SignatureVersion=2`.
  Mismatch is the most common cause of spurious 403 responses.

```bash
aws sns set-subscription-attributes \
  --subscription-arn <https-sub-arn> \
  --attribute-name RedrivePolicy \
  --attribute-value '{"deadLetterTargetArn":"arn:aws:sqs:us-east-1:111111111111:order-https-dlq"}'
```

#### Lambda

- **Retry budget:** Lambda async invocation retries **2 times** on top of
  SNS delivery. SNS considers delivery successful once Lambda acks the
  async invocation; function-level failures are retried by Lambda, not SNS.
- **Failure detection:** function throws an exception, times out (>15 min
  default), or returns an error response.
- **Required mitigation:** configure **Lambda on-failure destination**
  (SQS/SNS/EventBridge), NOT the SNS subscription DLQ. The subscription
  DLQ only catches SNS-to-Lambda delivery failures (rare — usually KMS or
  resource-policy issues). Function failures are handled by Lambda's own
  async-failure config.
- **Duplicate invocations:** SNS-to-Lambda does NOT deduplicate. Lambda
  async retries can deliver the same message 3 times (1 + 2 retries). For
  exactly-once semantics, use an SQS subscription with a Lambda
  event-source mapping — SQS provides visibility-timeout-based dedup.

```bash
# Configure Lambda on-failure destination (run in the Lambda account)
aws lambda put-function-event-invoke-config \
  --function-name order-handler \
  --maximumretry-attempts 2 \
  --destination-config '{"OnFailure":{"Destination":"arn:aws:sqs:us-east-1:222222222222:lambda-failure-dlq"}}'
```

#### SQS

- **Retry budget:** SNS delivers once; SQS visibility-timeout and redrive
  policy handle downstream retries. The SNS retry budget does NOT apply.
- **Failure detection:** queue remains empty after a successful publish
  with delivery-success logged — usually a KMS decrypt failure or queue
  policy issue.
- **Required mitigation:** configure the **SQS DLQ** via the queue's
  RedrivePolicy (`deadLetterTargetArn` + `maxReceiveCount`), NOT the SNS
  subscription DLQ. The SNS subscription DLQ catches SNS-side delivery
  failures; the SQS DLQ catches consumer-side processing failures. They
  operate at different layers and are both needed for full coverage.
- **Message retention:** SQS retains messages for 4 days by default
  (configurable up to 14 days). Set `MessageRetentionPeriod` to match the
  recovery SLA — a 1-day retention on a queue that drains hourly loses
  messages during an outage.

```bash
aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/order-queue \
  --attributes '{"RedrivePolicy":"{\"deadLetterTargetArn\":\"arn:aws:sqs:us-east-1:111111111111:order-sqs-dlq\",\"maxReceiveCount\":\"5\"}", "MessageRetentionPeriod":"1209600"}'
```

#### Mobile push (application)

- **Retry budget:** SNS retries per platform policy. APNS retries
  immediately; FCM uses exponential backoff. Failed endpoints are
  auto-disabled by SNS after the platform rejects the token.
- **Failure detection:** endpoint shows `Enabled=false` in
  `get-endpoint-attributes`. Delivery-failure logs show the platform
  response (e.g., `BadDeviceToken`, `Unregistered`).
- **Required mitigation:** subscribe mobile push endpoints via a topic
  (not just direct `publish --target-arn`) and attach a subscription DLQ.
  The DLQ captures delivery failures so you can re-register the device and
  replay. Direct-push failures are silent — there is no DLQ for direct
  `publish --target-arn`.
- **Token lifecycle:** device tokens rotate. Set up a periodic job to
  re-call `create-platform-endpoint` with fresh tokens from the app. An
  endpoint with a stale token is permanently disabled by SNS after a few
  delivery failures.

#### Email / Email-JSON

- **Retry budget:** none. SNS sends once; if the receiving SMTP server
  rejects, the message is lost.
- **Failure detection:** check SES bounce/complaint metrics if SNS email
  is routed through SES; otherwise there is no SNS-side failure telemetry.
- **Required mitigation:** none at the SNS layer. For reliable
  notifications, prefer SQS or HTTPS subscriptions and trigger email via a
  downstream consumer. Treat SNS email as a best-effort human-notification
  channel only.
- **Confirmation required:** every email subscription requires the
  recipient to click the SubscribeURL in the confirmation email within 3
  days. There is no programmatic bypass for email subscriptions without
  the token.

## References

- `references/topic-configuration-guide.md` — deep reference on topic type
  internals, delivery retry semantics, subscription confirmation flow,
  filter policy operators, cross-account KMS key policy requirements,
  and mobile push platform-specific message formats.

- `references/deployment-cli-commands.md` — full copy-pasteable CLI command
  sequence for all 10 deployment steps, including topic creation,
  subscriptions (all protocols), filter policies, access policies,
  SSE-KMS, delivery logging, subscription DLQs, mobile push setup, and
  Terraform `aws_sns_topic` resource equivalents.

## Section taxonomy (CloudOps deployer pattern)

1. **Frontmatter** — name, description, version, when-to-use.
2. **Quick navigation** — table of contents for the skill body.
3. **Activation keywords** — discoverability terms.
4. **Invocation contract** — the mandatory output format.
5. **Reasoning framework** — the *why* behind the deployment order.
6. **Prerequisites** — what must be verified before deployment.
7. **Deployment procedure** — the ordered 10-step deployment sequence.
8. **Latest SNS features** — 2024-2026 feature changes.
9. **Workload-specific deployment matrix** — per-workload configuration.
10. **NEVER** — anti-patterns with explicit *why* each is wrong.
11. **Pre-flight safety checks** — non-destructive deployment guards.
12. **Output format** — the fixed checklist report shape.
13. **Error-handling branches** — common deployment errors and fixes.
14. **References** — pointer to deeper references.

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
