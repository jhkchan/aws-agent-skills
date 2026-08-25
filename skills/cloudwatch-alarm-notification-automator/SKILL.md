---
name: cloudwatch-alarm-notification-automator
description: 'Designs CloudWatch alarm notification and escalation automation across six surfaces: SNS-to-Lambda forwarders for Slack / Teams / PagerDuty / Opsgenie; EventBridge rules on CloudWatch Alarm State Change; alarm-to-Jira / ServiceNow ticket auto-create with idempotency; composite alarm correlation to deduplicate noisy children into one escalation; tiered escalation (primary -> secondary -> manager) via SNS + Step Functions; and 2024-2026 surfaces — AWS User Notifications chat delivery (Slack / Chime / Teams without Lambda), SNS SMS / phone, and Amazon Q for natural-language triage. Enforces safety: subscription-confirmation, kill-switch, dry-run test publish, IAM least-privilege, secrets in Parameter Store / Secrets Manager, ticket idempotency. Emits AUTOMATED with the workflow OR MANUAL_STEP_REQUIRED with the gap. Use when wiring alarm-to-Slack, alarm-to-ticket, escalation tiers, composite-correlation fatigue reduction, or adopting User Notifications / Amazon Q.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan authoring. Live deployment uses aws sns create-topic / subscribe / publish, aws lambda create-function / update-function-code, aws events put-rule / put-targets, aws sqs create-queue, aws stepfunctions create-state-machine, aws ssm put-parameter, aws secretsmanager create-secret, aws cloudwatch put-metric-alarm / put-composite-alarm, aws notifications /...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATED | MANUAL_STEP_REQUIRED
  when_to_use: Designing CloudWatch alarm notification or escalation automation — wiring alarms to Slack/Teams/PagerDuty via SNS+Lambda, building EventBridge-driven alarm-to-ticket (Jira/ServiceNow) workflows, creating composite alarm correlation to deduplicate child alarms, designing tiered escalation policies, adopting AWS User Notifications for native chat-based delivery, configuring SNS SMS/phone for page-the-human alerts, or using Amazon Q for natural-language alarm triage. Do NOT invoke for creating/tuning the underlying alarm threshold itself (use cloudwatch-alarm-operator) or for security-incident containment automation (use incident-response-automator).
  activation_triggers: alarm to Slack, alarm to Teams, alarm to PagerDuty, alarm notification Lambda, alarm SNS fan-out, CloudWatch alarm EventBridge, alarm state change, alarm to Jira ticket, alarm to ServiceNow, composite alarm correlation, alarm escalation policy, tiered escalation, AWS User Notifications, SNS phone number, SNS SMS alarm, Amazon Q alarm analysis, reduce alarm fatigue
  invocation_schema: 'Input: either (a) a notification design intent with target channel(s) and source alarms, OR (b) an existing workflow (EventBridge rule + SNS topic ARN + Lambda forwarder ARN) for validation against the safety baseline. Output: deterministic NOTIFICATION_SOURCE / SCOPE / VERDICT / WORKFLOW / SAFETY / FINDINGS / REMEDIATION block where VERDICT is one of AUTOMATED | MANUAL_STEP_REQUIRED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CloudWatch alarm, alarm notification, SNS, Lambda forwarder, Slack, Microsoft Teams, PagerDuty, Opsgenie, EventBridge, alarm state change, Jira, ServiceNow, ticket automation, composite alarm, alarm correlation, escalation policy, tiered escalation, Step Functions, AWS User Notifications, SNS SMS, Amazon Q, alarm triage, alarm fatigue, kill-switch
  tags: cloudwatch, monitoring, alarms, notifications, automation, sns, eventbridge, slack, pagerduty, escalate
---

# CloudWatch Alarm Notification Automator

## What this skill does

Designs the notification and escalation layer that sits on top of
CloudWatch alarms — the wiring that turns an alarm state transition into
the right human action on the right channel at the right time. Covers six
surfaces: SNS-to-Lambda forwarders (Slack/Teams/PagerDuty/Opsgenie),
EventBridge rules on the `CloudWatch Alarm State Change` event,
alarm-to-ticket automation (Jira/ServiceNow), composite alarm correlation
for fatigue reduction, tiered escalation via Step Functions, and the
2024-2026 native surfaces (AWS User Notifications chat delivery, SNS
SMS/phone, Amazon Q operational analysis).

The verdict is binary: **AUTOMATED** when the workflow is complete, every
subscription is confirmed, the Lambda forwarder has a kill-switch, IAM is
least-privilege, secrets are stored, and the workflow has been dry-run on
a test alarm; **MANUAL_STEP_REQUIRED** when any safety or coverage gate
fails, with the specific gap enumerated in FINDINGS.

## Quick navigation

| # | Section | Jump when |
|---|---|---|
| 1 | [Pre-flight gate](#pre-flight-notification-spec-gate) | Starting any workflow — blocks unsafe specs |
| 2 | [Decision tree](#decision-tree--notification-surface-selection) | Picking Lambda forwarder vs User Notifications vs Q |
| 3 | [SNS fan-out + Lambda](#sns-fan-out--lambda-forwarders) | Slack / Teams / PagerDuty / Opsgenie wiring |
| 4 | [EventBridge on alarm state change](#eventbridge-on-alarm-state-change) | The trigger pattern that drives everything |
| 5 | [Alarm-to-ticket automation](#alarm-to-ticket-automation-jira--servicenow) | Auto-create Jira / ServiceNow tickets |
| 6 | [Composite correlation](#composite-alarm-correlation--fatigue-reduction) | Roll up noisy children into one escalation |
| 7 | [Tiered escalation](#tiered-escalation-via-step-functions) | Primary -> secondary -> manager |
| 8 | [2024-2026 native surfaces](#2024-2026-native-surfaces) | User Notifications, SNS phone, Amazon Q |
| 9 | [Safety + kill-switch](#safety--kill-switch-mandatory) | The non-negotiable safety baseline |
| 10 | [STRICT output contract](#strict-output-contract) | The exact VERDICT block the skill emits |
| 11 | [NEVER anti-patterns](#never-these-things) | The hardcoded taboos |
| 12 | [Recent AWS features](#recent-aws-features-2024-2026) | What changed in 24 months |

## Mindset

**One-line takeaway:** alarm notification is a human-attention routing
problem, not a message-delivery problem. Delivering the message is easy;
getting the right human to act on it at 03:00 without burning them out is
the hard part. Three realities shape every notification workflow:

- **An alarm firing is a hypothesis, not a fact.** CloudWatch evaluates
  metric math over a window and emits a state-change event. The metric
  may be noisy, the threshold may be wrong, or the system may have
  self-recovered by the time the page reaches on-call. The notification
  layer's job is to add context (runbook link, related alarms, recent
  deploy) so the human can triage in seconds.

- **Subscription confirmation is the silent failure mode.** SNS
  email/HTTPS subscriptions require explicit confirmation; an unconfirmed
  subscription silently drops every message. Lambda subscriptions
  auto-confirm but STILL need `lambda:add-permission` for SNS to invoke
  them. This is the #1 root cause of "the alarm was firing but nobody
  was paged" post-incidents.

- **Alarm fatigue is the long-term failure mode.** A single EC2 instance
  flapping between OK and ALARM every 60 seconds generates 60 pages per
  hour. Within an hour, on-call stops reading the pages. Within a day,
  on-call mutes the channel. Composite correlation and tiered escalation
  are not optional polish — they are the difference between a
  notification system that works and one that gets ignored.

## Pre-flight: notification spec gate (run before generation)

Validate the input before producing any workflow. Several requirements
block generation — proceeding with an invalid spec produces a workflow
that silently drops messages or pages the wrong human.

| Attribute | Required | Effect on plan |
|---|---|---|
| `source_alarms` | YES | The alarm name(s) or composite rule to wire |
| `target_channels` | YES | Slack / Teams / PagerDuty / Opsgenie / SMS / email / Jira / ServiceNow |
| `region` | YES | SNS topics, Lambda, EventBridge rules are regional |
| `account_id` | YES | For ARN construction and cross-account checks |
| `escalation_tiers` | Recommended | 1 (single page) / 2 (primary + secondary) / 3 (+ manager) |
| `kill_switch_type` | RECOMMENDED | parameter-store / eventbridge-disable / lambda-guard |
| `existing_workflow` | For validation mode | Rule name + SNS topic ARN + Lambda ARN to validate |

**If the spec is incomplete** (missing source_alarms or target_channels),
output:

```text
NOTIFICATION_SOURCE: <unknown>
SCOPE: <unknown>
VERDICT: MANUAL_STEP_REQUIRED
REASON: Spec is missing required fields (<list>).
REQUIRED:
  - source_alarms (alarm name(s) or composite rule)
  - target_channels (slack | teams | pagerduty | opsgenie | sms | email | jira | servicenow)
  - region, account_id
REMEDIATION: Provide all four. Example: "wire prod-checkout-critical
composite to Slack #ops-alerts and PagerDuty PXYZ" maps to
source_alarms=prod-checkout-critical-rollup,
target_channels=[slack,pagerduty].
```

**Live-account pre-flight checks (skip for offline authoring):**
1. `aws sns list-topics` — confirm topics exist or will be created.
2. `aws lambda list-functions` — confirm forwarder exists or will be created.
3. `aws events list-rules --name-prefix alarm-` — check for existing rules.
4. `aws ssm get-parameter --name /notifications/kill-switch` — verify
   kill-switch parameter exists (create if not).
5. For AWS User Notifications: `aws notifications list-notification-hubs`
   — confirm the hub exists in the region.

## Decision tree — notification surface selection

Apply top-to-bottom. First matching rule wins.

```
START
  ├─ target = Slack / Chime / Teams AND org uses AWS Chatbot? ─► AWS User Notifications
  │                                                              (native chat, no Lambda)
  ├─ target = Slack / Teams / PagerDuty (custom format)? ─────► SNS -> Lambda forwarder
  ├─ target = SMS / phone (page-the-human)? ─────────────────► SNS SMS / phone subscription
  ├─ target = Jira / ServiceNow ticket? ──────────────────────► EventBridge -> Lambda (ticket API)
  ├─ need natural-language "why did this fire" triage? ───────► Amazon Q operational analysis
  ├─ need tiered escalation (primary -> secondary -> manager)? ─► Step Functions (SNS + Wait + Choice)
  └─ need to deduplicate N noisy child alarms? ───────────────► Composite alarm correlation
```

**Why two paths for Slack/Teams:** AWS User Notifications (2024-2025)
delivers natively via AWS Chatbot without Lambda glue. SNS-to-Lambda
gives full control over message formatting (rich blocks, interactive
buttons, thread replies) but adds a component to maintain. Choose User
Notifications for speed-of-setup; choose Lambda forwarder for custom
formatting or interactive workflows.

## SNS fan-out + Lambda forwarders

The canonical pattern for alarm-to-Slack/Teams/PagerDuty. SNS provides
fan-out (one alarm publishes to one topic; the topic fans out to N
subscribers). Lambda subscribes to the topic, formats the message, and
POSTs to the target webhook.

```bash
aws sns create-topic --name alarm-notifications-prod
```

Always use a dedicated topic per alarm severity or per service — do NOT
reuse a topic that carries application events. Mixing alarm and
application traffic causes subscription confusion and makes access-policy
scoping impossible.

### Lambda forwarder (Slack incoming webhook)

Handler code moved verbatim to [references/notification-patterns-and-deployment.md](references/notification-patterns-and-deployment.md) — "Lambda forwarder handler": full Python handler (kill-switch check, SSM-fetched webhook, Slack blocks) + secret-storage rule (Parameter Store for webhooks, Secrets Manager for OAuth; never env vars).
Load before writing or reviewing a forwarder.

### PagerDuty via Events API v2

Handler code moved verbatim to [references/notification-patterns-and-deployment.md](references/notification-patterns-and-deployment.md) — "PagerDuty Events API v2": trigger/resolve logic and the mandatory `dedup_key = AlarmName:Region` rule.
Load before wiring PagerDuty; a missing stable dedup key is the #1 integration bug.

### Subscription + confirmation (MANDATORY verification)

Exact CLI sequence moved verbatim to [references/notification-patterns-and-deployment.md](references/notification-patterns-and-deployment.md) — subscribe, the commonly-missed `lambda add-permission`, and the `list-subscriptions-by-topic` verification.
Lambda subscriptions auto-confirm but STILL need add-permission; HTTPS/email/SMS need endpoint confirmation.

### Test publish (run after every subscription change)

Test-publish command and 30-second delivery rule moved verbatim to [references/notification-patterns-and-deployment.md](references/notification-patterns-and-deployment.md).
If the test does not arrive, the subscription is unconfirmed OR the Lambda errored — check CloudWatch Logs.

## EventBridge on alarm state change

Every CloudWatch alarm state transition emits an event to the default
EventBridge bus. The pattern below matches any ALARM transition.

```bash
aws events put-rule \
  --name alarm-state-change-to-sns \
  --event-pattern '{
    "source": ["aws.cloudwatch"],
    "detail-type": ["CloudWatch Alarm State Change"],
    "detail": {"stateName": ["ALARM"]}
  }' \
  --state ENABLED

aws events put-targets \
  --rule alarm-state-change-to-sns \
  --targets '[{"Id":"sns-target","Arn":"arn:aws:sns:us-east-1:111111111111:alarm-notifications-prod"}]'
```

**Why use EventBridge in addition to alarm actions:** alarm actions
(`--alarm-actions`) call SNS directly but ONLY on the ALARM transition.
EventBridge sees ALL state changes (OK -> ALARM, ALARM -> OK,
ALARM -> INSUFFICIENT_DATA), enabling richer workflows: auto-resolve
tickets when alarm clears, alert on INSUFFICIENT_DATA (sensor failure),
fan to multiple targets with different filters (`alarmName.prefix`).

| Need | Alarm actions | EventBridge |
|---|---|---|
| Notify SNS on ALARM only | Yes (simpler) | Also works |
| Notify on OK (auto-resolve ticket) | OK actions | Yes (only way for ticket) |
| Notify on INSUFFICIENT_DATA | InsufficientData actions | Yes (only way for ticket) |
| Filter by alarm-name prefix | No | Yes (`alarmName.prefix`) |
| Fan to multiple targets with different filters | No (max 5 ARNs) | Yes (unlimited targets) |

## Alarm-to-ticket automation (Jira / ServiceNow)

Auto-create a ticket when an alarm fires, auto-resolve when it clears.
Pattern: EventBridge rule -> Lambda -> Jira/ServiceNow REST API.

Handler code moved verbatim to [references/notification-patterns-and-deployment.md](references/notification-patterns-and-deployment.md) — full Jira Lambda with the MANDATORY DynamoDB idempotency check, plus the ServiceNow equivalent.
Without dedup, alarm flapping creates dozens of tickets per hour.

## Composite alarm correlation + fatigue reduction

When N child alarms fire on the same underlying incident, do NOT page
on-call N times. Build a composite rollup that fires once.

```bash
aws cloudwatch put-composite-alarm \
  --alarm-name prod-checkout-critical-rollup \
  --alarm-description "Correlated: any of {5xx, latency, lambda errors}" \
  --actions-enabled \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-escalation \
  --alarm-rule "ALARM(alb-error-ratio-prod) OR ALARM(alb-latency-anomaly-prod) OR ALARM(lambda-errors-high-prod-checkout)" \
  --treat-missing-data notBreaching
```

**Wire the notification to the COMPOSITE, not the children.** Child
alarms should have empty (or InsufficientData-only) actions; only the
composite pages on-call. This is the #1 alarm-fatigue fix.

**AND vs OR for correlation:**
- `OR` — escalation: any child triggers the composite. Use for "any
  signal that this service is degraded."
- `AND` — high-confidence correlation: requires multiple symptoms.
  Fragile — children with different detection latencies may not overlap.

**Deduplication heuristic:** if the same on-call would receive pages from
N alarms within a 5-minute window for the same service, build a composite.

## Tiered escalation via Step Functions

For 2-tier or 3-tier escalation (primary -> secondary -> manager), use a
Step Functions state machine with `Wait` + `Choice` + SNS targets.

State-machine JSON, ack URL mechanism, and tier timing baselines moved verbatim to [references/notification-patterns-and-deployment.md](references/notification-patterns-and-deployment.md).
Standard: 5 min between tiers; SEV-1: 2 min then simultaneous secondary + manager.

## 2024-2026 native surfaces

Implementation detail moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — User Notifications setup CLI + comparison matrix, SNS SMS/phone caveats (confirmation, best-effort delivery, cost), Amazon Q operational analysis setup and what Q adds.
The decision tree above already encodes WHEN to pick each surface; load the reference for the HOW.

## Safety & kill-switch (MANDATORY)

Every alarm-notification workflow MUST include:

1. **A kill-switch checked BEFORE any action.** Parameter Store:
   Lambda reads `/notifications/kill-switch` first; if "disabled",
   returns without sending. EventBridge rule disable is a global
   kill-switch: `aws events disable-rule --name alarm-state-change-to-sns`.

2. **Subscription confirmation verified.** Every SNS subscription must
   have a `SubscriptionArn` (not `PendingConfirmation`). Verify after
   every change with `list-subscriptions-by-topic`.

3. **Test publish after every change.** Publish a test message and
   confirm delivery to the target channel within 30 seconds.

4. **IAM least-privilege on the Lambda forwarder.** The Lambda needs
   only: `ssm:GetParameter` on the webhook/token parameter,
   `sns:Publish` (if fanning out further). It does NOT need `sqs:*`,
   broad `dynamodb:*` (only the dedup table), or `*` permissions.

5. **Secrets in Parameter Store or Secrets Manager.** Webhook URLs,
   API tokens, and credentials MUST be stored encrypted — never
   hardcoded in Lambda environment variables in plain text.

6. **Idempotency for ticket creation.** The ticket-creation Lambda must
   check for an existing open ticket before creating a new one. Alarm
   flapping without dedup creates dozens of tickets per hour.

```bash
aws ssm put-parameter --name /notifications/kill-switch --value "enabled" --type String
# Disable ALL alarm notifications in one command:
aws ssm put-parameter --name /notifications/kill-switch --value "disabled" --type String --overwrite
```

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
NOTIFICATION_SOURCE: <alarm-name(s) or composite rule>
SCOPE: <channels and tiers>
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
WORKFLOW:
  EventBridge rule: <name>
  SNS topic: <arn>
  Lambda forwarder(s): <arns>
  Subscription status: <confirmed | pending>
  Escalation state machine: <arn or N/A>
  Ticket integration: <Jira project / ServiceNow table or N/A>
  AWS User Notifications hub: <arn or N/A>
SAFETY:
  - [PASS] Kill-switch implemented (Parameter Store: /notifications/kill-switch)
  - [PASS] All subscriptions confirmed (verified via list-subscriptions-by-topic)
  - [PASS] Test publish delivered to all targets within 30s
  - [PASS] Lambda IAM least-privilege
  - [PASS] Secrets stored in Parameter Store / Secrets Manager
  - [PASS] Idempotency check for ticket creation
FINDINGS:
  - [INFO] <observation>
  - [WARN] <observation>
REMEDIATION:
  1. <step 1 if MANUAL_STEP_REQUIRED>
```

### FORBIDDEN output patterns

- NEVER start with conversational preamble ("Let me design…") — the
  VERDICT block is the FIRST line, always. Use uppercase verdict values
  only (`AUTOMATED`, `MANUAL_STEP_REQUIRED`).
- NEVER omit SAFETY — every gate must appear with `[PASS]` or `[FAIL]`
  and a specific reason for each failure.
- NEVER emit a workflow with placeholder ARNs in an AUTOMATED verdict —
  every ARN must be populated with actual values from the input data.
- NEVER claim AUTOMATED without every SAFETY line showing `[PASS]`.
- NEVER recommend a notification path without confirming subscription
  status and running a test publish.

## NEVER (these things)

- NEVER rely on an unconfirmed SNS subscription. Email/HTTPS/SMS
  subscriptions require explicit confirmation. Lambda subscriptions
  auto-confirm but STILL need `lambda:add-permission` for SNS to invoke.
  Verify every subscription with `list-subscriptions-by-topic` and a
  test publish.

- NEVER hardcode webhook URLs or API tokens in Lambda environment
  variables. Environment variables are visible in CloudTrail
  `GetFunctionConfiguration` and the console. Store in Parameter Store
  (free) or Secrets Manager (paid, rotation).

- NEVER wire notifications to child alarms when a composite rollup
  exists. The composite is the escalation signal; child alarms should
  have empty or InsufficientData-only actions. Wiring both = N+1 pages
  per incident (alarm fatigue).

- NEVER deploy a notification workflow without a kill-switch. A
  flapping alarm without a kill-switch generates pages every 60 seconds,
  burns out on-call, and triggers PagerDuty/SMS cost alerts.

- NEVER create tickets without idempotency. Alarm flapping
  (OK -> ALARM -> OK -> ALARM) without a dedup check creates dozens of
  Jira/ServiceNow tickets per hour. Use DynamoDB keyed by `alarmName`;
  auto-resolve when the alarm clears.

## Expert heuristic: "alarm fired but nobody was paged" diagnostic

The #1 post-incident finding for notification workflows. Apply in order:

```
Alarm fired (describe-alarm-history confirms ALARM transition)
   |
   ├─ Did the alarm action fire? (describe-alarms: AlarmActions populated + ActionsEnabled: true)
   |    └─ NO -> ActionsEnabled false OR AlarmActions empty. Fix the alarm config.
   |
   ├─ Did SNS publish? (CloudTrail: sns:Publish by cloudwatch.amazonaws.com within 60s)
   |    └─ NO -> IAM permission missing on CloudWatch service-linked role.
   |
   ├─ Did SNS deliver? (CloudWatch SNS metrics: NumberOfMessagesPublished > 0, NumberOfNotificationsDelivered > 0)
   |    └─ NO, NumberOfNotificationsFailed > 0 -> subscription broken (Lambda errored, HTTPS 4xx, email bounced)
   |
   ├─ Did the Lambda forwarder succeed? (CloudWatch Logs: errors within 60s of publish?)
   |    └─ ERROR -> SSM access denied, webhook URL wrong, target API rate-limited, timeout
   |
   └─ Did the target receive it? (Slack message visible? PagerDuty incident created? Ticket in Jira?)
        └─ NO but Lambda succeeded -> webhook points to wrong channel, routing key wrong, project key wrong
```

**Most common root cause:** unconfirmed subscription or missing
`lambda:add-permission`. Always verify with a test publish BEFORE
relying on the workflow.

## Pre-flight safety checks (run before any deploy)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`cloudformation deploy`, `lambda update-function-code`,
  `events put-rule`, `sns subscribe`), the automator MUST emit
  `CONFIRM:` and wait for explicit `yes`.
- **Dry-run on a test alarm.** Before enabling the EventBridge rule,
  publish a synthetic alarm event via `aws events put-events` and verify
  the full chain (EventBridge -> SNS -> Lambda -> Slack/PagerDuty) works.
- **Verify subscription ARNs.** After every subscription change, run
  `aws sns list-subscriptions-by-topic` and confirm every
  `SubscriptionArn` is populated.
- **Validate the kill-switch.** Set `/notifications/kill-switch` to
  `disabled`, publish a test message, verify the Lambda returns without
  sending. Then re-enable.
- **Check for Chatbot double-subscription.** If both the Lambda
  forwarder and AWS Chatbot subscribe to the same SNS topic, every alarm
  produces two Slack messages. Verify Chatbot subscribes to a separate
  `aws-chatbot` topic.

## Edge-case handling

Edge-case catalog moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — flapping, cross-region topics, Lambda timeout, PagerDuty/Slack rate limits, Chatbot double-notify.
Load when a deployed workflow misbehaves under load or across regions.

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — User Notifications, Amazon Q triage, SNS SMS sandbox lift, cross-account composite alarms, EventBridge global endpoints.
Load when adopting 2024-2026 surfaces.

## References (load on demand)

- [references/notification-patterns-and-deployment.md](references/notification-patterns-and-deployment.md) — deployment reference + moved inline code: Slack/PagerDuty forwarder handlers, subscription + confirmation commands, test publish, alarm-to-ticket Lambda (Jira/ServiceNow, idempotency), tiered-escalation Step Functions JSON with ack + timing.
- [references/advanced-patterns.md](references/advanced-patterns.md) — 2024-2026 native surfaces detail (User Notifications setup, SNS SMS/phone caveats, Amazon Q triage), the edge-case catalog (flapping, cross-region, rate limits, double-notify), and recent AWS features (2024-2026).

## Domain

AWS CloudOps / CloudWatch Alarm Notification, Escalation, and Triage
Automation.

## AWS documentation

- **Amazon CloudWatch User Guide** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html
- **CloudWatch Alarms** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html
- **Using Composite Alarms** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Create_Composite_Alarm.html
- **Amazon SNS Developer Guide** — https://docs.aws.amazon.com/sns/latest/dg/welcome.html
- **AWS Lambda Developer Guide** — https://docs.aws.amazon.com/lambda/latest/dg/welcome.html
- **Amazon EventBridge User Guide** — https://docs.aws.amazon.com/eventbridge/latest/userguide/
- **AWS Chatbot Administrator Guide** — https://docs.aws.amazon.com/chatbot/latest/adminguide/
- **AWS User Notifications** — https://docs.aws.amazon.com/notifications/
- **Amazon Q Developer** — https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/
