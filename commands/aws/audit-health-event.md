---
description: Audit AWS Health for active open issues, upcoming scheduled changes, affected-entity status, closed-event resolution, Health Organizational View coverage, and EventBridge aws.health integration.
nl_triggers:
  - "audit AWS Health"
  - "check Health Dashboard"
  - "Health events"
  - "ongoing Health event"
  - "scheduled change deadline"
  - "EC2 instance retirement"
  - "affected entities impaired"
  - "RDS operational event"
  - "is Health Organizational View enabled"
  - "EventBridge aws.health rule"
  - "Personal Health Dashboard"
  - "AWS Health posture"
  - "Health event audit"
  - "open Health event"
  - "upcoming scheduled change"
routes_to: health-event-auditor
---

# /aws:audit-health-event

Activate the `health-event-auditor` skill and audit AWS Health events,
affected entities, and account/organization posture.

## What it does

Reads AWS Health event records (eventTypeCategory, eventStatus,
affected entities with statusCode) plus account posture (support tier,
Health Organizational View status, EventBridge aws.health rule
inventory) and applies the ordered classification logic:

1. Account-posture gate — Basic/Developer support cannot call the
   Health API (CONFIG_GAP); API region must be us-east-1.
2. Open issue events — any `IMPAIRED` or `UNKNOWN` entity drives
   UNRESOLVED_EVENT (entity status is authoritative, not event status).
3. Upcoming scheduled changes — `scheduledChange` + `upcoming` status
   drives SCHEDULED_CHANGE with `startTime` as the deadline.
4. Configuration gaps — Health Organizational View disabled on a
   multi-account org (Step 3a); zero EventBridge rules matching
   `aws.health` (Step 3b).
5. Closed events — `closed` + all entities `RESOLVED`/`UNIMPAIRED`
   classifies as OK.
6. Aggregation — worst finding wins
   (UNRESOLVED_EVENT > SCHEDULED_CHANGE > CONFIG_GAP > OK).

Emits a deterministic VERDICT per event (or per account/org scope for
CONFIG_GAP):

```text
EVENT: <eventArn, or "account: <id>" / "org: <id>" for scope audits>
VERDICT: UNRESOLVED_EVENT | SCHEDULED_CHANGE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [UNRESOLVED_EVENT] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a Health event record and ask any of:

- "audit this AWS Health event"
- "is this Health event still impacting resources?"
- "what's the deadline for this scheduled change?"
- "are my affected entities recovered?"
- "is Health Organizational View enabled?"
- "do I have an EventBridge rule for aws.health?"
- "what's my overall AWS Health posture?"

A bare eventArn + any audit verb ("audit this Health event", "check
affected entities") also routes here via the orchestrator.

## Inputs

- One or more AWS Health event records (JSON or text), including
  eventArn, eventTypeCategory, eventStatus, service, eventTypeCode,
  startTime, lastUpdatedTime, eventScopeCode, and the affected-entity
  list with statusCode.
- Account posture: support tier, AWS Organization presence,
  healthServiceAccessStatusForOrganization, EventBridge rule inventory
  on the default bus.
- For org-scope audits: management-account context and any delegated
  administrator configuration.

## Outputs

- One VERDICT block per event (or one for the whole scope).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: stop/start instances for retirement, enable
  org view from the management account, create EventBridge rule with
  source `aws.health`, open a Support case to close verified-resolved
  events.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Audit specialist for AWS Health operational events).
- `/aws:audit-eventbridge-bus-policy` for auditing the event bus policy
  and per-target DLQ posture that carries Health event deliveries.
- `/aws:audit-cloudtrail-org-trail` for forensic audit of past Health
  API calls when events older than 90 days have aged out of the
  Health API retention window.
