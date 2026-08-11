# Eval prompt: scheduled-change-leadtime

Design AWS Health scheduledChange automation for our org (10 member
accounts). Emit the standard Health block (EVENT_TYPES, AFFECTED_ENTITIES,
RESPONDERS, ORG_VIEW, SCHEDULED_CHANGES, VERIFICATION, VERDICT).

Requirements:
- Event categories: scheduledChange only
- Services: EC2, RDS
- Regions: us-east-1, us-west-2
- Accounts scope: organizational (10 member accounts)
- Lead time:
  - EC2 instance retirement: 7 days before scheduledEndTime, replace
    via launch template + drain affected instance
  - RDS maintenance: 1 day before scheduledEndTime, verify standby is
    current and plan failover window
- Lead-time mechanism: EventBridge Scheduler one-time schedule
- scheduledEndTime re-fetch: yes, before firing the lead-time action
  (AWS sometimes extends windows)
- Org view: enable-health-service-access-for-organization run
- Delegated admin: audit account 333333333333
- DLQ on every EventBridge target (sqs health-dlq)
- Affected-entity enrichment Lambda (describe-affected-entities)
- Synthetic event replay: 2026-07-20, validated end-to-end
- Idempotency: dedup on eventArn

Expected: AUTOMATED. The scheduledChange playbook covers lead-time
actions per service with scheduledEndTime re-fetch, org view centralizing
across 10 accounts, and eventArn-based idempotency.
