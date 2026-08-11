# Example usage: health-event-automator

A walkthrough showing the skill designing a Health event automation
playbook for an organization with 25 member accounts. Routes issue and
scheduledChange events to Slack + Jira, with DR failover gated behind
impact evaluation. The skill emits an AUTOMATED verdict.

## Input (user prompt)

> Design AWS Health event automation for our org (25 member accounts,
> delegated admin in audit account). Route issue events for EC2 and RDS
> to Slack + create Jira tickets, trigger DR failover only on region-wide
> outages, and create lead-time actions for scheduled changes. Also
> handle accountNotification for exposed credentials.

## Skill output

```text
EVENT_TYPES:
  - [PASS] issue rule: aws.health / EC2 + RDS / all active regions (org)
  - [PASS] accountNotification rule: aws.health / credential exposed
  - [PASS] scheduledChange rule: aws.health / EC2 + RDS / all regions (org)
AFFECTED_ENTITIES:
  - [PASS] Lambda health-enrich-entities calls describe-affected-entities
  - [PASS] Payload includes entityValue, awsAccountId, region
RESPONDERS:
  - [PASS] Slack notify via Lambda webhook (with DLQ health-dlq)
  - [PASS] Jira create with eventArn in labels for dedup
  - [PASS] DR failover trigger gated behind ImpactChoice (region_outage)
  - [PASS] Scale-out: update-auto-scaling-group with MaxSize check
  - [PASS] DLQ: sqs health-dlq on every EventBridge target
ORG_VIEW:
  - [PASS] enable-health-service-access-for-organization run
  - [PASS] Delegated admin: 222222222222 (audit account, us-east-1)
SCHEDULED_CHANGES:
  - [PASS] Lead-time action: EventBridge Scheduler at scheduledEndTime - 7d
  - [PASS] Re-fetch event before firing lead-time action
VERIFICATION:
  - [PASS] Synthetic event replay: 2026-08-01, end-to-end 12s
  - [PASS] Poller: EventBridge + 60s describe-events fallback
  - [PASS] Idempotency: Jira dedup on eventArn label
VERDICT: AUTOMATED
FINDINGS:
  - [INFO] 25 member accounts covered via single org-view rule
  - [INFO] Health API poller in audit account as backup for EventBridge lag
  - [WARN] Lead-time action depends on accurate scheduledEndTime — re-fetch before firing
REMEDIATION:
  1. Add ElastiCache failover coverage for Health events on cache nodes
  2. Document the eventArn-to-Jira-key mapping in the runbook
```

## What the skill caught that a generic assistant misses

1. **Org view requires management-account enablement.** A generic assistant
   may only delegate admin. The skill requires
   `enable-health-service-access-for-organization` from the management
   account first — without it, the delegated admin sees no events.

2. **DR trigger gated behind ImpactChoice.** A generic assistant may wire
   the issue event directly to the DR orchestrator. The skill requires an
   `ImpactChoice` state that evaluates the event code and entity count
   before triggering failover — a single degraded host is not a regional
   outage.

3. **DLQ on every EventBridge target.** A generic assistant may skip DLQs
   because Health events are low-volume. The skill requires DLQs because
   the events are high-urgency — a silently-dropped event is a missed
   outage.

4. **Affected-entity enrichment is non-negotiable.** A generic assistant
   may send the raw event to Slack. The skill requires a
   `describe-affected-entities` call so the message includes specific
   resource IDs — "EC2 issue" is useless; "i-0abc123 degraded in
   us-east-1a" is actionable.

5. **scheduledEndTime re-fetch.** A generic assistant may schedule the
   lead-time action from the initial `scheduledEndTime`. The skill
   requires a re-fetch before firing — AWS shifts windows; the cached
   deadline may be stale by days.

6. **Poller fallback for tier-0.** A generic assistant may rely on
   EventBridge alone. The skill recommends a 60-second
   `describe-events` poller as backup — public Health events lag the
   API by up to 10 minutes.

7. **Jira dedup on eventArn.** A generic assistant may create a new ticket
   for every event update. The skill requires dedup via a Jira label
   matching the `eventArn` — one ticket per event, comments for updates.

## Slash-command invocation

```
/aws:automate-health-event
```

Or via the orchestrator:

```
/aws:pipeline
You: "route Health issue events for EC2 in our org to Slack + Jira, with DR failover on region outage"
```

## Live-account follow-up (optional, requires AWS CLI)

After deploying the responder chain, validate the posture:

```bash
# Verify Health API access (Business/Enterprise required)
aws health describe-events --profile default --query 'events[0].arn'

# Verify org view enabled
aws health describe-health-service-status --profile default

# Verify delegated admin
aws organizations list-delegated-administrators \
  --service-principal health.amazonaws.com \
  --profile management-profile

# Verify the EventBridge rule firing
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name Invocations \
  --dimensions Name=RuleName,Value=health-issue-ec2-rds \
  --start-time 2026-08-01T00:00:00Z --end-time 2026-08-10T00:00:00Z \
  --period 86400 --statistics Sum --profile default

# Verify the DLQ is empty (no silently-dropped events)
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/health-dlq \
  --attribute-names ApproximateNumberOfMessagesVisible --profile default

# Verify the scheduler has the lead-time schedule
aws scheduler list-schedules --profile default
```
