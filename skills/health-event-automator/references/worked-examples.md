# Worked Examples — Health Event Automator

Secondary worked examples, moved verbatim from SKILL.md. Load on demand.

## Worked example — MANUAL_STEP_REQUIRED (no org view, no DLQ) (moved from SKILL.md)

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

