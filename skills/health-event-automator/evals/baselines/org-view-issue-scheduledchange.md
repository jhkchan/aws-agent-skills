# Baseline (no-skill) response: org-view-issue-scheduledchange

This file captures what a generic assistant produces WITHOUT the
health-event-automator skill loaded.

---

To set up AWS Health event automation for your 25-account org, you'll
want to use AWS Organizations to enable organizational view, then set up
EventBridge rules in your delegated admin account to catch Health events
across all member accounts.

For issue events on EC2 and RDS, route them to SNS and have a Lambda
function send Slack notifications and create Jira tickets. If the issue
is severe, trigger your DR failover Step Functions state machine.

For scheduledChange events, you can use EventBridge Scheduler to
schedule lead-time actions 7 days before the scheduled end time, so you
can replace retired instances before AWS retires them.

For accountNotification events about exposed credentials, deactivate the
exposed access key and create a new one.

Make sure to test the responder chain by sending a synthetic event.

---

Notes on what the baseline misses:

- No mention of enable-health-service-access-for-organization being run
  from the management account first (delegated admin alone is not enough).
- No DLQ on EventBridge targets (silent event drop risk on cold-start).
- DR failover trigger is not gated behind an impact evaluation — any
  issue event would trigger failover.
- No affected-entity enrichment step (Slack messages lack instance IDs).
- No idempotency mechanism (duplicate Jira tickets on event updates).
- No poller fallback for tier-0 workloads (EventBridge lag risk).
- No scheduledEndTime re-fetch (AWS sometimes extends windows).
