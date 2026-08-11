# EventBridge Health Event Patterns — Reference

This reference catalogs the EventBridge event patterns for each AWS Health
event category, common service filters, and the responder chain each
pattern should route to. Use alongside the Health Event Automator SKILL.md.

## Anatomy of a Health event

Every AWS Health event on EventBridge has the same envelope:

```json
{
  "version": "0",
  "id": "12345678-1234-1234-1234-123456789012",
  "detail-type": "AWS Health Event",
  "source": "aws.health",
  "account": "111111111111",
  "time": "2026-08-10T12:34:56Z",
  "region": "us-east-1",
  "resources": [],
  "detail": {
    "eventArn": "arn:aws:health:us-east-1::event/EC2/AWS_EC2_INSTANCE_DEGRADATION/abc123",
    "service": "EC2",
    "eventTypeCode": "AWS_EC2_INSTANCE_DEGRADATION",
    "eventTypeCategory": "issue",
    "eventScopeCode": "PUBLIC",
    "statusCode": "open",
    "startTime": "2026-08-10T12:30:00Z",
    "endTime": null,
    "lastUpdatedTime": "2026-08-10T12:32:00Z",
    "eventDescription": [{"language": "en_US", "latestDescription": "..."}],
    "affectedEntities": []
  }
}
```

**Key fields for routing:**
- `detail.eventTypeCategory` — issue | accountNotification | scheduledChange
- `detail.service` — EC2, RDS, S3, etc.
- `detail.eventTypeCode` — stable code (e.g., `AWS_EC2_INSTANCE_DEGRADATION`)
- `detail.statusCode` — open | upcoming | closed
- `region` — region of the affected resource (not where the rule is deployed)
- `account` — the account the event applies to

## Pattern 1 — All issue events (single account, single region)

```json
{
  "source": ["aws.health"],
  "detail": {"eventTypeCategory": ["issue"]}
}
```

Deploy this rule in each region of interest. Target: SNS topic with Lambda
responder for enrichment + notify.

## Pattern 2 — Issue events filtered by service

```json
{
  "source": ["aws.health"],
  "detail": {
    "eventTypeCategory": ["issue"],
    "service": ["EC2", "RDS", "S3", "LAMBDA"]
  }
}
```

Use when only certain services are operationally critical. Avoid `["*"]`
(over-broad) — explicitly list services.

## Pattern 3 — Specific event type codes

```json
{
  "source": ["aws.health"],
  "detail": {
    "eventTypeCategory": ["scheduledChange"],
    "eventTypeCode": [
      "AWS_EC2_INSTANCE_RETIREMENT_SCHEDULED",
      "AWS_RDS_MAINTENANCE_SCHEDULED"
    ]
  }
}
```

Use when building per-code lead-time actions (different lead time for
retirement vs maintenance).

## Pattern 4 — Account notifications (urgent subset)

```json
{
  "source": ["aws.health"],
  "detail": {
    "eventTypeCategory": ["accountNotification"],
    "eventTypeCode": [
      "AWS_ACCOUNT_NOTIFICATION_CREDENTIAL_EXPOSED",
      "AWS_ACCOUNT_NOTIFICATION_ABUSE",
      "AWS_BILLING_SUSPENSION"
    ]
  }
}
```

These are urgent — page security / finance owner immediately, not via the
general notify responder.

## Pattern 5 — Org-wide events (delegated admin)

In the delegated admin account:

```json
{
  "source": ["aws.health"]
}
```

A catch-all rule with the org-view event stream delivers events from all
member accounts. Filter further by `awsAccountId` in `detail` if needed.

## Pattern 6 — Cross-region aggregation

In each region, deploy a rule forwarding to a central bus:

```bash
aws events put-rule --name health-forward-to-central \
  --event-pattern '{"source": ["aws.health"]}' --state ENABLED

aws events put-targets --rule health-forward-to-central \
  --targets '[{"Id":"CentralBus","Arn":"arn:aws:events:us-east-1:111111111111:event-bus/central-health","RoleArn":"arn:aws:iam::111111111111:role/EventBridgeForwardRole"}]'
```

This centralizes Health events in one account / region for unified alerting.

## Responder chain per category

| Category | Default lead-time | Default responder chain |
|---|---|---|
| issue (region outage) | Immediate | Enrich → ImpactChoice → DR trigger → notify stakeholders |
| issue (single-resource) | Immediate | Enrich → ImpactChoice → scale-out / replace → notify team channel |
| accountNotification (credential) | Immediate | Page security → deactivate key → notify owner |
| accountNotification (billing) | Same day | Notify finance owner |
| scheduledChange (retirement) | 7 days before | Schedule replacement via EventBridge Scheduler |

## Verifying event delivery

After deploying a rule, verify with the synthetic replay API:

```bash
aws health describe-event-types \
  --filter 'eventTypeCategories=[issue]' \
  --query 'eventTypes[0].code' --output text
```

Then check CloudWatch metrics for the rule:

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name Invocations \
  --dimensions Name=RuleName,Value=health-issue-ec2-rds \
  --start-time 2026-08-09T00:00:00Z --end-time 2026-08-10T00:00:00Z \
  --period 3600 --statistics Sum
```

Zero invocations over a week may indicate the pattern is mis-scoped.

## Common pitfalls

- **`resources` array is empty for Health events.** The affected resources
  are not in the top-level `resources` field — they require a
  `describe-affected-entities` call. Filtering on `resources` returns nothing.
- **`eventDescription` is a list, not a string.** Read index 0's
  `latestDescription`. AWS appends updates over time.
- **The same eventArn can fire multiple times.** Each update to the event
  (status change, description refresh) emits a new EventBridge invocation.
  Responders must dedup on `eventArn` to avoid duplicate tickets.
- **Public events fire across all accounts.** A `PUBLIC` scope event
  (region-wide AWS issue) fires once per account — if you have 25 accounts
  in an org without org view, you get 25 duplicate alerts.
