---
description: Design and implement automated AWS Health event response. Cover the three event type categories (issue, accountNotification, scheduledChange), EventBridge rules routing Health events to SNS + Lambda responders (Slack/Teams notify, Jira ticket create, DR failover trigger gated behind impact evaluation, Auto Scaling scale-out, access key rotation), Health API affected-entity enrichment, organizational view for org-level events across all member accounts, EventBridge Scheduler for scheduled-change lead-time actions, and AWS User Notifications for managed chat delivery. Enforces dead-letter queue on every target, org-view enablement for orgs, and eventArn-based responder idempotency.
nl_triggers:
  - "AWS Health event automation"
  - "EventBridge rule for Health"
  - "Health affected entity"
  - "Health organizational view"
  - "scheduled change lead-time"
  - "Health event SNS Lambda"
  - "Slack notification for Health"
  - "Jira ticket from Health event"
  - "DR failover from Health"
  - "Auto Scaling scale-out on Health"
  - "AWS User Notifications"
  - "Health Omics alert"
  - "accountNotification automation"
  - "scheduledChange automation"
  - "credential exposed Health"
  - "instance retirement scheduled change"
routes_to: health-event-automator
---

# /aws:automate-health-event

Activate the `health-event-automator` skill and produce a Health event
response automation playbook (or validation report).

## What it does

Reads event categories (issue, accountNotification, scheduledChange),
service scope, regions, accounts scope (single or org), and responder
targets (Slack/Teams/Jira/DR/scale-out/custom), and either:

1. **Designs** a complete responder playbook with: EventBridge rules per
   category and region, Health API affected-entity enrichment Lambda,
   SNS topics + Lambda responders (Slack notify, Jira create, DR trigger
   gated behind ImpactChoice, scale-out with capacity check, access key
   rotation for credential-exposed notifications), Step Functions
   orchestrator (EnrichEntities -> EvaluateImpact -> ImpactChoice ->
   TriggerDRFailover | ScaleOut | NotifyOnly -> CreateJiraTicket),
   organizational view setup for multi-account orgs (enable service
   access from management account + delegate admin), EventBridge Scheduler
   for scheduled-change lead-time actions, AWS User Notifications for
   managed chat delivery, dead-letter queue on every target, and
   eventArn-based responder idempotency.
2. **Validates** an existing Health responder workflow against the
   mandatory safety baseline (DR trigger gated behind ImpactChoice, DLQ
   on every EventBridge target, affected-entity enrichment step, org view
   enabled for orgs, lead-time action for scheduledChange, eventArn
   dedup, synthetic event replay tested within 90 days).

Emits a deterministic block per design:

```text
EVENT_TYPES:
  - [PASS|FAIL] issue rule configured
  - [PASS|FAIL] accountNotification rule configured
  - [PASS|FAIL] scheduledChange rule configured
AFFECTED_ENTITIES:
  - [PASS|FAIL] describe-affected-entities enrichment step
  - [PASS|FAIL] entityValue scoped to region + account in payload
RESPONDERS:
  - [PASS|FAIL] Notify (Slack/Teams/User Notifications) target
  - [PASS|FAIL] Ticketing (Jira) target with eventArn correlation
  - [PASS|FAIL] DR failover trigger gated behind impact evaluation
  - [PASS|FAIL] Scale-out responder with capacity headroom check
  - [PASS|FAIL] Dead-letter queue on every EventBridge target
ORG_VIEW:
  - [PASS|FAIL] Organizational view enabled (or N/A: single-account)
  - [PASS|FAIL] Delegated administrator configured (or N/A)
SCHEDULED_CHANGES:
  - [PASS|FAIL] Lead-time action via EventBridge Scheduler (or N/A: no scheduledChange)
  - [PASS|FAIL] scheduledEndTime re-fetched before action fires
VERIFICATION:
  - [PASS|FAIL] Event replay tested (synthetic Health event)
  - [PASS|FAIL] Health API poller as backup for EventBridge lag (recommended)
  - [PASS|FAIL] Responder idempotency verified (eventArn dedup)
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
FINDINGS:
  - [INFO|WARN|HIGH|CRITICAL] <observation>
REMEDIATION:
  <numbered steps for fixing any FAIL findings>
```

## When to invoke

Provide event categories + responder targets and ask any of:

- "route issue events for EC2 and RDS to Slack + Jira"
- "set up organizational Health view for my 25-account org"
- "automate scheduled-change lead-time actions for instance retirement"
- "trigger DR failover from a region-wide Health event"
- "page security when a Health event says an access key is exposed"
- "validate our existing Health event responder workflow for gaps"
- "wire User Notifications for Slack delivery of Health events"

A bare Health / event / automation prompt routes here via the orchestrator.

## Inputs

- **Required:** event_categories (subset of issue, accountNotification,
  scheduledChange), accounts_scope (single | org), responder_targets
  (subset of slack, teams, jira, dr, scale-out, key-rotation, custom).
- **Recommended:** services (e.g., EC2, RDS, S3; or `["*"]`), regions
  (e.g., us-east-1, us-west-2; or `["*"]`), delegated_admin_account_id
  (for org scope), lead_time_days (for scheduledChange, default 7).
- **For validation mode:** existing EventBridge rule JSON, Lambda
  responder code, Step Functions ASL JSON, DLQ configuration.

## Outputs

- One VERDICT block per design (AUTOMATED or MANUAL_STEP_REQUIRED).
- The complete responder playbook (EventBridge rules, Lambda functions,
  Step Functions ASL, SNS topics, DLQs) in EVENT_TYPES/AFFECTED_ENTITIES/
  RESPONDERS/ORG_VIEW/SCHEDULED_CHANGES.
- Gate pass/fail per dimension in EVENT_TYPES/RESPONDERS/VERIFICATION.
- Specific remediation steps for any failing gate in REMEDIATION.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 4 Automate specialist for AWS Health events).
- `/aws:automate-dr-failover` to design the DR orchestrator that this
  skill triggers (Health is the trigger; DR skill is the strategy).
- `/aws:automate-incident-response` for general incident response design
  (Health is one of several triggers that can invoke IR orchestration).
- `/aws:audit-health-event` for auditing existing Health event posture
  (a verification input for this skill's responder chain).
- `/aws:automate-event-driven-architecture` to design the broader
  EventBridge topology this skill fits into.
