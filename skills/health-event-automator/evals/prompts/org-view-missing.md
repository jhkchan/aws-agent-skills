# Eval prompt: org-view-missing

Validate this existing AWS Health automation posture for our 50-account
org. Emit the standard Health block (EVENT_TYPES, AFFECTED_ENTITIES,
RESPONDERS, ORG_VIEW, SCHEDULED_CHANGES, VERIFICATION, VERDICT,
FINDINGS, REMEDIATION).

Current state:
- 50 member accounts in AWS Organizations
- Management account has NOT run
  enable-health-service-access-for-organization
- No delegated administrator for health.amazonaws.com
- Per-account EventBridge rules deployed in only 5 of 50 accounts
  (manual CloudFormation deployment, no org-level rollout)
- The 5 covered accounts have:
  - Rules for issue / EC2 / us-east-1
  - DLQ configured
  - Affected-entity enrichment Lambda deployed
  - Slack notify via Lambda webhook
  - Jira create with eventArn dedup
- 45 accounts have NO Health event coverage at all — no EventBridge
  rules, no responders
- No scheduledChange automation anywhere
- No synthetic event replay test in any account
- No Health API poller fallback

Expected: MANUAL_STEP_REQUIRED. The skill must flag:
1. Org view not enabled — 45 of 50 accounts have zero Health coverage.
   A region-wide EC2 issue in any of the 45 uncovered accounts would
   not trigger any responder.
2. No delegated administrator — central visibility across the org is
   impossible. Must run enable-health-service-access-for-organization
   from the management account and register a delegated admin.
3. Recommend enabling org view + delegating admin to centralize via a
   single org-level rule in the delegated admin's default bus.
4. scheduledChange automation is missing entirely — instance retirement
   events will cause surprise outages when AWS retires the host.
