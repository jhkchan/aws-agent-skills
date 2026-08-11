# Eval prompt: no-dlq-no-impact-gate

Validate this existing AWS Health responder workflow. Emit the standard
Health block (EVENT_TYPES, AFFECTED_ENTITIES, RESPONDERS, ORG_VIEW,
SCHEDULED_CHANGES, VERIFICATION, VERDICT, FINDINGS, REMEDIATION).

Current state:
- Event categories: issue (only — accountNotification and
  scheduledChange are not handled)
- Services: EC2
- Accounts scope: single account
- Existing workflow:
  - EventBridge rule: aws.health / issue / EC2 / us-east-1
  - Lambda target: directly invokes DR failover Step Functions on any
    issue event (no impact evaluation, no ImpactChoice)
  - No DLQ on any EventBridge target
  - No describe-affected-entities enrichment step
  - Slack message says only "EC2 issue" — no instance IDs, region, or
    account in the payload
  - Jira ticket created for every event update (no eventArn dedup —
    duplicate tickets on status changes)
- No synthetic event replay test
- No Health API poller fallback
- No idempotency anywhere

Expected: MANUAL_STEP_REQUIRED. The skill must flag multiple CRITICAL
gaps and produce specific remediation:
1. No DLQ on EventBridge target — a Lambda cold-start failure or SNS
   throttle silently drops the Health event (missed outage risk).
2. DR trigger ungated — any single-host degradation event (e.g.,
   AWS_EC2_INSTANCE_DEGRADATION for one i-0abc) triggers full regional
   failover. Must add ImpactChoice state in Step Functions that
   evaluates event code + entity count threshold.
3. No affected-entity enrichment — Slack messages lack specific resource
   IDs. Must add describe-affected-entities Lambda before notify.
4. No idempotency — duplicate Jira tickets on event updates. Must dedup
   on eventArn via Jira label.
5. No replay test — responder chain is untested.
