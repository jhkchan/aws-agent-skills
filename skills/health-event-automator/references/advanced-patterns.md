# Advanced Patterns — Health Event Automator

Expert heuristics, edge-case catalogs, and recent-feature notes, moved verbatim from SKILL.md. Load on demand.

## Expert heuristic callouts (moved from SKILL.md)

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

## Edge-case handling (moved from SKILL.md)

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

## Recent AWS features (2024-2026) (moved from SKILL.md)

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

