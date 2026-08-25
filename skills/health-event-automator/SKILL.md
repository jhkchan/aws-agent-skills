---
name: health-event-automator
description: Designs AWS Health event response automation across the three event type categories (issue, accountNotification, scheduledChange), EventBridge rules routing Health events to SNS, Lambda responders (Slack/Teams notify, Jira ticket create, DR failover trigger, Auto Scaling scale-out), AWS Health API affected-entity mapping, organizational view for org-level Health events across all member accounts, AWS User Notifications chat delivery, AWS Health Omics workflow alerts, and EventBridge Scheduler for scheduled-change lead-time actions. Emits AUTOMATED with the responder playbook or MANUAL_STEP_REQUIRED with the gap. Use when designing Health event automation, org-level health visibility, or scheduled-change remediation workflows.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan authoring. Live deployment uses aws health describe-events / describe-affected-entities, aws health describe-aggregate-offers (org), aws events put-rule (Health event pattern), aws events put-targets (SNS/Lambda), aws scheduler create-schedule (scheduled-change lead-time), aws notifications contacts / channels (User Notifications), aws backup start-restore-job (DR trigger)...
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
  when_to_use: Designing Health event response automation, wiring EventBridge rules for AWS Health events (issue, accountNotification, scheduledChange), mapping affected entities, building organizational-view Health dashboards, automating Slack/Teams/Jira notifications, triggering DR failover or scale-out from Health events, scheduling lead-time actions for scheduled changes, or routing Health Omics workflow alerts.
  when_not_to_use: General incident response without an AWS Health signal (use incident-response-automator — Health is one trigger source)., DR failover design itself (use dr-failover-automator — this skill triggers failover, it does not design the strategy)., Security finding triage (use guardduty / security-hub skills — Health events are operational, not security findings)., Cost anomaly response (use cost-anomaly-response-automator — Health events are not billing signals).
  activation_triggers: AWS Health event automation, EventBridge rule for Health, Health affected entity, Health organizational view, scheduled change lead-time, Health event SNS Lambda, Slack notification for Health, Jira ticket from Health event, DR failover from Health, Auto Scaling scale-out on Health, AWS User Notifications, Health Omics alert, accountNotification automation, scheduledChange automation
  invocation_schema: 'Input: either (a) a Health automation requirement ("route issue events for EC2 in org to Slack + create Jira, with DR failover on region outage"), OR (b) an existing EventBridge Health rule / responder workflow to audit and harden. Output: deterministic Health block per requirement — EVENT_TYPES/AFFECTED_ENTITIES/RESPONDERS/ORG_VIEW/ SCHEDULED_CHANGES/VERIFICATION/VERDICT — where VERDICT is AUTOMATED (responder playbook complete with all gates passing) or MANUAL_STEP_REQUIRED (specific gap cited, e.g., no affected-entity enrichment, no org-level rule, lead-time action missing).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS Health, Health event, EventBridge rule, event type category, issue, accountNotification, scheduledChange, affected entity, organizational view, Health API, Health Omics, User Notifications, scheduled change, lead-time action, EventBridge Scheduler, SNS Lambda responder, Slack notification, Jira ticket, DR failover trigger, Auto Scaling scale-out
  tags: aws-health, eventbridge, sns, lambda, user-notifications, automate
---

# Health Event Automator

## What this skill does

Designs automated AWS Health event response across the three event type
categories — **issue** (ongoing operational problems), **accountNotification**
(notifications like billing, abuse, credential exposure), and
**scheduledChange** (upcoming AWS-driven changes like retirement, reboot,
maintenance) — and the building blocks that compose each: EventBridge rules
matching the Health event pattern, SNS topics + Lambda responders (Slack/Teams
notify, Jira ticket create, DR failover trigger, Auto Scaling scale-out),
Health API affected-entity enrichment, organizational-view rules for
org-level events across all member accounts, EventBridge Scheduler for
scheduled-change lead-time actions, and AWS User Notifications for chat
delivery.

The verdict is binary: **AUTOMATED** when the playbook covers a chosen event
category with mapped affected entities, a defined responder chain, org-level
visibility (for orgs), lead-time action for scheduled changes (if any), and
verification step; **MANUAL_STEP_REQUIRED** when any component is missing
(e.g., no affected-entity enrichment, single-account-only rule in an org,
responder chain has no dead-letter queue, scheduled change has no lead-time
action).

## Quick navigation

| # | Section | Jump when |
|---|---|---|
| 1 | [Pre-flight gate](#pre-flight-health-spec-gate) | Starting any design — blocks unsafe specs |
| 2 | [Event type categories](#event-type-categories) | issue / accountNotification / scheduledChange |
| 3 | [EventBridge rule](#eventbridge-rule-for-health-events) | The Health event pattern + scope |
| 4 | [Affected-entity mapping](#affected-entity-mapping) | Enrich events with affected resources |
| 5 | [SNS + Lambda responders](#sns--lambda-responders) | Slack/Teams/Jira/DR/scale-out |
| 6 | [Organizational view](#organizational-view-org-level-health) | Multi-account org-wide Health events |
| 7 | [Scheduled changes](#scheduled-change-lead-time-actions) | EventBridge Scheduler lead-time actions |
| 8 | [User Notifications](#aws-user-notifications-chat-delivery) | Managed chat / email delivery |
| 9 | [Health Omics](#aws-health-omics-workflow-alerts) | Omics workflow Health events |
| 10 | [Step Functions orchestrator](#step-functions-responder-orchestration) | Multi-step responder state machine |
| 11 | [STRICT output contract](#output-format-strict-output-contract) | The exact Health block the skill emits |
| 12 | [NEVER anti-patterns](#never-these-things) | The hardcoded list of Health taboos |
| 13 | [Expert heuristic](#expert-heuristic-callouts) | Non-obvious behaviors that change the design |
| 14 | [Recent AWS features](#recent-aws-features-2024-2026) | User Notifications, Health Omics, Scheduler |
| 15 | [Edge cases](#edge-case-handling) | Public-event lag, region scoping, DLQ |

## Mindset

**One-line takeaway:** AWS Health is the **upstream signal AWS emits about
its own platform** — every minute between the event firing and the right
responder acting on it is a minute of customer impact. The art is routing
each event category to the responder that knows what to do with it, with
enough context (affected entities, region, account) that no human triage is
required.

- **The event category determines the responder, not the other way around.**
  An `issue` event for an EC2 host degradation triggers scale-out and DR
  evaluation. A `scheduledChange` for instance retirement triggers a
  lead-time action (replace before the deadline). An `accountNotification`
  for exposed credentials triggers key rotation. Design the routing per
  category.
- **Public Health events lag the Health API by up to 10 minutes.** EventBridge
  fires on the public event stream. For the fastest detection, use the Health
  API `describe-events` on a 60-second poller in addition to EventBridge.
- **Affected entities are the bridge to action.** A Health event without
  affected entities is a generic notice ("something is wrong in EC2"). With
  affected entities ("i-0abc123, i-0def456 in us-east-1a"), the responder
  can drain, replace, or failover the specific resources.

## Pre-flight: Health spec gate (run before generation)

| Attribute | Required | Effect on plan |
|---|---|---|
| `event_categories` | YES | Which categories to handle (issue, accountNotification, scheduledChange) |
| `services` | Recommended | Scope (EC2, RDS, S3, etc.) — `["*"]` for all |
| `regions` | Recommended | Scope (`["*"]` for all, or specific regions) |
| `accounts_scope` | YES | Single-account OR organizational (delegated admin) |
| `responder_targets` | YES | Slack / Teams / Jira / DR failover / scale-out / custom |
| `existing_workflow` | For audit mode | When provided, run the layer gates |

**If the spec is incomplete**, output:

```text
EVENT_TYPES: <unknown>
AFFECTED_ENTITIES: <unknown>
RESPONDERS: <unknown>
ORG_VIEW: <unknown>
SCHEDULED_CHANGES: <unknown>
VERIFICATION: <unknown>
VERDICT: MANUAL_STEP_REQUIRED
REASON: Spec is missing required fields (<list>).
REQUIRED:
  - event_categories (subset of [issue, accountNotification, scheduledChange])
  - accounts_scope (single | org)
  - responder_targets (one or more of slack, teams, jira, dr, scale-out, custom)
REMEDIATION: Provide all required fields. Example: "route issue and
scheduledChange events for EC2 and RDS in org to Slack + Jira, with DR
failover on region outage" maps to event_categories=[issue, scheduledChange],
accounts_scope=org, services=[EC2, RDS], responder_targets=[slack, jira, dr].
```

**Live-account pre-flight checks (skip for offline authoring):**
1. Verify Health API access: `aws health describe-events` (requires Business/Enterprise support).
2. Verify EventBridge default bus receives Health events: `aws events list-rules --event-bus-type.aws-service health`.
3. For org: verify delegated admin: `aws organizations list-delegated-administrators --service-principal health.amazonaws.com`.
4. Verify SNS topic exists: `aws sns list-topics`.
5. Verify User Notifications channel: `aws notifications list-channels`.

## Event type categories

| Category | What it means | Example | Default responder |
|---|---|---|---|
| `issue` | Ongoing operational problem on an AWS resource | EC2 host degradation, RDS cluster interruption | Scale-out + DR evaluation + notify |
| `accountNotification` | Notification about the account itself | Billing threshold, abuse report, exposed access key | Page security/finance owner + rotate key |
| `scheduledChange` | Upcoming AWS-driven change | EC2 instance retirement, RDS maintenance, deprecation | Schedule lead-time action before deadline |

**EventBridge event pattern key:**

```json
{
  "source": ["aws.health"],
  "detail": {
    "eventTypeCategory": ["issue", "accountNotification", "scheduledChange"]
  }
}
```

The `detail.eventTypeCategory` is the primary routing lever. Sub-filter by
`service` (`detail.service`) and `region` (`region`) for finer scoping.

## EventBridge rule for Health events

```bash
# Single-account rule: all issue events for EC2 and RDS
aws events put-rule --name health-issue-ec2-rds \
  --event-pattern '{
    "source": ["aws.health"],
    "detail": {
      "eventTypeCategory": ["issue"],
      "service": ["EC2", "RDS"]
    }
  }' \
  --state ENABLED

# Add an SNS target
aws events put-targets --rule health-issue-ec2-rds \
  --targets '[{"Id":"HealthTopic","Arn":"arn:aws:sns:us-east-1:111111111111:health-issue-alerts","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:health-dlq"}}]'

# Add a Lambda target (responder)
aws events put-targets --rule health-issue-ec2-rds \
  --targets '[{"Id":"HealthResponder","Arn":"arn:aws:lambda:us-east-1:111111111111:function:health-responder"}]'
```

**Scope options:**
- By service: `"service": ["EC2", "RDS", "S3"]`
- By region: deploy the rule in each region of interest (Health events fire
  in the region of the affected resource).
- By event code: `"eventTypeCode": ["AWS_EC2_INSTANCE_DEGRADATION"]`

**Gotchas:** Health events fire on the **default EventBridge bus** in the
region of the affected resource. To aggregate centrally, forward from each
region's default bus to a central bus in us-east-1 (or use the org
organizational-view rule). Without a DLQ target, events that fail delivery
are silently dropped.

## Affected-entity mapping

A Health event has an `eventArn`. The list of affected resources (instance
IDs, cluster ARNs, bucket names) comes from a second API call:

```bash
# Get the event first
aws health describe-events --filter 'eventStatusCodes=[open]' \
  --query 'events[0].arn' --output text

# Map affected entities
aws health describe-affected-entities \
  --filter 'eventArns=[arn:aws:health:us-east-1::event/EC2/AWS_EC2_INSTANCE_DEGRADATION/xxx]' \
  --query 'entities[*].entityValue' --output table
```

**Enrichment pattern (Lambda responder):**

```python
import boto3, json, os
health = boto3.client('health', region_name='us-east-1')
sns = boto3.client('sns')

def lambda_handler(event, context):
    detail = event['detail']
    event_arn = detail['eventArn']
    # Health API is global endpoint — always us-east-1
    entities = health.describe_affected_entities(
        filter={'eventArns': [event_arn]}
    )['entities']
    affected = [e['entityValue'] for e in entities]
    message = {
        'category': detail['eventTypeCategory'],
        'service': detail['service'],
        'code': detail['eventTypeCode'],
        'region': event['region'],
        'start_time': detail['startTime'],
        'affected_entities': affected,
        'event_arn': event_arn
    }
    sns.publish(
        TopicArn=os.environ['TOPIC_ARN'],
        Subject=f"[{detail['eventTypeCategory']}] {detail['service']} - {detail['eventTypeCode']}",
        Message=json.dumps(message, indent=2, default=str)
    )
    return {'statusCode': 200, 'affected_count': len(affected)}
```

**Gotchas:** The Health API endpoint is global (`us-east-1`) regardless of
where the event fires. `describe-affected-entities` requires a Business or
Enterprise support plan. The `entityValue` is region-scoped (e.g., `i-0abc`
is unique within a region + account) — always include region in the
enrichment payload.

## SNS + Lambda responders

| Responder | Trigger | Action |
|---|---|---|
| Slack/Teams notify | All categories | Post to webhook with event payload + affected entities |
| Jira ticket create | issue, scheduledChange | Create ticket with eventArn as correlation ID |
| DR failover trigger | issue (region outage) | Invoke `dr-failover-orchestrator` Step Functions |
| Auto Scaling scale-out | issue (EC2 host degradation) | Update ASG desired capacity, drain affected instances |
| Access key rotation | accountNotification (exposed key) | Deactivate + create replacement, notify owner |
| Patch lead-time | scheduledChange (retirement) | Schedule replacement via EventBridge Scheduler |

**Slack notification Lambda (excerpt):**

```python
import json, urllib.request, os

WEBHOOK = os.environ['SLACK_WEBHOOK']

def lambda_handler(event, context):
    detail = event['detail']
    blocks = [
        {"type": "header", "text": {"type": "plain_text",
         "text": f"AWS Health: {detail['eventTypeCategory']} - {detail['service']}"}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*Code:*\n{detail['eventTypeCode']}"},
            {"type": "mrkdwn", "text": f"*Region:*\n{event['region']}"},
            {"type": "mrkdwn", "text": f"*Status:*\n{detail.get('statusCode','unknown')}"},
            {"type": "mrkdwn", "text": f"*Start:*\n{str(detail.get('startTime'))}"}
        ]},
        {"type": "section", "text": {"type": "mrkdwn",
         "text": f"*Description:*\n{detail.get('eventDescription',[{}])[0].get('latestDescription','N/A')}"}}
    ]
    req = urllib.request.Request(
        WEBHOOK,
        data=json.dumps({'blocks': blocks}).encode(),
        headers={'Content-Type': 'application/json'}
    )
    urllib.request.urlopen(req)
    return {'statusCode': 200}
```

**Dead-letter handling:** Every EventBridge target needs a DLQ. Health
events are low-volume (a few per day on a quiet account) but high-urgency —
a silently-dropped event is a missed outage signal. Configure
`DeadLetterConfig` on every target.

## Organizational view (org-level Health)

For AWS Organizations, enable the organizational view feature so a delegated
administrator account sees aggregated Health events across all member
accounts.

```bash
# In the management account: enable Health org view
aws health enable-health-service-access-for-organization

# Delegate admin to a member account
aws organizations register-delegated-administrator \
  --account-id 222222222222 \
  --service-principal health.amazonaws.com

# In the delegated admin account: org-wide EventBridge rule
aws events put-rule --name health-org-all-accounts \
  --event-pattern '{"source": ["aws.health"]}' \
  --state ENABLED
```

Then in the delegated admin account, the Health API returns events across
all member accounts:

```bash
aws health describe-events-for-organization \
  --filter 'eventTypeCategories=[issue,scheduledChange]' \
  --query 'events[*].[arn,awsAccountId,service,region,statusCode]' \
  --output table
```

**Gotchas:** Org view rules fire ONLY in the delegated admin account's
default bus. The delegated admin needs an IAM policy allowing
`health:Describe*` and `organizations:Describe*`. Events from member
accounts still appear on the member account's default bus too — pick one
ingestion path to avoid double-processing.

## Scheduled change lead-time actions

Scheduled-change events carry a `scheduledEndTime` — the deadline by which
AWS will perform the action (or retire the resource). The pattern: schedule
a lead-time responder (e.g., 7 days before) so the team can act first.

```bash
# Parse the scheduledEndTime, schedule a lead-time action 7 days prior
aws scheduler create-schedule \
  --name health-leadtime-instance-retirement \
  --schedule-expression "at(2026-08-25T03:00:00)" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target '{"Arn":"arn:aws:lambda:us-east-1:111111111111:function:replace-retired-instance","RoleArn":"arn:aws:iam::111111111111:role/SchedulerInvokeRole"}' \
  --start-date "2026-08-18T00:00:00" --end-date "2026-08-26T00:00:00"
```

**Lead-time defaults:**
| Change type | Default lead time | Action |
|---|---|---|
| Instance retirement | 7 days before | Replace via launch template + drain |
| RDS maintenance | 1 day before | Verify standby is current, plan failover window |
| API deprecation | 30 days before | Migrate code path |
| Certificate rotation | 7 days before | Verify renewal completed |

**Gotchas:** `scheduledEndTime` can shift — AWS sometimes extends the
window. Re-fetch the event before the lead-time action fires. EventBridge
Scheduler has a 1-year max schedule; long deprecations need a recurring
schedule or a different mechanism.

## AWS User Notifications (chat delivery)

AWS User Notifications (2024-2025) is a managed service that delivers Health
events (and other AWS notifications) to chat (Slack, Chime, Teams) and email
without custom Lambda code.

```bash
# Create a notification channel (Slack)
aws notifications create-channel \
  --name health-slack \
  --type SLACK \
  --configuration '{"workspaceId":"T0001","channelId":"C123456"}'

# Create a notification configuration matching Health events
aws notifications create-notification-configuration \
  --name health-events \
  --source 'aws.health' \
  --channel-arns 'arn:aws:notifications:us-east-1:111111111111:channel/health-slack'
```

**Trade-off:** User Notifications is turnkey but limited in transformation
(affected-entity enrichment, custom routing by service). For complex routing
or responders (DR trigger, scale-out), EventBridge + Lambda remains the
default. A common pattern: User Notifications for chat delivery +
EventBridge + Lambda for action responders.

## AWS Health Omics workflow alerts

AWS Health Omics (2024-2025) emits Health events for workflow run failures,
aborted runs, and resource quota issues. The event pattern:

```json
{
  "source": ["aws.health"],
  "detail": {
    "service": ["OMICS"],
    "eventTypeCategory": ["issue"]
  }
}
```

Omics-specific gotchas: workflow runs are long-lived (hours) — the Health
event may fire well after the user-facing failure. Pair with Omics CloudWatch
metrics for synchronous alerting.

## Step Functions responder orchestration

For multi-step responders (e.g., issue → enrich entities → evaluate impact →
trigger DR or scale-out → notify), use Step Functions:

```json
{
  "StartAt": "EnrichEntities",
  "States": {
    "EnrichEntities": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:<region>:<account>:function:health-enrich-entities",
      "Next": "EvaluateImpact"
    },
    "EvaluateImpact": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:<region>:<account>:function:health-evaluate-impact",
      "Next": "ImpactChoice"
    },
    "ImpactChoice": {
      "Type": "Choice",
      "Choices": [
        {"Variable": "$.impactLevel", "StringEquals": "region_outage", "Next": "TriggerDRFailover"},
        {"Variable": "$.impactLevel", "StringEquals": "resource_degradation", "Next": "ScaleOut"},
        {"Variable": "$.impactLevel", "StringEquals": "low", "Next": "NotifyOnly"}
      ],
      "Default": "NotifyOnly"
    },
    "TriggerDRFailover": {
      "Type": "Task",
      "Resource": "arn:aws:states:::states:startExecution",
      "Parameters": {"StateMachineArn": "arn:aws:states:<region>:<account>:stateMachine:dr-failover-orchestrator",
        "Input.$": "$"},
      "Next": "NotifyStakeholders"
    },
    "ScaleOut": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:<region>:<account>:function:health-scale-out-asg",
      "Next": "NotifyStakeholders"
    },
    "NotifyOnly": {
      "Type": "Task",
      "Resource": "arn:aws:sns:<region>:<account>:health-issue-alerts",
      "Next": "CreateJiraTicket"
    },
    "NotifyStakeholders": {
      "Type": "Task",
      "Resource": "arn:aws:sns:<region>:<account>:health-critical-alerts",
      "Next": "CreateJiraTicket"
    },
    "CreateJiraTicket": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:<region>:<account>:function:jira-create-from-health",
      "Retry": [{"ErrorEquals": ["States.TaskFailed"], "IntervalSeconds": 60, "MaxAttempts": 3}],
      "End": true
    }
  }
}
```

**Gotchas:** Always evaluate impact before triggering DR failover — not
every Health `issue` is a region outage. The `ImpactChoice` state is the
human-in-the-loop safety net: a misrouted `low` event should never trigger
a failover.

## Output format (STRICT output contract)

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
  1. <step 1>
  2. <step 2>
```

### Worked example — AUTOMATED issue + scheduledChange
```text
EVENT_TYPES:
  - [PASS] issue rule: aws.health / EC2 + RDS / us-east-1, us-west-2
  - [PASS] accountNotification rule: aws.health / all services / global
  - [PASS] scheduledChange rule: aws.health / EC2 / all regions
AFFECTED_ENTITIES:
  - [PASS] Lambda health-enrich-entities calls describe-affected-entities
  - [PASS] Payload includes entityValue, awsAccountId, region
RESPONDERS:
  - [PASS] Slack notify via Lambda webhook (with DLQ)
  - [PASS] Jira create via Lambda with eventArn in description
  - [PASS] DR failover trigger gated behind ImpactChoice (region_outage only)
  - [PASS] Scale-out: update-auto-scaling-group + capacity check
  - [PASS] DLQ: sqs health-dlq attached to every target
ORG_VIEW:
  - [PASS] enable-health-service-access-for-organization run
  - [PASS] Delegated admin: 222222222222 (audit account)
SCHEDULED_CHANGES:
  - [PASS] Lead-time action: EventBridge Scheduler at scheduledEndTime - 7d
  - [PASS] Re-fetch event before firing lead-time action
VERIFICATION:
  - [PASS] Synthetic event replay: 2026-07-20, end-to-end 12s
  - [PASS] Poller: EventBridge rule + 60s describe-events fallback
  - [PASS] Idempotency: Step Functions dedup on eventArn
VERDICT: AUTOMATED
FINDINGS:
  - [INFO] Health events fire on default bus in affected resource's region
  - [WARN] User Notifications channel lag: ~30s vs EventBridge ~5s
REMEDIATION:
  1. Consider User Notifications as backup only for chat delivery
```

### Worked example — MANUAL_STEP_REQUIRED (no org view, no DLQ)
```text
EVENT_TYPES:
  - [PASS] issue rule: aws.health / EC2 / us-east-1
  - [FAIL] accountNotification rule missing
  - [FAIL] scheduledChange rule missing
AFFECTED_ENTITIES:
  - [FAIL] No enrichment step — Slack messages lack specific resources
RESPONDERS:
  - [PASS] Slack notify target configured
  - [FAIL] No Jira correlation ID
  - [FAIL] DR trigger wired directly to issue events (no impact gate)
  - [FAIL] No DLQ — failed deliveries silently dropped
ORG_VIEW:
  - [FAIL] Organizational view not enabled (org with 25 accounts)
  - [FAIL] No delegated administrator — per-account rules needed in 25 accounts
SCHEDULED_CHANGES:
  - [FAIL] No lead-time action — instance retirement discovered at deadline
VERIFICATION:
  - [FAIL] No synthetic event replay test
  - [FAIL] No poller fallback
VERDICT: MANUAL_STEP_REQUIRED
FINDINGS:
  - [CRITICAL] DR trigger ungated: any issue event (including single-host
    degradation) triggers full regional failover.
  - [CRITICAL] No DLQ: a Lambda cold-start failure drops the Health event
    silently — missed outage.
  - [HIGH] No org view: 25 member accounts each need their own rule; org-
    wide visibility is lost.
  - [HIGH] No scheduledChange automation: instance retirement will cause
    surprise outages when AWS retires the host.
  - [HIGH] No enrichment: Slack messages say "EC2 issue" with no instance IDs.
REMEDIATION:
  1. Add ImpactChoice state before any DR trigger — only region_outage triggers.
  2. Attach SQS DLQ to every EventBridge target.
  3. Enable org view + delegate admin to centralize across 25 accounts.
  4. Add scheduledChange rule + EventBridge Scheduler lead-time action.
  5. Add enrichment Lambda: describe-affected-entities before notify.
```

## NEVER (these things)

- NEVER trigger DR failover directly from an issue event without an impact
  evaluation step. A single-host degradation is not a regional outage. Wire
  the issue event to an ImpactChoice state in Step Functions; only
  `region_outage` severity triggers the DR orchestrator. Ungated triggers
  cause false-positive failovers.

- NEVER ship an EventBridge rule without a dead-letter queue. Health events
  are low-volume and high-urgency — a Lambda cold-start failure, SNS
  throttle, or transient IAM error silently drops the event. Always attach
  `DeadLetterConfig` to every target.

- NEVER rely on EventBridge alone for time-sensitive detection. Public
  Health events can lag the Health API by up to 10 minutes. For tier-0
  workloads, run a `describe-events` poller on a 60-second cadence as a
  fallback alongside EventBridge.

- NEVER skip affected-entity enrichment. A Health event without entities is
  "something is wrong in EC2" — useless to responders. Always call
  `describe-affected-entities` and include the resource IDs in the payload.
  The Health API requires a Business/Enterprise support plan.

- NEVER assume a single-region rule catches all events. Health events fire
  on the default bus in the affected resource's region. A rule in us-east-1
  does not catch an event for a resource in eu-west-1. Deploy the rule in
  every active region, or use organizational view (delegated admin bus).

## Expert heuristic callouts

- **The Health API endpoint is global (us-east-1) regardless of event
  region.** A `describe-events` call always goes to us-east-1; the
  `region` field in the response tells you where the affected resource is.
- **EventBridge Health events fire on the default bus, not a custom bus.**
  Rules must target the default bus (`--event-bus-name default`) or the
  AWS-default service bus — a custom bus will not see Health events.
- **`eventTypeCode` is the stable identifier for routing.** Examples:
  `AWS_EC2_INSTANCE_DEGRADATION`, `AWS_RDS_MAINTENANCE_SCHEDULED`. Build
  per-code routing tables for high-volume categories.
- **`scheduledEndTime` shifts.** AWS extends windows; re-fetch the event
  before firing the lead-time action. Cache the latest `scheduledEndTime`
  in the Scheduler input.
- **Account-notification events for exposed credentials are urgent.**
  `AWS_ACCOUNT_NOTIFICATION_CREDENTIAL_EXPOSED` means a key was found on a
  public site. Route this to immediate key rotation, not a daily digest.
- **Org view requires the management account to enable it.** Delegated
  admin alone is not enough — `enable-health-service-access-for-organization`
  must run from the management account first.
- **Health Omics workflow events fire post-failure, not pre-failure.**
  Omics runs are long; pair Health with CloudWatch metrics for synchronous
  detection of run failures.
- **User Notifications delivery lag (~30s) is higher than EventBridge
  (~5s).** For sub-minute SLA, use EventBridge + Lambda directly.
- **The `eventDescription` array has `latestDescription` at index 0.** AWS
  appends updates as the event evolves — always read index 0, not the
  last element.
- **Event replay is the only way to verify the responder chain.** AWS
  publishes synthetic Health events for testing; use them quarterly.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before any state-changing responder
  (`autoscaling update-auto-scaling-group`, `stepfunctions start-execution`
  for DR, `iam update-access-key`), emit: `CONFIRM: About to <action>
  triggered by Health event <eventArn>. Proceed? (yes/no)` and wait for
  explicit `yes`.
- **Impact-gate the DR trigger.** The DR orchestrator must be reachable
  only from an `ImpactChoice` that evaluates `region_outage`. Never wire
  DR directly from an issue event.
- **Verify the DLQ is drained.** `aws sqs get-queue-attributes` — a
  growing DLQ means silently-dropped Health events.
- **Verify org view is enabled.** `aws health describe-health-service-status`
  in the delegated admin account.
- **Verify responder idempotency.** Replaying the same `eventArn` should
  not create a second Jira ticket or trigger a second failover. Dedup on
  `eventArn` in the responder state.

## Edge-case handling

- **Public Health events lag the Health API.** A Health event for an
  ongoing issue may appear in `describe-events` before EventBridge fires.
  Run a poller as backup for tier-0 workloads.
- **Region scoping.** A rule in us-east-1 does not catch a Health event for
  a resource in ap-southeast-1. Deploy rules in every active region, or
  use the delegated admin's org-view bus (single rule, all regions).
- **DLQ growth.** A growing `health-dlq` indicates responder failures
  (Lambda cold-start, IAM misconfiguration, SNS throttle). Alarm on
  `ApproximateNumberOfMessagesVisible > 0`.
- **Delegated admin rotation.** When the delegated admin account changes,
  re-enable org view from the management account and re-deploy rules in
  the new delegated admin.
- **Event replay drift.** Synthetic Health events for testing may not
  match the production event schema exactly — pin the test event to the
  schema documented in the AWS Health user guide.
- **Multi-account Health events without org view.** For orgs that cannot
  enable org view (e.g., regulatory constraints), deploy per-account
  rules in every member account and forward to a central bus.

## Recent AWS features (2024-2026)

- **AWS User Notifications (2024-2025):** Managed delivery of Health events
  to Slack, Chime, Teams, and email without custom Lambda. Pairs with
  EventBridge for action responders.
- **AWS Health Omics (2024-2025):** Health events for Omics workflow run
  failures and quota issues. Long-running workflows — pair with CloudWatch.
- **EventBridge Scheduler (2024-2025):** Serverless cron for scheduled-
  change lead-time actions. One-time and recurring schedules with
  flexible time windows.
- **Health API organizational view (2024-2025):** Aggregated Health events
  across all member accounts via a delegated administrator.
- **Health API programmatic access (2024-2025):** Business / Enterprise
  support now includes programmatic (API + EventBridge) access; Basic
  support sees only the Personal Health Dashboard.
- **EventBridge cross-account event routing (2024-2025):** Forward Health
  events from member accounts to a central security / operations bus
  without org view.
- **Health event replay API (2024-2025):** Synthetic event replay for
  responder chain testing.
- **HealthOmics multi-omics workflows (2024-2025):** Expanded Health event
  coverage for variant calling and workflow run states.

## Domain

AWS CloudOps / Health Event Response Automation.

## AWS documentation

- **AWS Health** — https://docs.aws.amazon.com/health/latest/ug/
- **AWS Health API** — https://docs.aws.amazon.com/health/latest/ug/health-api.html
- **AWS Health Organizational View** — https://docs.aws.amazon.com/health/latest/ug/organizational-view.html
- **Amazon EventBridge AWS Health Events** — https://docs.aws.amazon.com/health/latest/ug/cloudwatch-events-based-health-monitoring.html
- **AWS User Notifications** — https://docs.aws.amazon.com/notifications/latest/userguide/
- **AWS Health Omics** — https://docs.aws.amazon.com/omics/
- **Amazon EventBridge Scheduler** — https://docs.aws.amazon.com/scheduler/latest/UserGuide/
- **AWS Support plans** — https://aws.amazon.com/premiumsupport/plans/
- **AWS Health Blog** — https://aws.amazon.com/blogs/infrastructure-and-automation/
