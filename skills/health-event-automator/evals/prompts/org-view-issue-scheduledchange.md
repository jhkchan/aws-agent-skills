# Eval prompt: org-view-issue-scheduledchange

Design AWS Health event automation for our org (25 member accounts,
delegated admin in audit account 222222222222). Emit the standard Health
block (EVENT_TYPES, AFFECTED_ENTITIES, RESPONDERS, ORG_VIEW,
SCHEDULED_CHANGES, VERIFICATION, VERDICT, FINDINGS, REMEDIATION).

Requirements:
- Event categories: issue, accountNotification, scheduledChange
- Services: EC2, RDS
- Regions: all active (us-east-1, us-west-2, eu-west-1)
- Accounts scope: organizational (25 member accounts)
- Responders:
  - Slack notify (Lambda webhook)
  - Jira create (Lambda with eventArn in labels for dedup)
  - DR failover trigger (region outage only, gated behind ImpactChoice)
  - Auto Scaling scale-out (EC2 host degradation, MaxSize check)
  - Access key rotation (credential exposed notification)
- Org view: enable-health-service-access-for-organization run from
  management account, delegated admin in audit account 222222222222
- Lead time: 7 days before scheduledEndTime for scheduledChange
  (replace retired instance via launch template)
- scheduledEndTime re-fetch before firing lead-time action
- DLQ on every EventBridge target
- Synthetic event replay: 2026-08-01, end-to-end 12s
- Poller fallback: 60s describe-events cadence on tier-0 workloads
- Idempotency: Jira dedup on eventArn label, Step Functions dedup on
  eventArn

Expected: AUTOMATED. The responder chain covers all three event
categories with mapped affected entities, an ImpactChoice-gated DR
trigger, lead-time actions for scheduledChange, org view centralized
across 25 accounts, and eventArn-based idempotency.
