---
description: Automate CloudWatch alarm notification and escalation — Slack, Teams, PagerDuty, Jira/ServiceNow tickets, composite correlation, tiered escalation, AWS User Notifications, Amazon Q triage.
nl_triggers:
  - "alarm to Slack"
  - "alarm to Teams"
  - "alarm to PagerDuty"
  - "alarm notification Lambda"
  - "alarm SNS fan-out"
  - "CloudWatch alarm EventBridge"
  - "alarm state change"
  - "alarm to Jira ticket"
  - "alarm to ServiceNow"
  - "composite alarm correlation"
  - "alarm escalation policy"
  - "tiered escalation"
  - "AWS User Notifications"
  - "SNS phone number"
  - "SNS SMS alarm"
  - "Amazon Q alarm analysis"
  - "reduce alarm fatigue"
  - "alarm notification broken"
  - "alarm fired but nobody paged"
routes_to: cloudwatch-alarm-notification-automator
---

# /aws:automate-cloudwatch-alarm-notification

Activate the `cloudwatch-alarm-notification-automator` skill and design
(or validate) a CloudWatch alarm notification / escalation workflow
with the safety baseline gate and a deterministic VERDICT.

## What it does

Reads a notification design intent (target channels, source alarms,
escalation tiers) and applies the priority-ordered safety baseline:

1. Pre-flight notification spec gate — short-circuit cases where
   source_alarms or target_channels are missing.
2. Decision tree — pick the right surface (Lambda forwarder vs AWS User
   Notifications vs Amazon Q vs Step Functions escalation vs composite
   correlation).
3. Safety baseline — subscription-confirmation check, kill-switch,
   IAM least-privilege on the forwarder, secrets in Parameter Store /
   Secrets Manager, idempotency for ticket creation, dry-run test
   publish.
4. AUTOMATED verdict when all gates pass — emit the full WORKFLOW block
   (EventBridge rule, SNS topic, Lambda ARNs, subscription status,
   escalation state machine, ticket integration, User Notifications hub).
5. MANUAL_STEP_REQUIRED verdict when any gate fails — enumerate the
   specific gap (unconfirmed subscription, missing
   `lambda:add-permission`, hardcoded webhook, no kill-switch, no ticket
   idempotency) with the exact remediation command.

Emits a deterministic VERDICT per workflow:

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
  - [PASS] Kill-switch implemented
  - [PASS] All subscriptions confirmed
  - [PASS] Test publish delivered within 30s
  - [PASS] Lambda IAM least-privilege
  - [PASS] Secrets in Parameter Store / Secrets Manager
  - [PASS] Idempotency check for ticket creation
FINDINGS:
  - [INFO] <observation>
  - [WARN] <observation>
REMEDIATION:
  1. <step if MANUAL_STEP_REQUIRED>
```

## When to invoke

Paste a notification design intent or describe the scenario:

- "wire the prod-checkout-critical composite to Slack and PagerDuty"
- "auto-create a Jira ticket when the latency alarm fires"
- "validate the existing alarm-to-Slack workflow (on-call says it's broken)"
- "build a 2-tier escalation: primary then secondary after 5 min"
- "set up AWS User Notifications for alarm delivery to Slack"
- "add Amazon Q triage to the alarm notifications"

A bare alarm name + any notification verb ("wire this alarm to Slack",
"page on-call on this alarm") also routes here via the orchestrator.

## Inputs

- Source alarm(s): alarm name(s) or composite rule to wire.
- Target channels: Slack / Teams / PagerDuty / Opsgenie / SMS / email /
  Jira / ServiceNow.
- Region + account_id (required for ARN construction).
- Escalation tiers: 1 (single page), 2 (primary + secondary), 3 (+ manager).
- Kill-switch type: parameter-store (default) / eventbridge-disable /
  lambda-guard.
- For validation mode: existing EventBridge rule name + SNS topic ARN +
  Lambda forwarder ARN.

## Outputs

- One VERDICT block per workflow.
- SAFETY list with `[PASS]` / `[FAIL]` per gate and reason for failure.
- For AUTOMATED: the full WORKFLOW block (EventBridge rule, SNS topic,
  Lambda ARNs, subscription status, escalation state machine, ticket
  integration, User Notifications hub) plus deployment commands.
- For MANUAL_STEP_REQUIRED: the specific failure (unconfirmed
  subscription, missing `lambda:add-permission`, hardcoded webhook,
  no kill-switch, no ticket idempotency, no test publish) and the exact
  remediation command.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Automate specialist for alarm notification/escalation).
- `/aws:operate-cloudwatch-alarm` for creating/tuning the underlying
  alarm threshold itself (this skill wires the notification layer on
  top of alarms the operator creates).
- `/aws:audit-cloudwatch-alarm` for auditing existing alarm
  configurations.
