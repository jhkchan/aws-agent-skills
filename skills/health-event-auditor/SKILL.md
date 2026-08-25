---
name: health-event-auditor
description: Audits AWS Health for active (open) issue events, upcoming scheduled changes, affected-resource entity status, closed-event resolution, Health Dashboard organization-view enablement, and EventBridge aws.health integration. Emits a deterministic verdict (UNRESOLVED_EVENT | SCHEDULED_CHANGE | CONFIG_GAP | OK) per event or per account/org scope with enumerated findings and specific CLI remediation. Use when reviewing AWS Health events, validating Health Organizational View coverage, diagnosing affected-resource entity status, checking scheduled-change deadlines, auditing EventBridge Health-event wiring, or assessing overall Health posture before an operational review or incident triage.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline event-document classification. Live-account audits use aws health describe-events, describe-affected- entities, describe-entity-aggregates, describe-health-service-status-for- organization, and aws events list-rules (AWS CLI v2, SSO or key-based credentials, Business/Enterprise/Enterprise On-Ramp support required for the Health API itself).
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  verdict_shape: UNRESOLVED_EVENT | SCHEDULED_CHANGE | CONFIG_GAP | OK
  when_to_use: Reviewing AWS Health events before an operational review or incident triage, validating Health Organizational View coverage, diagnosing affected-entity statusCode (IMPAIRED/RESOLVED), checking scheduled-change deadlines, auditing EventBridge aws.health rule wiring, or assessing overall Health posture across an account or organization.
  activation_triggers: audit AWS Health events, check Health Dashboard, ongoing Health events, scheduled change deadline, EC2 instance retirement, affected entities impaired, is Health Organizational View enabled, EventBridge aws.health rule, Personal Health Dashboard, AWS Health posture
  invocation_schema: 'Input: either (a) one or more AWS Health event records (JSON or text, including eventArn, eventTypeCategory, eventStatus, service, eventTypeCode, startTime, lastUpdatedTime, eventScopeCode, and the affected-entity list with statusCode), optionally paired with account posture (support tier, Health Org View status, EventBridge rule inventory), OR (b) a request to audit live Health posture (the auditor invokes aws health describe-events and the supporting API surface). Output: deterministic EVENT/VERDICT/REASON/FINDINGS/REMEDIATION block per event (or per account/org scope for CONFIG_GAP), where VERDICT is in {UNRESOLVED_EVENT, SCHEDULED_CHANGE, CONFIG_GAP, OK}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS Health, Health Dashboard, Health API, Personal Health Dashboard, scheduled change, account event, ongoing event, affected entities, entity status, IMPAIRED, UNIMPAIRED, RESOLVED, open event, upcoming event, closed event, eventTypeCategory, scheduledChange, accountNotification, issue, AWS_EC2_INSTANCE_RETIREMENT_SCHEDULED, retirement scheduled, degraded performance, operational event, EventBridge, aws.health, default-rule-Health, Organizational View, healthServiceAccessStatusForOrganization, delegated administrator, Business Support, Enterprise Support, Basic Support, SubscriptionRequiredException, Health event audit, operational readiness
  tags: aws-health, health-dashboard, eventbridge, management, governance, audit, incident, scheduled-change, organizational-view
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

Expert edge-case catalog moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Expert edge cases — non-obvious AWS Health behaviours

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

Per-verdict remediation command sequences moved to references.
→ [references/diagnostic-commands.md](references/diagnostic-commands.md) § Remediation guidance — per-verdict commands

## Deep reference: AWS Health internals

AWS Health internals deep reference moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Deep reference: AWS Health internals

## Recent AWS features (2024-2026)

2024-2026 feature notes moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Recent AWS features (2024-2026)

## References (load on demand)

Consult these only when the corresponding topic comes up:

- [references/advanced-patterns.md](references/advanced-patterns.md) — expert edge cases (non-obvious Health behaviours), the AWS Health internals deep reference (API surface, event lifecycle, schema versions, EventBridge delivery, pagination/throttling, support-tier matrix), and recent AWS features
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — per-verdict remediation command sequences (moved from § Remediation guidance)
## Domain

AWS CloudOps / AWS Health Operational Event Management.

## AWS documentation

- **AWS Health User Guide** — https://docs.aws.amazon.com/health/latest/ug/what-is-aws-health.html
- **AWS Health Security** — https://docs.aws.amazon.com/health/latest/ug/security.html
- **AWS Health API Reference** — https://docs.aws.amazon.com/health/latest/APIReference/
- **AWS Health CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/health/
- **Health Aware notifications** — https://aws.amazon.com/blogs/aws/build-aws-health-aware-custom-notifications-with-amazon-eventbridge-and-aws-lambda/
