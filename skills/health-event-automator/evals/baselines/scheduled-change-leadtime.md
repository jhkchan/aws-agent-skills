# Baseline (no-skill) response: scheduled-change-leadtime

This file captures what a generic assistant produces WITHOUT the
health-event-automator skill loaded.

---

To automate scheduled change responses for EC2 instance retirement and
RDS maintenance, you can use EventBridge Scheduler to schedule a Lambda
function that runs 7 days before the scheduled end time. The Lambda
would replace the retired instance by launching a new one from your
launch template.

For RDS maintenance, schedule the action 1 day before so you can verify
the standby is current and plan a failover window if needed.

Make sure your Lambda has the right IAM permissions to call EC2 and RDS
APIs.

---

Notes on what the baseline misses:

- No mention of re-fetching the event before firing the lead-time action
  (scheduledEndTime shifts — the cached deadline may be stale by days).
- No DLQ on the EventBridge target (silent drop on cold-start).
- No affected-entity enrichment step.
- No idempotency (same eventArn could fire duplicate actions).
- No org-view setup for the 10-account org.
- No distinction between EC2 retirement (7 days) and RDS maintenance
  (1 day) — treats them as the same lead time.
