---
name: cleanrooms-collaboration-auditor
description: >-
  Audits AWS Clean Rooms collaborations for membership-status gaps (INVITED
  or REMOVED members), privacy-budget risks (differential privacy disabled,
  epsilon spend exhausted, aggregate constraints missing), analysis-template
  SQL-validation defects (unresolved parameters, dangling table references),
  and configured-audience activation gaps (audience model untrained or
  stale). Emits a deterministic verdict (MEMBERSHIP_GAP | PRIVACY_RISK |
  CONFIG_GAP | OK) per collaboration with enumerated findings and specific
  CLI remediation. Use when reviewing Clean Rooms collaborations, checking
  member activation status, validating analysis templates, auditing the
  protected-query privacy budget, verifying configured-audience readiness,
  or hardening collaboration posture before production query traffic.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline config-doc classification.
  Live-account audits use aws cleanrooms get-collaboration,
  aws cleanrooms list-members, aws cleanrooms get-analysis-template,
  aws cleanrooms get-protected-query, aws cleanrooms list-configured-tables,
  aws cleanrooms get-membership, and aws cleanroomsml
  get-configured-audience-model (AWS CLI v2, SSO or key-based credentials).
keywords:
  - Clean Rooms
  - collaboration
  - membership status
  - differential privacy
  - epsilon budget
  - privacy budget
  - analysis template
  - SQL validation
  - protected query
  - aggregate constraints
  - configured audience
  - Clean Rooms ML
  - audience activation
  - INVITED member
  - REMOVED member
  - collaboration audit
  - data collaboration
  - privacy controls
  - cleanroomsml
  - join columns
  - configured table
tags: [cleanrooms, analytics, security, privacy, differential-privacy, collaboration, membership, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Analytics
  verdict_shape: "MEMBERSHIP_GAP | PRIVACY_RISK | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing a Clean Rooms collaboration before production query traffic,
    checking member activation status (INVITED vs ACTIVE vs REMOVED),
    validating differential-privacy budget posture (epsilon spend vs cap),
    auditing analysis-template SQL validity, auditing protected-query
    privacy controls, or validating configured-audience readiness for
    audience activation.
  activation_triggers:
    - "audit this Clean Rooms collaboration"
    - "check Clean Rooms member status"
    - "is differential privacy enabled"
    - "epsilon budget exhausted"
    - "validate analysis template SQL"
    - "is my audience model trained"
    - "Clean Rooms membership gap"
    - "configured audience ready"
    - "privacy budget audit"
    - "protected query failed"
    - "Clean Rooms collaboration posture"
  invocation_schema: >-
    Input: either (a) a Clean Rooms collaboration configuration snapshot
    (collaboration metadata + member list + analysis-template body +
    differential-privacy config + configured-audience state), OR (b) a
    collaboration ARN or ID for live-account audit. Output: deterministic
    COLLABORATION/VERDICT/REASON/FINDINGS/REMEDIATION block per
    collaboration, where VERDICT ∈ {MEMBERSHIP_GAP, PRIVACY_RISK,
    CONFIG_GAP, OK, ERROR}.
---

# Clean Rooms Collaboration Auditor

## Mindset

**One-line takeaway:** the verdict is the **worst** finding across four
orthogonal dimensions — **membership activation**, **privacy-budget
posture**, **analysis-template SQL validity**, and **configured-audience
readiness** — applied in the precedence
`MEMBERSHIP_GAP > PRIVACY_RISK > CONFIG_GAP > OK`.

Clean Rooms is a **multi-party collaboration** service, not a single-account
resource — every audit has at least two principals (the collaboration
creator and one or more members), and the caller's view of a member's
status is perspective-relative. Three structural facts drive the audit:

- **Membership activation gates every query.** A member in `INVITED` state
  has not accepted the collaboration — they cannot create analysis
  templates, run protected queries, or contribute their configured table.
  The collaboration looks healthy in `get-collaboration` but is
  operationally stalled until every intended member transitions to `ACTIVE`.
- **Differential privacy is a per-member, per-collaboration epsilon
  budget.** Epsilon does NOT renew automatically; it monotonically
  decreases as protected queries execute. A collaboration with epsilon
  spent is not "low risk" — it is **privacy-exhausted**, and any further
  queries run without DP noise would leak row-level signal.
- **Analysis templates are owned per-member, not per-collaboration.** The
  collaboration references them, but only the owning member can update the
  SQL. A template that references a configured-table alias the owner
  removed is a runtime defect that surfaces only at query time — there is
  no live SQL validator on the service side.

## Quick reference — verdict thresholds

| Condition | Verdict | Rule |
|---|---|---|
| Any intended member is in `INVITED` state | **MEMBERSHIP_GAP** | Rule M1 |
| Any previously-active member is in `REMOVED` state | **MEMBERSHIP_GAP** | Rule M2 |
| Member count < 2 (solo "collaboration") | **MEMBERSHIP_GAP** | Rule M3 |
| `differentialPrivacyConfig.enabled: false` or absent on protected queries | **PRIVACY_RISK** | Rule P1 |
| `epsilon` spend >= 80% of `epsilonBudget` cap | **PRIVACY_RISK** | Rule P2 |
| epsilon budget exhausted (no remaining spend allowed) | **PRIVACY_RISK** | Rule P2 |
| No `aggregateConstraints` (min/max) configured | **PRIVACY_RISK** | Rule P3 |
| Analysis-template SQL has unresolved `${param}` tokens | **CONFIG_GAP** | Rule A1 |
| Analysis-template SQL references a non-existent configured-table alias | **CONFIG_GAP** | Rule A2 |
| Configured audience activated but no `ConfiguredAudienceModel` in READY state | **CONFIG_GAP** | Rule C1 |
| Configured audience in CREATE_FAILED or training state | **CONFIG_GAP** | Rule C2 |
| No protected-query output configuration (S3 result receiver) | **CONFIG_GAP** | Rule Q1 |
| All members ACTIVE, DP enabled, epsilon healthy, templates valid, audience ready | **OK** | Step 6 |

See the ordered steps below for edge cases. Deep Clean Rooms internals
(epsilon budget math, configured-table join semantics, Clean Rooms ML
training pipeline) are in the [Deep reference](#deep-reference-clean-rooms-internals)
section at the end.

## Critical rules — read first (do NOT violate)

These are the high-frequency, high-impact mistakes. Each is expanded in
the NEVER list and Step 0 below — this block exists so an agent executing
under time pressure sees them before any classification logic:

1. **Any member in `INVITED` state is MEMBERSHIP_GAP — no exceptions.**
   The member has not accepted; the collaboration is operationally
   partial. Do not classify as OK regardless of how clean the privacy
   config looks.
2. **`differentialPrivacyConfig.enabled: true` is NOT proof that queries
   run with DP noise.** The collaboration flag is the capability gate;
   the per-query `additionalAnalyses` epsilon is the enforcement. A
   query with `additionalAnalyses: 0` runs without DP noise even on a
   DP-enabled collaboration. Always audit the most recent query's
   epsilon value.
3. **Epsilon does NOT reset at any calendar boundary.** It is a
   monotonic per-member budget for the collaboration's lifetime. Once
   exhausted, the only path is recreating the collaboration. Budget for
   the lifetime at creation — there is no "monthly refill."
4. **`queryLogStatus: DISABLED` is a CONFIG_GAP note, not a
   PRIVACY_RISK verdict.** Query logging is an operational/forensic
   dimension; it does not affect the privacy of protected queries.
   Further, enabling it post-hoc requires recreating the collaboration
   (one-way, set-at-creation flag).
5. **Aggregate constraints (MIN/MAX) are the structural privacy floor;
   DP is the noise layer on top.** A collaboration with DP enabled but
   no aggregate constraints can still return singleton rows when noise
   rounds a 1-row group up to threshold. Both layers must be present
   for defense in depth.
6. **The configured audience model lives in `cleanroomsml`, not
   `cleanrooms`.** A collaboration can reference a valid-looking ARN
   while the model is in `CREATE_FAILED`. Always fetch the model state
   from `cleanroomsml get-configured-audience-model` separately.
7. **Membership status is perspective-relative.** `ListMembers` returns
   the collaboration's view; `GetMembership` returns the caller's own
   view. A member can be ACTIVE from the creator's perspective but LEFT
   from their own. Cross-reference both views in multi-party audits.
8. **Never recommend deleting a collaboration as remediation without
   explaining the blast radius** — it removes ALL members, configured
   tables, analysis templates, and query history irreversibly. The
   correct fix for one misconfigured member is `DeleteMember`.

## Pre-flight: collaboration metadata gate (run before classification)

Before evaluating membership and privacy, classify the collaboration
itself. Several attributes **short-circuit** the audit — misclassifying
them produces false positives that erode trust.

**Multi-collaboration sweep note (pagination):** `aws cleanrooms
list-collaborations` returns at most 100 collaborations per page. Use
`--next-token` to drain every page; the long tail often contains stale
proof-of-concept collaborations that are the most likely to have INVITED
or REMOVED members. For each collaboration, also page
`aws cleanrooms list-members` and
`aws cleanrooms list-analysis-templates` — both cap at 100/page. Always
drain `nextToken` to completion.

**Live-account pre-flight checks (skip if doing offline config-doc audit):**
1. Verify the caller's identity can run
   `cleanrooms:GetMembership` and `cleanrooms:ListMembers` — most read-only
   auditor roles can list members but cannot see other members' epsilon
   spend without the `cleanrooms:GetMembership` permission. Surface this
   BEFORE the operator approves the audit.
2. Verify CloudTrail is logging `cleanrooms:StartProtectedQuery` and
   `cleanrooms:GetProtectedQuery` — these are the audit-grade events for
   privacy-budget spend forensics. Without them, you cannot reconstruct
   which member spent which epsilon slice.
3. Snapshot `aws cleanrooms list-members --collaboration-id <id>` (paged)
   BEFORE any recommendation — member status is mutable, and an INVITED
   member may transition to ACTIVE during the audit window.

| Attribute | Value | Effect on audit |
|---|---|---|
| `collaboration.status` | `ACTIVE` | Proceed with full audit. |
| `collaboration.status` | `PENDING` (not yet active) | Collaboration has been created but not activated — membership gate fires regardless. Skip privacy checks (no queries have run). |
| `collaboration.status` | `INACTIVE` | Collaboration has been deactivated — emit MEMBERSHIP_GAP regardless of member states; no protected queries can run. |
| `creatorDisplayName` | (set) | The creator is always the first member and is always ACTIVE after creation. The creator cannot be REMOVED without deleting the collaboration. |
| `member abilities` | no member with `CAN_QUERY` | No analysis path exists; even with full privacy controls, the collaboration is operationally inert. Emit MEMBERSHIP_GAP (no querier) unless audience-activation is the sole intent. |
| `queryLogStatus` | `ENABLED` | Excellent — query history is durable for forensics. Note in REMEDIATION. |
| `queryLogStatus` | `DISABLED` | No query history — forensics for epsilon-spend audits are unavailable. Note as operational risk; not a verdict driver on its own. |
| `collaboration.analyticsEngine` | `SPARK` | Spark-based collaborations have additional compute configuration (execution role, output S3). Audit the execution role separately as IAM. |
| `collaboration.analyticsEngine` | `CLEAN_ROOMS_SQL` | Standard SQL collaborations. The default. |

**If the collaboration config JSON is malformed** (invalid JSON, missing
`members`, missing `collaborationIdentifier`), output:

```text
COLLABORATION: <collaboration-id>
VERDICT: ERROR
REASON: Collaboration document is not valid JSON or is missing required
fields — cannot classify.
REMEDIATION: Retrieve the canonical config with
`aws cleanrooms get-collaboration --collaboration-id <id> --output json`
and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious Clean Rooms behaviors that change classification

These behaviors are easy to misjudge without operational Clean Rooms
experience. Each changes a verdict if ignored:

- **Membership status is perspective-relative.** `ListMembers` returns the
  collaboration's view of members; `GetMembership` returns the caller's
  view of their own membership. A collaboration can show a member as
  `ACTIVE` from the creator's perspective while the member sees their
  own status as `LEFT` (they self-removed). Always cross-reference both
  views in a multi-party audit; a member listed as ACTIVE who has LEFT is
  a silent MEMBERSHIP_GAP that surfaces only when their queries fail with
  `AccessDeniedException`.

- **Epsilon is per-member, not per-collaboration.** Each member who runs
  protected queries has their OWN epsilon budget contributed to the
  collaboration's total spend. A collaboration where one member has spent
  95% of their budget and another has spent 5% is NOT uniformly healthy —
  the high-spend member is the bottleneck. Report per-member epsilon
  posture, not just the collaboration aggregate.

- **`differentialPrivacyConfig.enabled: true` is not the same as "DP is
  applied."** Differential privacy in Clean Rooms is enforced via the
  `additionalAnalyses` field on each protected query, with the member's
  epsilon contribution specified. A collaboration with DP "enabled" but
  whose protected queries pass `additionalAnalyses: 0.0` (or omit it) is
  running WITHOUT DP noise. The config-level `enabled` flag is the
  capability gate; the per-query epsilon is the enforcement. Always audit
  the most recent protected query's `additionalAnalyses` value, not just
  the collaboration-level flag.

- **Aggregate constraints (MIN/MAX) apply to query OUTPUT rows, not input
  rows.** A constraint of `MIN=10` means the query result must contain at
  least 10 rows per group — it is a privacy check preventing singleton
  re-identification. A configured table with NO aggregate constraints
  means ANY query can return singleton rows — there is no privacy floor.
  Treat the absence of `aggregateConstraints` as a HIGH-severity privacy
  gap regardless of DP status.

- **Analysis templates are SQL-with-parameters, not free SQL.** The
  service validates the SQL at template-creation time against the
  configured tables, BUT it cannot validate runtime parameter values. A
  template with `${dt}` substituted by the caller with a literal that
  matches no rows is a silent query-no-op. Parameter type validation is
  the caller's responsibility — there is no server-side type check.

- **Configured tables are owned per-member and the alias is the join
  key.** The collaboration references configured tables by alias; the
  underlying Glue table can change ARN (account, database, name) without
  the alias changing. If a member removes their configured table but the
  template still references the alias, the next protected query fails
  with `ResourceNotFoundException` at runtime — there is no live validator
  that catches the dangling alias.

- **Configured audiences live in a different API service
  (`cleanroomsml`), not `cleanrooms`.** Audience activation is a
  collaboration-level toggle, but the trained audience model is a
  `cleanroomsml` resource. A collaboration with
  `configuredAudienceModelArn` set to an ARN in CREATE_IN_PROGRESS or
  CREATE_FAILED state will fail at audience-activation time with no
  collaboration-level warning. Always fetch the audience-model state from
  `cleanroomsml get-configured-audience-model` separately — the
  collaboration config shows only the ARN.

- **Protected queries return S3 result locations, not result rows.** The
  protected-query API returns a `outputConfiguration.S3.destination`
  prefix per member; the actual rows are written to S3 in Parquet. An
  audit that checks only the query status (`SUCCEEDED`) without
  verifying the S3 bucket policy on the destination is incomplete — a
  bucket that allows cross-account reads silently widens the audience
  for the (differentiated, noised) result set.

- **A member with status `COLLABORATION_TIME`** is not a real status —
  the canonical states are `INVITED`, `ACTIVE`, `REMOVED`, `LEFT`. Any
  other status string indicates either a stale snapshot or a private
  preview feature. Surface as ERROR rather than guessing semantics.

- **Privacy budget "spend" is reported via the `epsilon` field on the
  protected-query result, not as a counter on the membership.** To audit
  historical spend, page `ListProtectedQueries` and sum the epsilon
  contributions per member. There is no `GetPrivacyBudget` API — the
  budget is a configured cap, and consumption is the integral of query
  epsilons.

- **Clean Rooms is REGION-scoped.** A collaboration in `us-east-1` cannot
  include members whose membership is in `eu-west-1`. Cross-region
  membership is not supported. Verify that every member's account and
  region are aligned with the collaboration's region — a member ARN with
  the wrong region silently fails to activate.

- **`queryLogStatus` is a one-way flag.** Once enabled, it cannot be
  disabled. A collaboration with `queryLogStatus: DISABLED` is a signal
  that logging was never turned on (it is OFF by default at creation);
  the operator must delete and recreate the collaboration to enable it
  post-hoc. Treat as a CONFIG_GAP note, not a privacy verdict.

- **DP noise scales with aggregate SENSITIVITY, not result row count.**
  The noise added per output row is proportional to the sensitivity of
  the underlying column (a column with 2 distinct values has lower
  sensitivity than one with 1M distinct values). This means a query
  that groups by a high-cardinality column (e.g., user_id) receives
  MORE noise per group than one grouping by a low-cardinality column
  (e.g., country). The practical consequence: a template that groups
  by user_id produces noisier results than the epsilon value alone
  suggests — the effective privacy protection is HIGHER than the
  epsilon spend indicates. Do not flag a high-cardinality grouping as
  a privacy weakness; the noise model already compensates.

- **Configured table analysis rules are versioned but queries in
  flight are NOT retroactively re-evaluated.** When a member updates
  their configured table's analysis rule (e.g., tightening
  `aggregateConstraints` from MIN=5 to MIN=10), queries already in
  `RUNNING` state continue under the OLD rule. Only queries
  SUBMITTED after the update pick up the new constraint. This creates
  a race window during remediation: an audit that recommends tightening
  a rule should note that in-flight queries may still produce results
  compliant with the old (weaker) rule.

- **The `CreateMembership` API is idempotent only within the
  invitation window (7 days).** If the invitee does not call
  `CreateMembership` within 7 days of `CreateCollaboration` (or
  `CreateInvitation`), the invitation EXPIRES and the member status
  transitions from `INVITED` to a terminal state that requires the
  creator to re-issue a fresh invitation. A member stuck in INVITED
  for >7 days is not merely "pending" — the invitation has lapsed and
  the creator must re-invite. This is why Rule M1 fires regardless of
  how long the member has been INVITED; the operator either accepts
  or re-invites, there is no "wait longer" option.

### Step 1: Membership activation evaluation (MEMBERSHIP_GAP)

Membership is evaluated FIRST because no other dimension matters if the
collaboration cannot execute queries.

**Rule M1 — INVITED member.** Any member in `INVITED` state is
MEMBERSHIP_GAP. The member has been sent an invitation but has not yet
called `CreateMembership` to accept. The collaboration is operationally
partial: queries from ACTIVE members can run, but the INVITED member
cannot contribute their configured table, approve analysis templates, or
run their own protected queries.

**Rule M2 — REMOVED member.** A member in `REMOVED` state (the creator
revoked) or `LEFT` state (the member self-removed) is MEMBERSHIP_GAP.
The collaboration metadata still references their configured tables and
analysis templates, but the data is no longer queryable. A protected
query that joins on a now-removed member's table fails at runtime with
`ResourceNotFoundException`.

**Rule M3 — Solo "collaboration."** A collaboration with fewer than 2
members is not a collaboration — it is a single account talking to
itself. This configuration is operationally valid (the creator can run
queries against their own configured tables) but defeats the purpose of
Clean Rooms and is almost always a misconfiguration or a stale proof of
concept. Emit MEMBERSHIP_GAP.

**Rule M4 — No CAN_QUERY member.** Every member has an `abilities` list
that must include `CAN_QUERY` for at least one member. A collaboration
where no member has `CAN_QUERY` cannot run protected queries — the
collaboration is inert even if all members are ACTIVE. Emit
MEMBERSHIP_GAP unless audience activation is the sole configured use
case.

### Step 2: Privacy-budget posture (PRIVACY_RISK)

If all intended members are ACTIVE (Step 1 passes), evaluate the
privacy-budget posture.

**Rule P1 — Differential privacy disabled.** A collaboration where
`differentialPrivacyConfig` is absent, or where
`differentialPrivacyConfig.enabled: false`, is PRIVACY_RISK. Protected
queries run against raw rows with no DP noise — the only privacy control
is the aggregate constraint floor (Rule P3). For any collaboration
handling user-level data, this is a HIGH-severity finding.

**Rule P2 — Epsilon budget exhaustion.** The epsilon budget is the total
privacy "spend" the collaboration allows per member. If the
accumulated epsilon (summed across protected queries for a member) is:

- **>= 80% of cap** → **PRIVACY_RISK** (near-exhaustion). The 80%
  threshold is an expert batch-planning heuristic, not a service-level
  limit: a typical analysis workload submits 4-8 protected queries per
  sprint, each consuming 2-5% of the budget. At 80% spend, the
  remaining 20% is insufficient for one full sprint cycle — the
  collaboration will reject the next batch with
  `ServiceQuotaExceededException` partway through, leaving analysts
  with partial results. Treat 80% as the "plan migration" trigger, not
  a hard cutoff.
- **100% of cap (exhausted)** → **PRIVACY_RISK** (CRITICAL within the
  dimension). The service rejects further DP-protected queries. If
  queries are still succeeding at this spend level, they are running
  with `additionalAnalyses: 0` (DP bypassed) — flag as CRITICAL
  operational risk.

Compute spend per member by paging `ListProtectedQueries` and summing
the `epsilon` field from the `additionalAnalyses` of completed queries.
There is no `GetPrivacyBudget` API. Note: epsilon is charged at query
SUBMISSION time, not at result materialization — a query that runs for
10 minutes still consumes its epsilon slice up front, and a FAILED
 query that added noise before failing still spends its epsilon.

**Rule P3 — Aggregate constraints absent.** A configured table with no
`aggregateConstraints` (no MIN or MAX on output rows per group) is
PRIVACY_RISK. Without an aggregate floor, a query can return singleton
rows, enabling row-level re-identification regardless of DP status.
Aggregate constraints are the structural privacy floor; DP is the noise
layer on top.

**Rule P4 — Join columns missing from configured tables.** A configured
table without `joinColumns` configured cannot be joined in a protected
query — it can only be queried standalone. If the collaboration's
analysis templates assume a join, the queries will fail at runtime. This
is a CONFIG_GAP unless paired with explicit "no joins" use case.

### Step 3: Analysis-template SQL validity (CONFIG_GAP)

If membership and privacy posture pass, validate the analysis templates.

**Rule A1 — Unresolved parameters.** A template body containing
`${param}` tokens that are not declared in the template's `parameters`
block is CONFIG_GAP. The service validates parameter declarations at
creation, but a template can have orphaned tokens if it was edited
in-place (which is not supported — templates are immutable; you must
create a new version). If the input shows a template body with `${...}`
tokens that have no matching parameter declaration, emit CONFIG_GAP and
recommend recreating the template.

**Rule A2 — Dangling table references.** A template that references a
configured-table alias not present in the collaboration's
`configuredTables` list is CONFIG_GAP. This happens when a member
removes their configured table but their analysis template still
references the alias. The next protected query will fail at runtime with
`ResourceNotFoundException`.

**Rule A3 — SQL syntax not parseable.** If the template body is not
valid Athena/Presto SQL (unbalanced parentheses, missing SELECT,
unterminated string), emit CONFIG_GAP. The service validates at
creation, but a snapshot may show a pre-fix state or a manually-edited
template body in an offline audit.

**Rule A4 — Template references unavailable columns.** A template that
SELECTs columns not present in the configured table's `allowedColumns`
list is CONFIG_GAP. Configured tables expose only allow-listed columns
to the collaboration; selecting a column outside this list fails at
runtime with `ValidationException`.

### Step 4: Protected-query output configuration (CONFIG_GAP)

**Rule Q1 — No output receiver configured.** A protected query requires
an output configuration (typically an S3 bucket per member). If the
collaboration's most recent protected queries show
`outputConfiguration` is absent or the destination bucket does not
exist, emit CONFIG_GAP. The query will fail with `AccessDeniedException`
on the PutObject call.

**Rule Q2 — Stale S3 destination.** If the output S3 bucket policy was
widened to allow cross-account reads (e.g., for export to a downstream
analytics tool), the privacy-controlled result set is silently exposed
to a wider audience. Note as CONFIG_GAP with the recommendation to scope
the bucket policy to the collaboration's member accounts only.

### Step 5: Configured-audience readiness (CONFIG_GAP)

This step applies only to collaborations configured for audience
activation (the `cleanroomsml` integration). Skip if no
`configuredAudienceModelArn` is referenced.

**Rule C1 — Audience model not READY.** A collaboration with
`configuredAudienceModelArn` set but the referenced model is in any
state other than `READY` (e.g., `CREATE_IN_PROGRESS`, `CREATE_FAILED`,
`INACTIVE`) is CONFIG_GAP. Audience activation queries will fail. Always
fetch the model state from
`aws cleanroomsml get-configured-audience-model --configured-audience-model-arn <arn>`
separately — the collaboration config shows only the ARN.

**Rule C2 — Audience model stale.** A trained audience model has a
training data window. If the model's `trainingContainerExecutionStatus`
indicates the training data is older than the collaboration's refresh
cadence, audience activation produces stale predictions. Note as
CONFIG_GAP.

**Rule C3 — Audience activation without destination.** Audience
activation writes the predicted audience to an S3 bucket. If no
`destinationConfig` is set on the configured-audience model, activation
queries fail. Emit CONFIG_GAP.

### Step 6: Aggregation — worst finding wins by precedence

The final verdict is the **maximum severity** finding across all
dimensions, in the precedence:

```text
MEMBERSHIP_GAP > PRIVACY_RISK > CONFIG_GAP > OK
```

Membership takes precedence because a non-functional collaboration is
the worst operational state — no privacy or config dimension can be
exercised. Privacy takes precedence over config because a config gap
fails loudly (query returns an error), while a privacy gap fails
silently (queries succeed but leak signal).

If no findings fire (all members ACTIVE, DP enabled, epsilon healthy,
aggregate constraints set, templates valid, audience READY), the verdict
is **OK**.

## Output format (per collaboration)

```text
COLLABORATION: <collaboration-id or ARN>
VERDICT: MEMBERSHIP_GAP | PRIVACY_RISK | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its rule number>
FINDINGS:
  - [MEMBERSHIP_GAP] <finding description (Rule Mn)>
  - [PRIVACY_RISK] <finding description (Rule Pn)>
  - [CONFIG_GAP] <finding description (Rule An/Qn/Cn)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — collaboration with INVITED member and no DP

```text
COLLABORATION: arn:aws:cleanrooms:us-east-1:111111111111:collaboration/abc-123
VERDICT: MEMBERSHIP_GAP
REASON: Member 222222222222 is in INVITED state (Rule M1) — collaboration
is operationally partial. Differential privacy is also absent (Rule P1).
FINDINGS:
  - [MEMBERSHIP_GAP] Member 222222222222 in INVITED state (Rule M1) —
    cannot run protected queries or contribute configured table
  - [PRIVACY_RISK] differentialPrivacyConfig absent on collaboration
    (Rule P1) — protected queries run with no DP noise
  - [PRIVACY_RISK] Configured table cr-marketing-events has no
    aggregateConstraints (Rule P3) — singleton-row re-identification
    possible
  - [OK] All declared analysis templates have resolved parameters and
    valid table references
REMEDIATION:
  1. MEMBERSHIP_GAP — Have 222222222222 accept the invitation:
     aws cleanrooms create-membership --collaboration-arn <arn>
     --membership-display-name "222-analyst" --profile 222-profile.
     Or revoke: aws cleanrooms delete-membership --membership-identifier
     <membership-arn> if 222 is no longer intended.
  2. PRIVACY_RISK — Enable differential privacy:
     aws cleanrooms update-collaboration --collaboration-identifier
     <id> --differential-privacy-config enabled=true.
  3. PRIVACY_RISK — Add aggregate constraint MIN=10 on the configured
     table: aws cleanrooms update-configured-table-analysis-rule
     --configured-table-id cr-marketing-events ...
```

## Anti-Patterns — NEVER

- NEVER classify a collaboration with a member in `INVITED` state as
  `OK`. An INVITED member has not accepted the collaboration — they
  cannot query, contribute data, or activate audiences. The
  collaboration is operationally partial regardless of how clean the
  privacy config looks.

- NEVER treat `differentialPrivacyConfig.enabled: true` as proof that
  queries are running with DP noise. The collaboration-level flag is the
  CAPABILITY gate; the per-query `additionalAnalyses` epsilon value is
  the ENFORCEMENT. A query with `additionalAnalyses: 0` runs without DP
  noise even on a DP-enabled collaboration. Always audit the most recent
  protected query's epsilon contribution.

- NEVER report a collaboration as PRIVACY_RISK based solely on
  epsilon-spend percentage without naming the per-member spend. Epsilon
  is per-member — one member at 95% spend and another at 5% is not a
  uniform PRIVACY_RISK. The high-spend member is the bottleneck; report
  per-member, not aggregate.

- NEVER flag a `queryLogStatus: DISABLED` collaboration as PRIVACY_RISK.
  Query logging is an operational/forensic dimension — it does not affect
  the privacy of protected queries. Treat as a CONFIG_GAP note in the
  FINDINGS list (operator should enable for forensics), not as a
  verdict driver. Note that enabling queryLogStatus requires deleting and
  recreating the collaboration — it is a one-way, set-at-creation flag.

- NEVER classify a member with status string outside
  {INVITED, ACTIVE, REMOVED, LEFT} as a known state. The canonical
  Clean Rooms member statuses are these four. Any other value
  (e.g., `PENDING`, `COLLABORATION_TIME`) is either a stale snapshot,
  a private-preview feature, or a malformed input. Emit ERROR rather
  than guessing semantics — false-positive MEMBERSHIP_GAP erodes trust.

- NEVER assume a `SUCCEEDED` protected query means the result was
  consumed correctly. The query status reflects the service-side
  computation; the result rows are written to S3 in Parquet. A bucket
  policy that blocks the member's PutObject produces a separate failure
  mode that surfaces as `SUCCEEDED` query + empty S3 prefix. Always
  cross-reference the S3 destination.

- NEVER assume the configured audience model is `READY` because the
  collaboration's `configuredAudienceModelArn` is set. The ARN is a
  reference, not a state. Audience activation queries fail at runtime if
  the model is in `CREATE_IN_PROGRESS` or `CREATE_FAILED`. Always fetch
  the model state from `cleanroomsml get-configured-audience-model`.

- NEVER treat the collaboration creator as a "wildcard" principal. The
  creator is always the first member and is always ACTIVE; they cannot
  be REMOVED without deleting the collaboration. A "creator's role is
  too broad" finding is an IAM audit, not a Clean Rooms audit — route
  to the iam-least-privilege-advisor skill.

- NEVER skip the configured-table alias cross-reference. Analysis
  templates reference aliases; configured tables expose aliases; the
  collaboration's `configuredTables` list is the source of truth. A
  template with a dangling alias (member removed their table) passes
  static validation and fails only at query runtime. Audit the
  alias set in BOTH the templates and the configuredTables list.

- NEVER conflate `cleanrooms` (the collaboration API) with `cleanroomsml`
  (the audience-model API). They are separate AWS service namespaces
  with separate IAM permissions, separate CLI commands, and separate
  CloudTrail event sources. A policy granting `cleanrooms:*` does NOT
  grant `cleanroomsml:*`. An audit that checks only `cleanrooms` config
  misses the audience-model state entirely.

- NEVER recommend deleting a collaboration as remediation without
  explaining the blast radius. Deleting a collaboration removes ALL
  member memberships, ALL configured tables, ALL analysis templates,
  and ALL protected-query history. It is irreversible. The correct
  remediation for a single misconfigured member is to remove the member
  (`DeleteMember`), not the collaboration.

- NEVER assume epsilon "resets" at a calendar boundary. Clean Rooms
  epsilon is a monotonic budget per member per collaboration; there is
  no daily/monthly/annual reset. Once exhausted, the member cannot run
  further DP-protected queries without recreating the collaboration or
  obtaining a budget increase (via a new collaboration). Plan budgets
  for the collaboration lifetime, not per period.

- NEVER assume `analysis template` immutability means "always valid."
  Templates are immutable per-creation, but the configured tables they
  reference ARE mutable — a member can remove their configured table
  after the template was created. The template remains valid by
  creation-time checks; it fails only at runtime. Always cross-reference
  template aliases against the live configuredTables list.

- NEVER evaluate a collaboration's privacy posture without checking
  `aggregateConstraints`. Differential privacy is the noise layer;
  aggregate constraints are the structural floor. A collaboration with
  DP enabled but no aggregate constraints can still return singleton
  rows when the noise addition rounds a 1-row group up to the minimum
  threshold. Both layers must be present for defense in depth.

- NEVER treat a REMOVED member's historical queries as privacy-irrelevant.
  REMOVED members' protected queries are retained in the collaboration
  history; their epsilon contributions count toward the collaboration's
  total spend permanently. Removing a member does NOT reclaim their
  spent epsilon — the budget is consumed for the lifetime of the
  collaboration.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`UpdateCollaboration`, `DeleteMembership`, `DeleteCollaboration`,
  `StartProtectedQuery`, `UpdateConfiguredTableAnalysisRule`), the
  auditor MUST emit:
  `CONFIRM: About to <action> on collaboration <id>. This affects
  <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms. This gate
  prevents automated pipelines from silently modifying multi-party
  collaborations where every change affects every member.
- **Membership operations are not reversible without re-invitation.**
  `DeleteMembership` removes the member AND all their configured tables
  AND their analysis templates. Re-inviting requires
  `CreateCollaboration` re-issue — the member must accept again. Confirm
  the operator has notified the member's account owner before emitting
  the CLI.
- **`UpdateCollaboration` cannot change the creator.** The creator
  member is immutable for the collaboration's lifetime. If the creator
  account is being decommissioned, the only path is to recreate the
  collaboration under a new creator and re-invite all members — there is
  no transfer-ownership API.
- **Epsilon budget is not adjustable post-creation.** The per-member
  epsilon cap is set when differential privacy is configured on the
  collaboration. Increasing it requires recreating the collaboration
  with a new cap. Recommend budgeting for the collaboration lifetime at
  creation, not retroactively.
- **Confirm the collaboration exists and is accessible:**
  `aws cleanrooms get-collaboration --collaboration-id <id> --profile <p>`
  — fail closed (skip remediation) if it returns an error.
- **Capture current membership state for rollback:**
  `aws cleanrooms list-members --collaboration-id <id> --output json >
  /tmp/<id>-members-backup-$(date +%s).json` BEFORE any membership
  change. Membership changes are not versioned.
- **Multi-region guardrail.** Clean Rooms is region-scoped. All members
  must be in the same region as the collaboration. Before recommending
  cross-account operations, verify the member's AWS account region
  alignment — a member in the wrong region silently fails to activate.
- Prefer additive changes (add a member, add a constraint) over
  destructive changes (remove a member) — additive changes are
  reversible and do not risk breaking downstream audiences that depend
  on the collaboration's data.

## Remediation guidance

**Remediation ordering principle:** always prefer member-acceptance
flows and additive privacy controls over destructive membership
operations. Activate privacy controls (DP, aggregate constraints) BEFORE
revoking access — the safe sequence is: (1) snapshot state, (2) enable
DP / add constraints, (3) verify the controls are effective via a test
protected query, (4) only then remove a misconfigured member. This
prevents a window where neither the old nor new controls are in effect.

### For MEMBERSHIP_GAP — INVITED member (Rule M1)

1. Notify the member's account owner to accept the invitation:
   `aws cleanrooms create-membership --collaboration-arn <arn>
   --membership-display-name "<name>" --profile <member-profile>`.
2. If the member is no longer intended, revoke:
   `aws cleanrooms delete-membership --membership-identifier <arn>`.
3. Verify activation:
   `aws cleanrooms list-members --collaboration-id <id>` shows the
   member in `ACTIVE` state.

### For MEMBERSHIP_GAP — REMOVED/LEFT member (Rule M2)

1. Identify which analysis templates and configured tables referenced
   the removed member's data.
2. Either re-invite the member (`CreateMembership`) or update the
   templates to remove the dangling alias references.
3. Re-run the audit to verify no template references remain.

### For MEMBERSHIP_GAP — Solo collaboration (Rule M3)

1. Either invite the missing second party (`CreateMembership` invitation
   via the creator), or document the solo-collaboration as intentional
   (rare; usually indicates a stale proof of concept).
2. If the collaboration is no longer needed, delete it:
   `aws cleanrooms delete-collaboration --collaboration-id <id>`.

### For PRIVACY_RISK — DP disabled (Rule P1)

1. Enable differential privacy on the collaboration:
   `aws cleanrooms update-collaboration --collaboration-identifier <id>
   --differential-privacy-config enabled=true`.
2. Set a per-member epsilon budget appropriate to the collaboration
   lifetime (epsilon does NOT reset).
3. Verify on the next protected query: the response should include
   `additionalAnalyses` > 0.

### For PRIVACY_RISK — Epsilon near-exhausted (Rule P2)

1. Identify the high-spend member via per-member epsilon sum
   (ListProtectedQueries + sum epsilon per member).
2. Either (a) wait for the collaboration to be recreated with a higher
   budget, or (b) pause queries from the high-spend member until the
   collaboration is migrated.
3. CRITICAL — if queries are running with `additionalAnalyses: 0`
   despite DP being enabled, halt the queries immediately. This is an
   active privacy leak — rows are returning without noise.

### For PRIVACY_RISK — Aggregate constraints absent (Rule P3)

1. Add aggregate constraints to each configured table:
   `aws cleanrooms update-configured-table-analysis-rule
   --configured-table-id <id> --analysis-rule-type AGGREGATION
   --analysis-rule-aggregate-columns ...`.
2. Set MIN (typically 10+) and MAX as appropriate to the use case.
3. Verify via a test query that singleton-row returns are blocked.

### For CONFIG_GAP — Invalid analysis template (Rules A1-A4)

1. Identify the specific defect (unresolved parameter, dangling alias,
  invalid column).
2. Recreate the template with the corrected body:
   `aws cleanrooms create-analysis-template --collaboration-id <id>
   --name <new-name> --template-body <corrected-sql>`. Templates are
   immutable — you cannot edit in place.
3. Update any downstream references to the new template.

### For CONFIG_GAP — Output configuration missing (Rule Q1)

1. Configure the protected-query output:
   `aws cleanrooms update-protected-query --output-configuration
   s3={destination=<bucket-prefix>}`.
2. Verify the S3 bucket policy allows the Clean Rooms service principal
   to PutObject for the collaboration's members only.

### For CONFIG_GAP — Untrained configured audience (Rules C1-C3)

1. Fetch the audience-model state:
   `aws cleanroomsml get-configured-audience-model
   --configured-audience-model-arn <arn>`.
2. If `CREATE_FAILED`, inspect the training job logs and recreate:
   `aws cleanroomsml create-configured-audience-model ...`.
3. If `CREATE_IN_PROGRESS`, wait for training completion before
   activating audiences.
4. If the model is `INACTIVE` (training data expired), retrain with
   fresh data.

### For OK

1. No remediation required for the current posture.
2. Recommend enabling `queryLogStatus` if not already enabled (note:
   requires recreation — set at collaboration creation).
3. Recommend periodic re-audit, especially after any member
   transitions to REMOVED or LEFT state.
4. Verify the configured-audience model retraining cadence aligns with
   the source data refresh interval.

## Condition strength reference (Clean Rooms-specific)

| Privacy control | Strength | Reason |
|---|---|---|
| Differential privacy (epsilon > 0) | STRONG | Cryptographic noise added per-query; cumulative budget enforced server-side. Bypassable only by collusion across multiple queries below the noise floor. |
| Aggregate constraints (MIN >= 10) | STRONG | Server-enforced floor on output rows per group. Prevents singleton re-identification regardless of DP. |
| Aggregate constraints (MIN 2-9) | MODERATE | Small MIN values provide weak k-anonymity; combined with DP they are acceptable, alone they are insufficient. |
| Join controls (allowed join columns) | MODERATE | Restricts which columns can be joined; does not directly add noise but limits the query surface. |
| Output controls (allowed output columns) | MODERATE | Restricts which columns can be returned; complements configured-table allowedColumns. |
| Per-query `additionalAnalyses: 0` | NONE | DP noise is OFF for this specific query even if collaboration-level DP is enabled. |
| Configured-table allowedColumns | STRUCTURAL | Not a privacy control per se; defines the column surface. A column not in allowedColumns cannot be selected. |

## Deep reference: Clean Rooms internals

### Differential privacy budget math

Clean Rooms uses epsilon-differential privacy. The per-member epsilon
contribution for each protected query is specified in the query's
`additionalAnalyses` field. The cumulative spend is the sum of all
epsilon contributions across all queries the member has run. The cap is
set per-member at collaboration creation (or via
`UpdateCollaboration` before any query runs).

Key non-obvious facts:

- The cap is set when DP is FIRST enabled on the collaboration. It
  cannot be increased without recreating the collaboration.
- The cap is shared across all analysis templates a member runs queries
  against — it is not per-template.
- Epsilon is consumed even for FAILED queries if the noise was added
  before the failure.
- The `additionalAnalyses` field on a protected query is the epsilon
  contribution for THAT query. The total spend is the integral of these
  values across the member's query history.

### Configured table join semantics

A configured table exposes:

1. `allowedColumns` — the subset of Glue-table columns visible to the
   collaboration.
2. `joinColumns` — the subset of `allowedColumns` that can be used in
   JOIN clauses.
3. `analysisRules` — per-table rules (LIST, AGGREGATION, CUSTOM) that
   govern what query shapes are allowed.

A configured table with `analysisRuleType: LIST` allows only
row-selection queries (no aggregation). A table with `AGGREGATION`
requires aggregate constraints (MIN/MAX). A `CUSTOM` rule allows a
user-supplied SQL analysis rule — the most flexible and the most
privacy-risky.

### Clean Rooms ML integration model

Audience activation uses a separate service (`cleanroomsml`). The
collaboration references a `configuredAudienceModelArn`; the actual
training pipeline lives in `cleanroomsml`. The model has its own
lifecycle: `CREATE_IN_PROGRESS` → `READY` (or `CREATE_FAILED`) →
`INACTIVE`. The collaboration config shows only the ARN — the state is
fetched separately.

Audience activation queries write their output to an S3 bucket
configured on the `configuredAudienceModel` resource. A collaboration
with audience activation enabled but no destination on the model fails
at activation time. Always audit both the collaboration config AND the
cleanroomsml model state.

### Protected query lifecycle

1. `StartProtectedQuery` — caller submits SQL (or template reference) +
   parameters.
2. Service validates the query against configured tables, aggregate
   constraints, and DP budget.
3. If DP is enabled and the per-query epsilon would exceed the member's
   remaining budget, the query is REJECTED with `ServiceQuotaExceededException`.
4. If all checks pass, the query runs and writes results to each
   member's configured S3 output prefix in Parquet.
5. The query transitions: `SUBMITTED` → `RUNNING` → `SUCCEEDED` (or
   `FAILED` / `CANCELLED`).

A `SUCCEEDED` query does NOT mean the result was consumed. The S3
output must be read separately; a bucket policy that blocks the
member's read produces a silent empty result.

### Region scoping

Clean Rooms collaborations are region-scoped. All members must be in
the same region as the collaboration. Cross-region membership is not
supported. The membership is created in the collaboration's region; a
member account in a different region cannot activate. Always verify
the region alignment in the membership ARN.

## Domain

AWS CloudOps / Clean Rooms Collaboration Privacy & Compliance.
