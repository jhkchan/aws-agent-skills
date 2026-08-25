# Advanced Patterns — AWS Health Event Auditor

Edge-case catalogs and expert-knowledge deep dives, moved verbatim from SKILL.md. Load on demand.

## Expert edge cases — non-obvious AWS Health behaviours (moved from SKILL.md)

- **`eventScopeCode` governs visibility, not severity.** `PUBLIC` events
  appear in the public AWS Health Dashboard (region-wide outages). They
  do not require an account-level audit — they affect everyone. An
  account-scope audit that flags a `PUBLIC` event as UNRESOLVED_EVENT is
  double-counting: the event is real, but the action is "monitor AWS's
  regional recovery," not "remediate your resource." Treat `PUBLIC`
  events as informational FINDINGS; only `ACCOUNT_SPECIFIC` events
  require per-resource remediation.

- **`describe-entity-aggregates` returns counts, not resources.** The
  org-view API `aws health describe-entity-aggregates --event-arns <arn>`
  returns `{eventId, eventArn, entityArn, entityValue, statusCode,
  awsAccountId}` per entity but does NOT include the underlying resource
  ARN or tags. For remediation, you must cross-reference the
  `entityValue` (e.g., an instance ID) against the resource in the
  member account. Confusing the aggregate entity ARN for a resource ARN
  breaks downstream automation.

- **The Health API throttles at ~1 request/second per account.** Bulk
  enumeration across many member accounts needs exponential backoff
  (`--max-attempts` and a jittered retry loop). Without throttling,
  `describe-affected-entities` returns `ThrottlingException` on large
  events. The throttle is per-account, not per-event — a 5000-entity
  event paginated in serial will throttle.

- **`eventDescription` is a list, not a string.** `describe-events`
  returns `eventDescription: [{language: "en_US", latestDescription:
  "..."}, ...]`. Iterating past the first element silently picks a
  non-English description. Always filter for `language: "en_US"` (or the
  operator's preferred locale). The description text often contains the
  prescribed action for scheduled changes — losing it via wrong-language
  iteration means emitting a SCHEDULED_CHANGE verdict with no action
  verb.

- **`startTime` for scheduled changes is the deadline, not the issue
  time.** Confusing `startTime` (deadline for scheduledChange, issue
  onset for issue events) with `lastUpdatedTime` (when AWS last touched
  the record) is the most common scheduling error. A scheduled change
  with `startTime` in the past and `eventStatus: upcoming` is rare but
  possible (AWS extending a window without updating status) — flag as
  DEADLINE_OVERDUE and treat as UNRESOLVED_EVENT-equivalent urgency.

- **`eventStatus: upcoming` only applies to scheduled changes.**
  `accountNotification` and `issue` events transition `open` → `closed`
  directly. If an input shows `eventStatus: upcoming` with
  `eventTypeCategory: issue`, the data is malformed — emit ERROR.

- **Health Organizational View is independent of AWS Organizations
  "all features."** An org in "consolidated billing only" mode can still
  enable Health org view — the feature does not require the full
  organization feature set. Treating "org features not enabled" as
  blocking Health org view is a false-CONFIG_GAP.

- **EventBridge rule patterns must match `source`, not just
  `detail-type`.** A rule filtering only on
  `detail-type: ["AWS Health Event"]` works but is brittle — AWS could
  rename detail-types (the v1 → v2 Health event schema renamed several).
  Filtering on `"source": ["aws.health"]` is the durable pattern.
  Composite rules (source + detail-type + detail.eventTypeCategory) are
  the most selective and the most resilient.

- **`affectedAccountName` is only populated in org-view events.** In a
  single-account event, the field is absent. Treating absence of
  `affectedAccountName` as "no affected accounts" is a false-OK — the
  account is implicit in the event ARN's account segment.

- **Multi-account events have a single org-view event ARN.** The same
  underlying incident surfaces as ONE event with multiple affected
  entities across accounts when org view is enabled, but as SEPARATE
  event ARNs (one per account) when each account is audited individually.
  De-duplicate cross-account findings by `eventTypeCode` + window, not
  by eventArn.

- **`describe-event-types` catalog is not exhaustive.** New event types
  appear before the catalog is updated. An unknown `eventTypeCode` is
  not an error — classify by `eventTypeCategory` and `eventStatus`,
  which are always present. Treat catalog absence as informational.

- **Health API is read-only and idempotent.** No Health API call modifies
  state — remediation commands are always against the affected resource's
  own service (EC2, RDS, Lambda). The `aws health` namespace has no
  `close-event` or `acknowledge-event`; closure is AWS-side and
  automatic when the underlying incident resolves.

- **Default rule name `default-rule-Health-<random>`** is created once
  per account around the time of first Health event delivery. If an
  account has never had a Health event, the rule may not exist yet —
  this is NOT a CONFIG_GAP on its own (it is AWS's lazy initialisation).
  The CONFIG_GAP is when Health events have occurred and no rule exists
  to consume them. Distinguish "no rule yet because no events" from
  "no rule while events exist."

- **Closed events are retained for ~90 days** in the Health API. Beyond
  that they age out and `describe-events` no longer returns them.
  Forensic audits older than 90 days must use CloudTrail (management
  events for `health:Describe*` calls) or the AWS Health Dashboard
  historical view.

## Deep reference: AWS Health internals (moved from SKILL.md) — API surface, event lifecycle, schema versions, EventBridge delivery, pagination/throttling, support-tier matrix

### Health API surface

The Health API (`health.amazonaws.com`, service prefix `health`) is
global — all calls go to `us-east-1` regardless of resource region.
The core audit surface:

- `describe-events` — list events by filter (eventStatusCodes,
  eventTypeCategories, services, regions, lastUpdatedTime ranges).
  Returns event metadata only, not affected entities.
- `describe-affected-entities` — list entities (resources) impacted by
  a specific event, with per-entity `statusCode`. Paginated at 100/page.
- `describe-entity-aggregates` — org-view aggregate counts per event
  per account. Does NOT return resource ARNs or tags.
- `describe-event-types` — catalog of all known event type codes. May
  lag behind newly introduced events.
- `describe-health-service-status-for-organization` — returns
  `healthServiceAccessStatusForOrganization` (enabled / disabled /
  pending). The authoritative org-view check.

### Event lifecycle

An event progresses through a fixed lifecycle by `eventTypeCategory`:

- `issue`: `open` → `closed`. AWS opens on incident detection, closes
  on resolution. Affected entities may transition
  `UNIMPAIRED → IMPAIRED → RESOLVED` independently.
- `scheduledChange`: `upcoming` → `closed`. AWS opens on schedule
  announcement, closes after the change window passes. Entities
  typically stay `UNIMPAIRED` until the action window, then transition
  based on operator action.
- `accountNotification`: no status transition — purely informational.
  Always treat as OK unless the notice text prescribes an action.

### Health event schema versions

AWS Health event JSON has two coexisting schema versions (v1 and v2)
delivered to EventBridge. v2 adds `eventArn` structural metadata and
renames several detail fields. EventBridge rules that filter on v1
field paths may silently miss v2 events. Filter on `source` to be
version-resilient.

### EventBridge delivery

Health events are delivered to the **default event bus** in each
affected account (and each member account with org view enabled). The
delivery requires:

1. The default event bus exists (it always does in modern accounts).
2. The bus policy authorises `health.amazonaws.com` to call
   `events:PutEvents`. AWS auto-adds this statement when org view is
   enabled; without org view, the statement may be absent for member
   accounts — verify per account.
3. At least one rule on the default bus matches the event (typically
   `source: ["aws.health"]`). Without a matching rule, the event is
   delivered to the bus and immediately dropped (no rule consumes it).

### Pagination and throttle limits

- `describe-events`: 10-100 results per page (default 10), `nextToken`
  pagination.
- `describe-affected-entities`: 100 per page max.
- `describe-entity-aggregates`: returns up to 100 aggregates per call.
- Throttle: ~1 request/second per account. Bulk enumeration across
  many events or accounts needs exponential backoff with jitter.

### Support tier matrix

| Tier | Health API access | Health Dashboard | EventBridge delivery |
|---|---|---|---|
| Basic | No (`SubscriptionRequiredException`) | Read-only (limited) | Yes |
| Developer | No (`SubscriptionRequiredException`) | Read-only (limited) | Yes |
| Enterprise On-Ramp | Yes | Full | Yes |
| Business | Yes | Full | Yes |
| Enterprise | Yes | Full + org view | Yes |

A Basic/Developer account still receives EventBridge Health events —
the API gating is for direct programmatic audit, not delivery.
EventBridge-driven automations work even on Basic-tier accounts.

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Health Dashboard refresh (2024-2025):** The AWS Health Dashboard was redesigned with a unified view for account and organizational events. The organizational view is now enabled by default for management accounts. Auditors should verify that the org-level Health Dashboard is accessible to security/ops teams.
- **Health Aware notifications (2024):** Enhanced EventBridge integration for Health events with more detailed event metadata. Auditors should verify that EventBridge rules for `aws.health` events are configured for critical event categories (issue, scheduledChange).
- **RCA (Root Cause Analysis) events (2024):** AWS Health now publishes RCA summaries for resolved incidents. No new audit-surface fields, but auditors should verify that RCAs are reviewed and tracked.

