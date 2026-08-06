---
name: health-event-auditor
description: >-
  Audits AWS Health for active (open) issue events, upcoming scheduled
  changes, affected-resource entity status, closed-event resolution, Health
  Dashboard organization-view enablement, and EventBridge aws.health
  integration. Emits a deterministic verdict (UNRESOLVED_EVENT |
  SCHEDULED_CHANGE | CONFIG_GAP | OK) per event or per account/org scope
  with enumerated findings and specific CLI remediation. Use when reviewing
  AWS Health events, validating Health Organizational View coverage,
  diagnosing affected-resource entity status, checking scheduled-change
  deadlines, auditing EventBridge Health-event wiring, or assessing overall
  Health posture before an operational review or incident triage.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline event-document classification.
  Live-account audits use aws health describe-events, describe-affected-
  entities, describe-entity-aggregates, describe-health-service-status-for-
  organization, and aws events list-rules (AWS CLI v2, SSO or key-based
  credentials, Business/Enterprise/Enterprise On-Ramp support required for
  the Health API itself).
keywords:
  - AWS Health
  - Health Dashboard
  - Health API
  - Personal Health Dashboard
  - scheduled change
  - account event
  - ongoing event
  - affected entities
  - entity status
  - IMPAIRED
  - UNIMPAIRED
  - RESOLVED
  - open event
  - upcoming event
  - closed event
  - eventTypeCategory
  - scheduledChange
  - accountNotification
  - issue
  - AWS_EC2_INSTANCE_RETIREMENT_SCHEDULED
  - retirement scheduled
  - degraded performance
  - operational event
  - EventBridge
  - aws.health
  - default-rule-Health
  - Organizational View
  - healthServiceAccessStatusForOrganization
  - delegated administrator
  - Business Support
  - Enterprise Support
  - Basic Support
  - SubscriptionRequiredException
  - Health event audit
  - operational readiness
tags: [aws-health, health-dashboard, eventbridge, management, governance, audit, incident, scheduled-change, organizational-view]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Management
  verdict_shape: "UNRESOLVED_EVENT | SCHEDULED_CHANGE | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing AWS Health events before an operational review or incident
    triage, validating Health Organizational View coverage, diagnosing
    affected-entity statusCode (IMPAIRED/RESOLVED), checking scheduled-change
    deadlines, auditing EventBridge aws.health rule wiring, or assessing
    overall Health posture across an account or organization.
  activation_triggers:
    - "audit AWS Health events"
    - "check Health Dashboard"
    - "ongoing Health events"
    - "scheduled change deadline"
    - "EC2 instance retirement"
    - "affected entities impaired"
    - "is Health Organizational View enabled"
    - "EventBridge aws.health rule"
    - "Personal Health Dashboard"
    - "AWS Health posture"
  invocation_schema: >-
    Input: either (a) one or more AWS Health event records (JSON or text,
    including eventArn, eventTypeCategory, eventStatus, service,
    eventTypeCode, startTime, lastUpdatedTime, eventScopeCode, and the
    affected-entity list with statusCode), optionally paired with account
    posture (support tier, Health Org View status, EventBridge rule
    inventory), OR (b) a request to audit live Health posture (the auditor
    invokes aws health describe-events and the supporting API surface).
    Output: deterministic EVENT/VERDICT/REASON/FINDINGS/REMEDIATION block
    per event (or per account/org scope for CONFIG_GAP), where VERDICT is in
    {UNRESOLVED_EVENT, SCHEDULED_CHANGE, CONFIG_GAP, OK}.
---

# AWS Health Event Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across
all dimensions, and three AWS Health behaviours are easy to misjudge —
entity-level status diverges from event-level status (an `open` event can
hide `RESOLVED` entities and vice versa), `eventTypeCategory` drives
classification (`issue` vs `scheduledChange` vs `accountNotification`),
and Health API access is gated by **support tier** in a way nothing else
in AWS is.

AWS Health is the canonical source for operational events that affect
*your* resources specifically — region-wide outages are public, but the
event that says "host underlying instance i-abc123 will be retired on
Thursday" is account-scoped. The audit goal is to convert a list of
Health events into a deterministic action signal:

- An **open `issue`** with any `IMPAIRED` entity is **UNRESOLVED_EVENT**
  — the system is still being impacted. The work is not done until the
  last entity reports `RESOLVED`.
- An **upcoming `scheduledChange`** is **SCHEDULED_CHANGE** — a deadline
  exists and an action (stop/start, patch, reboot, drain) is required
  before it. `lastUpdatedTime` is when AWS last touched the record, not
  the deadline — `startTime` IS the deadline for scheduled changes.
- A missing **Health Organizational View** or a missing **EventBridge
  `aws.health` rule** is **CONFIG_GAP** — events may be arriving but
  nothing is consuming them, or you can only see one account out of N.

## Quick reference — severity thresholds

| Condition | Verdict | Step |
|---|---|---|
| `eventTypeCategory: issue` AND `eventStatus: open` AND any affected entity `statusCode: IMPAIRED` | **UNRESOLVED_EVENT** | Step 1 |
| `eventTypeCategory: issue` AND `eventStatus: open` AND any entity `statusCode: UNKNOWN` (status not yet reported) | **UNRESOLVED_EVENT** | Step 1 |
| `eventTypeCategory: scheduledChange` AND `eventStatus: upcoming` (deadline `startTime` in the future) | **SCHEDULED_CHANGE** | Step 2 |
| AWS Organization with >1 account AND `healthServiceAccessStatusForOrganization: disabled` | **CONFIG_GAP** | Step 3a |
| Zero EventBridge rules matching `Source: aws.health` on the default bus | **CONFIG_GAP** | Step 3b |
| `eventStatus: closed` AND all affected entities `statusCode: RESOLVED` (or `UNIMPAIRED`) | **OK** | Step 4 |
| No active (open/upcoming) events AND no config gaps | **OK** | Step 4 |
| Account support tier Basic/Developer (Health API not callable) | **CONFIG_GAP** | Step 0 |

Verdicts are mutually exclusive per audited scope: an event-level audit
emits one verdict per event; an account/org-scope audit emits one verdict
for the whole scope, aggregated worst (UNRESOLVED_EVENT > SCHEDULED_CHANGE
> CONFIG_GAP > OK).

## Pre-flight: account-posture gate (run before event classification)

Before classifying any event, classify the account posture. Several
factors **short-circuit** the audit — missing them produces false
"healthy" verdicts that hide the actual gap.

**Live-account pre-flight checks (skip for offline event-doc audit):**
1. Verify the caller's role has `health:DescribeEvents` and
   `health:DescribeAffectedEntities`. Most read-only auditor roles do;
   cross-account delegated-administrator roles frequently do NOT — verify
   the delegated admin was registered for `health.amazonaws.com` via
   `aws organizations list-delegated-administrators --service-principal
   health.amazonaws.com`. Surface a missing delegation BEFORE attempting
   org-wide enumeration.
2. All Health API calls go to **us-east-1**, regardless of where the
   affected resources live. The `region` field in the event describes the
   resource, not the API endpoint. A call to `aws health describe-events
   --region us-west-2` returns empty results, not an error — silently
   reporting "no events" when there are open events in other regions.
3. `aws health describe-health-service-status-for-organization` returns
   `healthServiceAccessStatusForOrganization`. The field reads `enabled`
   only AFTER the management account has called
   `enable-health-service-access-for-organization` at least once. A
   delegated administrator CANNOT enable org view — only the management
   account can. Treating "delegated admin configured" as equivalent to
   "org view enabled" is a false-OK.

| Posture attribute | Value | Effect on audit |
|---|---|---|
| Support plan | `Basic` / `Developer` | **Health API not callable.** `describe-events` returns `SubscriptionRequiredException`. The operator can still see Health events in the AWS Health Dashboard console (read-only), but no programmatic audit is possible. Output VERDICT: CONFIG_GAP with REMEDIATION "Upgrade to Business/Enterprise/Enterprise On-Ramp for Health API access, or audit manually via the Health Dashboard." Do NOT attempt to classify events from a Basic-tier account via API. |
| Support plan | `Business` / `Enterprise On-Ramp` / `Enterprise` | Health API is callable. Proceed. |
| AWS Organization | present (>1 account) | Org-view audit applies. Check `healthServiceAccessStatusForOrganization`. |
| AWS Organization | absent (standalone account) | Skip org-view check (Step 3a). Account-only audit. |
| `healthServiceAccessStatusForOrganization` | `enabled` | Org view is active — `describe-events` with `--aws-account-id` and `describe-entity-aggregates` work org-wide. |
| `healthServiceAccessStatusForOrganization` | `disabled` / `pending` / absent | Org view NOT active — you can only audit the calling account. Any account-scope audit of an org with >1 account is **CONFIG_GAP**. |
| EventBridge rules on default bus matching `Source: aws.health` | zero | **CONFIG_GAP** — events are delivered to the default event bus but no rule consumes them. Notifications silently dropped. |
| EventBridge rules matching `Source: aws.health` | one or more | Proceed — at least one rule exists. Verify it has an active target (Step 3b detail). |
| API region | not `us-east-1` | **Silent empty-result trap.** Re-run all Health API calls against us-east-1. |

**If the input is malformed** (not valid JSON, missing `eventArn`,
missing `eventTypeCategory` or `eventStatus`), output:

```text
EVENT: <eventArn or "unknown">
VERDICT: ERROR
REASON: Health event record is malformed — missing required fields
(eventTypeCategory / eventStatus). Cannot classify.
REMEDIATION: Re-fetch the canonical record with
`aws health describe-events --filter <criteria> --region us-east-1
--output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Account-posture gate (mandatory for any audit)

Apply the pre-flight gate. If the support tier is Basic/Developer, emit
**CONFIG_GAP** and stop — there is no programmatic audit surface. If the
API region is wrong, fail closed with an explicit note. If an
Organization is present and org view is `disabled`, emit **CONFIG_GAP**
(Step 3a) regardless of whether individual events are also flagged.

### Step 1: Open issue events with impaired entities — UNRESOLVED_EVENT

For each event with `eventTypeCategory: issue` AND `eventStatus: open`:

1. Fetch the affected entities (`aws health describe-affected-entities
   --filter eventArn=<arn>`). Page until `nextToken` is exhausted —
   `describe-affected-entities` caps at 100 per page and silently
   truncates. A region-wide event can have thousands of entities.
2. Inspect each entity's `statusCode`. The set is `IMPAIRED`,
   `UNIMPAIRED`, `RESOLVED`, `UNKNOWN` (legacy events may use
   `UNHEALTHY`/`HEALTHY` — treat `UNHEALTHY` as `IMPAIRED` and `HEALTHY`
   as `UNIMPAIRED`).
3. If ANY entity is `IMPAIRED` OR `UNKNOWN`, the event is
   **UNRESOLVED_EVENT**. The presence of `RESOLVED` entities does not
   cancel the impaired ones — the event cannot be OK until every entity
   reports `RESOLVED`/`UNIMPAIRED`.
4. If ALL entities are `RESOLVED` or `UNIMPAIRED` but `eventStatus` is
   still `open`, classify as **UNRESOLVED_EVENT** with REMEDIATION noting
   that AWS has not yet closed the event — escalate via Support if the
   entities are confirmed healthy.

**Expert note — entity vs event status divergence:** `eventStatus` is
the AWS-side aggregate, `statusCode` is the per-entity truth. AWS may
close an event (`eventStatus: closed`) while one entity is still
`IMPAIRED` (rare but happens during incident recovery). Conversely, an
`open` event with all `RESOLVED` entities is "waiting for AWS to close"
— still UNRESOLVED_EVENT but the action is "verify and request closure,"
not "fix the resource." The entity-level status is authoritative for
impact; the event-level status is authoritative for closure workflow.

### Step 2: Upcoming scheduled changes — SCHEDULED_CHANGE

For each event with `eventTypeCategory: scheduledChange` AND
`eventStatus: upcoming`:

1. Extract `startTime` — this IS the deadline. (Not `lastUpdatedTime`,
   which is when AWS last modified the record.) For
   `AWS_EC2_INSTANCE_RETIREMENT_SCHEDULED`, `startTime` is the start of
   the retirement window. For `AWS_LAMBDA_RUNTIME_DEPRECATION`, it is the
   deprecation date.
2. Compare deadline to current time. If deadline is within 7 days,
   severity escalation: append a **DEADLINE_URGENT** note to FINDINGS.
3. Identify the documented action. AWS Health scheduled-change events
   include an event description with the prescribed action (e.g., "stop
   and start the instance to migrate to a new host"). Surface the action
   verb in REMEDIATION — do not invent actions AWS has not documented.
4. Classify as **SCHEDULED_CHANGE**. The verdict is the same regardless
   of deadline urgency; urgency is a FINDINGS detail, not a separate
   verdict.

**Expert note — `upcoming` vs `closed` for scheduled changes:** a
scheduled change with `eventStatus: closed` has been applied by AWS
(instance retired, runtime deprecated). The window for proactive action
has passed. Classify such events via Step 4 (closed events) — typically
OK if the post-change state is healthy, but flag if the action was
forced and the resource is now in an unintended state.

### Step 3: Configuration gaps — CONFIG_GAP

Configuration gaps are account/org-scope findings, not event-scope. They
indicate the audit surface itself is broken: events exist but nothing
consumes them, or you can only see a slice of the surface.

#### Step 3a: Health Organizational View disabled

If the account is the management account of an AWS Organization with
more than one member account AND
`healthServiceAccessStatusForOrganization` is anything other than
`enabled` (commonly `disabled` or absent), emit **CONFIG_GAP**.

- The org view is enabled ONCE from the management account via
  `aws health enable-health-service-access-for-organization`. It is NOT
  a per-member toggle.
- A delegated administrator
  (`aws organizations register-delegated-administrator
  --service-principal health.amazonaws.com`) can READ org-wide events
  but CANNOT enable org view. The enable call must come from the
  management account. Treating delegated-admin setup as equivalent to
  org-view enablement is the most common false-OK.
- Until org view is enabled, the auditor must enumerate each member
  account individually (assuming the caller's role can assume into each)
  — at scale this is impractical and misses accounts. The gap is real.

#### Step 3b: Missing EventBridge aws.health rule

If the default event bus has zero rules whose `EventPattern` matches
`"source": ["aws.health"]` (case-sensitive — `"aws.health"` not
`"AWS.Health"`), emit **CONFIG_GAP**.

- AWS Health delivers events only to the **default event bus** in each
  account (and, with org view enabled, in each member account). Custom
  buses do not receive Health events.
- AWS auto-creates a default rule (`default-rule-Health-<random>`) in
  accounts created after ~2020. Older accounts may not have it. Do NOT
  assume its presence — verify with `aws events list-rules`.
- A rule without an active target is equivalent to no rule (events are
  matched and dropped). For each matching rule, also check
  `aws events list-targets-by-rule --rule <name>` — a rule with zero
  targets or all-disabled targets is a CONFIG_GAP.
- The `health.amazonaws.com` service principal must be authorized in
  the event bus policy (`aws events describe-event-bus --name default`)
  via a statement allowing `events:PutEvents`. AWS auto-creates this
  statement when org view is enabled; without org view, the statement
  may be absent and member-account events will be rejected.

### Step 4: Closed events and clean posture — OK

An event classifies as **OK** only when ALL of:

1. `eventStatus: closed` (the AWS-side lifecycle is complete).
2. Every affected entity has `statusCode: RESOLVED` or `UNIMPAIRED`.
3. There are no open sub-findings (e.g., the closed event is not a
   scheduled change that was force-applied after the deadline with an
   unintended post-state).

An account/org scope with **no** open `issue` events, **no** upcoming
`scheduledChange` events, org view enabled (where applicable), and at
least one EventBridge `aws.health` rule with an active target classifies
as **OK**.

**`accountNotification` events** (informational notices — billing,
maintenance announcements that are not resource-impacting) default to OK
unless they require action. Treat them as informational FINDINGS, not
verdict drivers, unless the notice explicitly states a required action.

### Step 5: Aggregation — worst finding wins

The final verdict is the **maximum severity** across all event-level
findings and scope-level config findings, where:

```
UNRESOLVED_EVENT > SCHEDULED_CHANGE > CONFIG_GAP > OK
```

Aggregation rules:

- An account-scope audit over many events takes the worst event verdict.
- A CONFIG_GAP from posture (Step 0 or Step 3) does NOT suppress an
  UNRESOLVED_EVENT — both are findings; the verdict is the worst, the
  FINDINGS list contains both.
- An OK closed event in the same scope as an UNRESOLVED_EVENT does not
  dilute the verdict — list the OK as a positive FINDING, but the scope
  verdict remains UNRESOLVED_EVENT.

## Output format (per event or per scope)

```text
EVENT: <eventArn, or "account: <id>" / "org: <id>" for scope audits>
VERDICT: UNRESOLVED_EVENT | SCHEDULED_CHANGE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
FINDINGS:
  - [UNRESOLVED_EVENT] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — open issue with mixed entity statuses

```text
EVENT: arn:aws:health:us-east-1::event/AWS_RDS/AWS_RDS_OPERATIONAL_EVENT/prod-incident
VERDICT: UNRESOLVED_EVENT
REASON: Open issue event with one of three affected entities still
IMPAIRED — the incident is partially recovered but not closed (Step 1).
FINDINGS:
  - [UNRESOLVED_EVENT] Entity db-prod-c is IMPAIRED while db-prod-a and
    db-prod-b are RESOLVED — partial recovery (Step 1)
  - [OK] Support tier is Enterprise — Health API is callable (Step 0)
  - [OK] Health Organizational View enabled and EventBridge aws.health
    rule present (Step 3)
REMEDIATION:
  1. Confirm db-prod-c recovery:
     aws health describe-affected-entities --filter eventArn=<arn>
     --region us-east-1
  2. If the entity is genuinely recovered but AWS has not closed the
     event, open a Support case referencing the eventArn.
  3. Do NOT treat the closed-entities as evidence of overall resolution;
     the event remains UNRESOLVED_EVENT until every entity is RESOLVED.
```

## Expert edge cases — non-obvious AWS Health behaviours

These patterns are easy to misjudge without operational Health
experience. Each changes a verdict if ignored.

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

## Anti-Patterns — NEVER

- NEVER classify an `open` issue event with an `IMPAIRED` entity as OK.
  The event-level status is the AWS-side lifecycle; the entity-level
  `statusCode` is the impact truth. An `open` event with one `IMPAIRED`
  entity is UNRESOLVED_EVENT regardless of how many entities are
  `RESOLVED`.

- NEVER treat `eventStatus: closed` as automatically OK. Verify every
  affected entity reports `RESOLVED` or `UNIMPAIRED`. AWS can close an
  event while a late entity is still `IMPAIRED` — the operational impact
  persists after the AWS-side closure.

- NEVER confuse `startTime` with the deadline for scheduled changes.
  `startTime` is the deadline for `scheduledChange`, the issue onset for
  `issue` events. Mixing these up produces either false-urgent
  ("deadline already passed" panic on an open issue) or false-complacent
  ("plenty of time" on a scheduled change that is actually overdue).

- NEVER call the Health API against any region other than us-east-1.
  `aws health describe-events --region us-west-2` returns an empty list,
  not an error — silently reporting "no events" when open events exist.
  The `region` field in the event describes the resource, not the API
  endpoint.

- NEVER assume Health API access from the support tier. Basic and
  Developer support plans cannot call the `health` API at all —
  `describe-events` raises `SubscriptionRequiredException`. The Health
  Dashboard is still console-accessible for these tiers, but no
  programmatic audit is possible. Always gate on support tier first.

- NEVER equate "delegated administrator configured" with "Health
  Organizational View enabled." A delegated admin can read org-wide
  events ONLY after the management account has called
  `enable-health-service-access-for-organization`. The delegation
  without the enablement produces empty org-wide results.

- NEVER assume the auto-created `default-rule-Health-...` EventBridge
  rule exists. Accounts created before ~2020 may not have it. Always
  verify with `aws events list-rules` — absence of any rule matching
  `aws.health` is CONFIG_GAP regardless of account age.

- NEVER filter EventBridge Health rules on `detail-type` alone. The
  durable filter is `source: ["aws.health"]`. Detail-type names have
  changed across Health event schema versions; source has not.

- NEVER treat `PUBLIC` events as account-level UNRESOLVED_EVENT. They
  are region-wide and surfaced in the public AWS Health Dashboard. List
  them as informational FINDINGS; reserve UNRESOLVED_EVENT for
  `ACCOUNT_SPECIFIC` events where the operator owns the affected
  resource.

- NEVER truncate `describe-affected-entities` pagination. The API caps
  at 100 per page. Large events (region-wide EC2 degradation) can have
  thousands of entities. Silently truncating at the first page misses
  affected resources and produces a false-OK when all 100 visible
  entities happen to be `RESOLVED` but the long tail contains
  `IMPAIRED`.

- NEVER report a closed scheduled change as actionable. A
  `scheduledChange` with `eventStatus: closed` has been applied — the
  window for proactive action is over. The post-change state may need
  verification (e.g., instance successfully migrated) but the verdict is
  driven by the post-state, not by the original change.

- NEVER attempt to close or acknowledge a Health event via the API.
  The Health API is strictly read-only. Closure is AWS-side and
  automatic. If an event should be closed but isn't, the action is to
  open a Support case, not to call a non-existent `health:CloseEvent`.

- NEVER invent remediation actions not documented in the event
  description. AWS Health scheduled-change events include a specific
  prescribed action (e.g., "stop and start the instance"). Recommending
  a different action (e.g., "reboot the instance" when AWS says
  "stop and start") can leave the underlying host in the same degraded
  state — reboot does not migrate hosts; stop/start does.

- NEVER classify an `accountNotification` as UNRESOLVED_EVENT unless it
  explicitly states a required action. Most notifications are
  informational (billing, planned maintenance that AWS handles). Reserve
  UNRESOLVED_EVENT and SCHEDULED_CHANGE for issue/scheduledChange
  categories respectively.

- NEVER treat the absence of `affectedAccountName` as "no affected
  accounts." The field is only populated in org-view events. In a
  single-account audit, the account is implicit in the event ARN.

- NEVER enable Health Organizational View from a delegated admin or
  member account. The call MUST originate from the Organizations
  management account. Emitting a remediation command targeted at the
  wrong account produces `AccessDeniedException` and erodes operator
  trust.

## Pre-flight safety checks (run before any remediation CLI)

- **Read-only Health API.** All `aws health *` calls are read-only and
  safe to execute without confirmation. The Health namespace has no
  mutating endpoints.
- **Mutating remediation runs against the affected resource's own
  service, not Health.** `aws ec2 stop-instances`, `aws rds reboot-db-
  instance`, etc. Before any mutating command, the auditor MUST emit:
  `CONFIRM: About to <action> on <resource-id> in account <account>
  region <region>. This is the prescribed action for Health event
  <eventArn>. Proceed? (yes/no)`. Do NOT execute until the operator
  confirms.
- **Snap-shot the event pre-remediation:**
  `aws health describe-affected-entities --filter eventArn=<arn>
  --region us-east-1 --output json > /tmp/<event-id>-pre-$(date +%s).json`
  This captures the affected-entity status before the action for
  post-remediation comparison.
- **Verify the prescribed action** by reading the `eventDescription`
  (`language: en_US`) BEFORE proposing a remediation command. The
  description contains AWS's documented action verb; deviating from it
  (e.g., reboot instead of stop/start) can leave the underlying state
  unchanged.
- **For scheduled changes with deadlines within 24 hours**, treat as
  incident-response — execute during the next maintenance window, not
  the next sprint. Force-applied scheduled changes after the deadline
  may produce unintended resource states (e.g., AWS retires the host
  under your instance, producing an unexpected stop).
- **Multi-account org-view remediation:** when an event affects
  resources in multiple member accounts, the remediation must be run
  per-account (assume the target account role, then run the resource's
  service command). The Health event is the SAME eventArn — do not
  re-fetch per account, but do execute remediation per account.
- **EventBridge bus-policy changes** (Step 3b remediation) are
  destructive at the policy level. Always append a statement rather
  than replacing the policy — `aws events put-permission --event-bus-name
  default --statement-id HealthAllow --action events:PutEvents
  --principal health.amazonaws.com`. Replacing the entire policy can
  revoke other service integrations.
- **Health Organizational View enablement** is one-way in practice:
  once enabled, disabling via
  `disable-health-service-access-for-organization` removes org-wide
  visibility immediately. Treat enablement as safe; treat disablement as
  high-risk and require explicit operator confirmation.

## Remediation guidance

**Remediation ordering principle:** always prefer AWS-documented actions
over inferred ones. The Health event description is authoritative for
prescribed actions; deviating from it (e.g., reboot vs stop/start) can
fail silently. For config gaps, prefer additive changes (add a rule,
add a bus-policy statement) over destructive ones (replace policy).

### For UNRESOLVED_EVENT — open issue with impaired entities

1. Verify the impaired entities are still impaired:
   `aws health describe-affected-entities --filter eventArn=<arn>
   --region us-east-1 --output json`
   Page via `--next-token` until exhausted.
2. For each `IMPAIRED` entity, apply the prescribed action from the
   event description. For EC2 degraded-performance, the typical action
   is stop/start:
   `aws ec2 stop-instances --instance-ids <id> --region <resource-region>`
   wait for `Stopped`, then
   `aws ec2 start-instances --instance-ids <id> --region <resource-region>`
3. Re-fetch the entity status after remediation. The status may take
   5-15 minutes to update from `IMPAIRED` to `RESOLVED`.
4. If all entities are `RESOLVED` but `eventStatus` is still `open`,
   open a Support case referencing the eventArn and the entity
   resolutions. Do NOT leave the event open — it pollutes future audits.

### For SCHEDULED_CHANGE — upcoming scheduled change

1. Identify the deadline (`startTime`) and the prescribed action from
   the event description.
2. Schedule the action during the operator's maintenance window,
   BEFORE the deadline. For EC2 instance retirement:
   `aws ec2 stop-instances --instance-ids <id>`
   `aws ec2 start-instances --instance-ids <id>`
   (Stop/start, not reboot — reboot does not migrate hosts.)
3. For multi-entity scheduled changes, batch the actions to minimize
   availability impact (e.g., cycle through an ASG rather than stop all
   instances at once).
4. After the deadline, the event transitions to `closed`. Verify the
   post-action state:
   `aws health describe-affected-entities --filter eventArn=<arn>`

### For CONFIG_GAP — org view disabled

1. From the Organizations MANAGEMENT account (not a delegated admin):
   `aws health enable-health-service-access-for-organization
   --region us-east-1`
2. Verify activation:
   `aws health describe-health-service-status-for-organization
   --region us-east-1`
   The `healthServiceAccessStatusForOrganization` field should read
   `enabled`.
3. Optionally register a delegated administrator for ongoing audits:
   `aws organizations register-delegated-administrator
   --account-id <security-tooling-account>
   --service-principal health.amazonaws.com`
4. Re-run the org-scope audit to enumerate events across all member
   accounts. Events that were previously invisible now surface.

### For CONFIG_GAP — missing EventBridge aws.health rule

1. Create the rule on the default event bus in EACH account (or use
   org-wide stacks via CloudFormation StackSets):
   `aws events put-rule --name HealthEventRouter --event-bus-name default
   --event-pattern '{"source":["aws.health"]}' --region us-east-1`
2. Add a target (SNS topic, Lambda, or Step Functions):
   `aws events put-targets --rule HealthEventRouter --event-bus-name
   default --targets file://targets.json --region us-east-1`
3. Verify the event bus policy allows `health.amazonaws.com` to put
   events:
   `aws events describe-event-bus --name default --region us-east-1`
   If no statement authorises `events:PutEvents` from
   `health.amazonaws.com`, add it:
   `aws events put-permission --event-bus-name default
   --statement-id HealthAllow --action events:PutEvents
   --principal health.amazonaws.com`
4. Test by emitting a mock event via `aws events put-events` (for the
   default bus) or wait for the next real Health event.

### For OK

1. No remediation required for the current posture.
2. Recommend verifying Health Organizational View status quarterly
   (the field can be inadvertently disabled by org-management changes).
3. Recommend reviewing the EventBridge aws.health rule set quarterly to
   catch target drift (Lambda deprecation, SNS topic deletion).
4. For closed events with active post-state verification (e.g., a
   migrated instance), confirm the resource is healthy in its own
   service console before considering the incident fully closed.

## Deep reference: AWS Health internals

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

## Recent AWS features (2024-2026)

- **Health Dashboard refresh (2024-2025):** The AWS Health Dashboard was redesigned with a unified view for account and organizational events. The organizational view is now enabled by default for management accounts. Auditors should verify that the org-level Health Dashboard is accessible to security/ops teams.
- **Health Aware notifications (2024):** Enhanced EventBridge integration for Health events with more detailed event metadata. Auditors should verify that EventBridge rules for `aws.health` events are configured for critical event categories (issue, scheduledChange).
- **RCA (Root Cause Analysis) events (2024):** AWS Health now publishes RCA summaries for resolved incidents. No new audit-surface fields, but auditors should verify that RCAs are reviewed and tracked.

## Domain

AWS CloudOps / AWS Health Operational Event Management.

## AWS documentation

- **AWS Health User Guide** — https://docs.aws.amazon.com/health/latest/ug/what-is-aws-health.html
- **AWS Health Security** — https://docs.aws.amazon.com/health/latest/ug/security.html
- **AWS Health API Reference** — https://docs.aws.amazon.com/health/latest/APIReference/
- **AWS Health CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/health/
- **Health Aware notifications** — https://aws.amazon.com/blogs/aws/build-aws-health-aware-custom-notifications-with-amazon-eventbridge-and-aws-lambda/
