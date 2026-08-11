# Eval prompt: user-notifications-chat

Design AWS Health automation using AWS User Notifications for managed
chat delivery. Emit the standard Health block (EVENT_TYPES,
AFFECTED_ENTITIES, RESPONDERS, ORG_VIEW, SCHEDULED_CHANGES,
VERIFICATION, VERDICT, FINDINGS, REMEDIATION).

Requirements:
- Event categories: issue
- Services: EC2, RDS, S3
- Regions: us-east-1, us-west-2
- Accounts scope: single
- Chat delivery: AWS User Notifications Slack channel for immediate
  notify on every issue event (managed, no custom Lambda)
- Action responder: EventBridge + Lambda for DR failover trigger
  - DR trigger gated behind ImpactChoice (region_outage severity only)
  - Single-host degradation routed to scale-out, not failover
- Affected-entity enrichment Lambda (describe-affected-entities) runs
  before DR trigger to populate the impact evaluation
- DLQ on Lambda target (sqs health-dlq)
- Synthetic event replay: 2026-08-05, end-to-end 9s
- Idempotency: dedup on eventArn in Step Functions

Expected: AUTOMATED. User Notifications handles the chat delivery
(managed), EventBridge + Lambda handles the action responder (DR
trigger gated behind ImpactChoice), affected entities are enriched
before any state-changing action, DLQ catches failed deliveries, and
the chain is replay-tested.
