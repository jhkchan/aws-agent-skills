---
name: cleanrooms-collaboration-auditor
description: Audits AWS Clean Rooms collaborations for membership-status gaps (INVITED or REMOVED members), privacy-budget risks (differential privacy disabled, epsilon spend exhausted, aggregate constraints missing), analysis-template SQL-validation defects (unresolved parameters, dangling table references), and configured-audience activation gaps (audience model untrained or stale). Emits a deterministic verdict (MEMBERSHIP_GAP | PRIVACY_RISK | CONFIG_GAP | OK) per collaboration with enumerated findings and specific CLI remediation. Use when reviewing Clean Rooms collaborations, checking member activation status, validating analysis templates, auditing the protected-query privacy budget, verifying configured-audience readiness, or hardening collaboration posture before production query traffic.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline config-doc classification. Live-account audits use aws cleanrooms get-collaboration, aws cleanrooms list-members, aws cleanrooms get-analysis-template, aws cleanrooms get-protected-query, aws cleanrooms list-configured-tables, aws cleanrooms get-membership, and aws cleanroomsml get-configured-audience-model (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  verdict_shape: MEMBERSHIP_GAP | PRIVACY_RISK | CONFIG_GAP | OK
  when_to_use: Reviewing a Clean Rooms collaboration before production query traffic, checking member activation status (INVITED vs ACTIVE vs REMOVED), validating differential-privacy budget posture (epsilon spend vs cap), auditing analysis-template SQL validity, auditing protected-query privacy controls, or validating configured-audience readiness for audience activation.
  activation_triggers: audit this Clean Rooms collaboration, check Clean Rooms member status, is differential privacy enabled, epsilon budget exhausted, validate analysis template SQL, is my audience model trained, Clean Rooms membership gap, configured audience ready, privacy budget audit, protected query failed, Clean Rooms collaboration posture
  invocation_schema: 'Input: either (a) a Clean Rooms collaboration configuration snapshot (collaboration metadata + member list + analysis-template body + differential-privacy config + configured-audience state), OR (b) a collaboration ARN or ID for live-account audit. Output: deterministic COLLABORATION/VERDICT/REASON/FINDINGS/REMEDIATION block per collaboration, where VERDICT ∈ {MEMBERSHIP_GAP, PRIVACY_RISK, CONFIG_GAP, OK, ERROR}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Clean Rooms, collaboration, membership status, differential privacy, epsilon budget, privacy budget, analysis template, SQL validation, protected query, aggregate constraints, configured audience, Clean Rooms ML, audience activation, INVITED member, REMOVED member, collaboration audit, data collaboration, privacy controls, cleanroomsml, join columns, configured table
  tags: cleanrooms, analytics, security, privacy, differential-privacy, collaboration, membership, audit
---

# Clean Rooms Collaboration Auditor

## Quick start

**Read-only:** emits findings + remediation text only — never executes
state-changing commands.

| Gate | Check | If failing |
|---|---|---|
| Membership | Any member `INVITED` or `REMOVED`? | **MEMBERSHIP_GAP** |
| Privacy | DP off, epsilon >= 80% cap, no `aggregateConstraints`? | **PRIVACY_RISK** |
| Config | Unresolved `${param}`, dangling alias, audience not `READY`? | **CONFIG_GAP** |
| All pass | — | **OK** |

Precedence: `MEMBERSHIP_GAP > PRIVACY_RISK > CONFIG_GAP > OK`.

**Top 3 traps:** (1) `INVITED` member = MEMBERSHIP_GAP always;
(2) DP `enabled: true` does NOT mean queries run with noise — check
per-query `additionalAnalyses`; (3) epsilon never resets — it is a
lifetime budget per member.

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

Full wording of the three structural facts (membership activation gating, per-member epsilon budgets, per-member template ownership): [Advanced patterns](references/advanced-patterns.md).

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

## Pre-flight: collaboration metadata gate (run before classification)

Before evaluating membership and privacy, classify the collaboration
itself. Several attributes **short-circuit** the audit — misclassifying
them produces false positives that erode trust.

Pagination sweep procedure (list-collaborations / list-members / list-analysis-templates, 100/page, drain nextToken): [Diagnostic commands](references/diagnostic-commands.md).

IAM-permission, CloudTrail-event, and membership-snapshot pre-flight checks: [Diagnostic commands](references/diagnostic-commands.md).

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

All 21 non-obvious behaviors (perspective-relative status, per-member epsilon, DP enabled vs applied, output-row aggregate constraints, template parameters, dangling aliases, cleanroomsml separation, S3 result destinations, invalid status strings, epsilon-via-query-results accounting, region scoping, one-way queryLogStatus, DP sensitivity scaling, non-retroactive rule updates, 7-day invitation expiry, allowedColumns drift, low-epsilon garbage output, multi-table JOIN cost, ListProtectedQueries pagination, SPARK execution roles, analysis-rule response shapes): [Advanced patterns](references/advanced-patterns.md).

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
  - [SEVERITY] <finding description (Rule Xn)> — one line per finding
EPSILON: <per-member spend: accountId:spent/cap, ...; or "N/A" if DP disabled>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

Field rules:
- **VERDICT**: exactly one value from the enum. No modifiers.
- **FINDINGS**: list ALL dimension findings (not just the verdict
  dimension). Each finding tagged with its severity bracket.
- **EPSILON**: always present. Per-member breakdown so the operator
  sees WHO is near-exhaustion, not just an aggregate.
- **REMEDIATION**: numbered list, one action per finding.

### Worked example — collaboration with INVITED member and no DP

```text
COLLABORATION: arn:aws:cleanrooms:us-east-1:111111111111:collaboration/abc-123
VERDICT: MEMBERSHIP_GAP
REASON: Member 333333333333 is in INVITED state (Rule M1) — collaboration
is operationally partial.
FINDINGS:
  - [MEMBERSHIP_GAP] Member 333333333333 in INVITED state (Rule M1)
  - [PRIVACY_RISK] differentialPrivacyConfig absent (Rule P1)
EPSILON: 111: 0.5/10.0, 222: 0.3/10.0, 333: N/A (INVITED)
REMEDIATION:
  1. Have 333 accept: aws cleanrooms create-membership
     --collaboration-arn <arn> --profile 333-profile
  2. Enable DP: aws cleanrooms update-collaboration
     --collaboration-identifier <id> --differential-privacy-config
     enabled=true
```

### Multi-collaboration batch output

When auditing multiple collaborations (e.g., a full account sweep),
emit ONE verdict block per collaboration, separated by `---`:

```text
COLLABORATION: <id-1>
VERDICT: <verdict-1>
...
---
COLLABORATION: <id-2>
VERDICT: <verdict-2>
...
```

End with a summary line:
`SUMMARY: <N> collaborations audited — <count> MEMBERSHIP_GAP, <count>
PRIVACY_RISK, <count> CONFIG_GAP, <count> OK.`

### Error and edge-case handling

Malformed-JSON, throttled-pagination (backoff + never report OK), and missing-cleanroomsml-permission handling: [Error handling](references/error-handling.md).

## Pre-flight safety checks (run before any remediation CLI)

**Read-only audit mode:** this skill operates in read-only mode by
default. It emits findings and CLI remediation TEXT but NEVER executes
state-changing commands. Set the explicit flag `AUDIT_READONLY=1` in
automated pipelines to enforce this — when set, the skill MUST NOT emit
CLI commands that execute, only their text representation for operator
review.

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
  `CreateCollaboration` re-issue — the member must accept again.
- **`UpdateCollaboration` cannot change the creator.** The creator
  member is immutable for the collaboration's lifetime. If the creator
  account is being decommissioned, the only path is to recreate the
  collaboration under a new creator and re-invite all members.
- **Epsilon budget is not adjustable post-creation.** The per-member
  epsilon cap is set when differential privacy is configured. Increasing
  it requires recreating the collaboration.
- **Capture current membership state for rollback:**
  `aws cleanrooms list-members --collaboration-id <id> --output json >
  /tmp/<id>-members-backup-$(date +%s).json` BEFORE any membership
  change. Membership changes are not versioned.
- **Multi-region guardrail.** Clean Rooms is region-scoped. Verify
  member account region alignment before cross-account operations.
- Prefer additive changes (add a member, add a constraint) over
  destructive changes.

## Anti-Patterns — NEVER

- NEVER ignore the S3 bucket policy on the protected-query output
  destination. The result set — even with DP noise — contains real
  user data. A bucket policy granting `s3:GetObject` to `*` or to
  cross-account principals beyond the collaboration members silently
  exposes the noised result set. Always audit the output bucket
  policy: scope `s3:GetObject` to the collaboration's member account
  ARNs only, and add an explicit `Deny` for `Principal: *` on the
  prefix. This is the most common production leakage path — operators
  widen the policy for a one-time export and forget to tighten it.

- NEVER grant `cleanrooms:*` or `cleanroomsml:*` wildcard to the
  auditor IAM role. The auditor needs only `Get*` and `List*`
  permissions. Granting `cleanrooms:Delete*`,
  `cleanrooms:Update*`, or `cleanrooms:StartProtectedQuery` to a
  read-only audit principal violates least privilege and enables
  accidental destruction of multi-party state. The auditor role should
  be scoped to: `cleanrooms:Get*`, `cleanrooms:List*`,
  `cleanroomsml:Get*`, `cleanroomsml:List*`, plus `glue:GetTable` for
  schema-drift checks. Any broader scope is a finding.

- NEVER classify a collaboration with a member in `INVITED` state as
  `OK`. The collaboration is operationally partial regardless of how
  clean the privacy config looks.

- NEVER treat `differentialPrivacyConfig.enabled: true` as proof that
  queries are running with DP noise. The per-query `additionalAnalyses`
  epsilon is the enforcement, not the collaboration-level flag.

- NEVER report PRIVACY_RISK based solely on aggregate epsilon-spend
  percentage without naming the per-member spend. Epsilon is per-member.

- NEVER assume a `SUCCEEDED` protected query means the result was
  consumed correctly. The result rows are written to S3 in Parquet; a
  bucket policy blocking the member's PutObject produces a silent
  empty-prefix failure.

- NEVER rely on `list-members` alone for membership status in a
  multi-party audit. `ListMembers` returns the collaboration's view;
  `GetMembership` returns the caller's OWN perspective. A member can
  appear `ACTIVE` in `list-members` while having self-removed (`LEFT`
  status in their own `get-membership` view). Always cross-reference
  both APIs — a member listed as ACTIVE who has actually LEFT is a
  silent MEMBERSHIP_GAP that surfaces only when their queries fail
  with `AccessDeniedException`.

- NEVER conflate `cleanrooms` with `cleanroomsml`. Separate service
  namespaces, separate IAM permissions, separate CloudTrail event
  sources. `cleanrooms:*` does NOT grant `cleanroomsml:*`.

- NEVER recommend deleting a collaboration as remediation without
  explaining the blast radius — it removes ALL members, configured
  tables, analysis templates, and query history irreversibly.

- NEVER assume epsilon resets at a calendar boundary. It is a monotonic
  per-member budget for the collaboration's lifetime.

- NEVER evaluate privacy posture without checking `aggregateConstraints`.
  DP is the noise layer; aggregate constraints are the structural floor.

- NEVER treat a REMOVED member's historical queries as
  privacy-irrelevant. Their epsilon contributions count toward the
  collaboration's total spend permanently.

## Remediation guidance

Ordering principle and per-verdict remediation playbooks (M1/M2/M3 membership, P1/P2/P3 privacy, A1-A4 templates, Q1 output config, C1-C3 audience, OK posture): [Advanced patterns](references/advanced-patterns.md).

## Condition strength reference (Clean Rooms-specific)

Full privacy-control strength table (DP, aggregate constraints, join/output controls, per-query additionalAnalyses: 0 bypass, allowedColumns): [Advanced patterns](references/advanced-patterns.md).

## Reference: Clean Rooms internals

Analysis-rule types (LIST/AGGREGATION/CUSTOM), protected-query lifecycle, and Clean Rooms ML model lifecycle: [Advanced patterns](references/advanced-patterns.md).

## Recent AWS features (2024-2026)

Recent features (ID mapping tables, differential-privacy enhancements, ML model collaboration): [Advanced patterns](references/advanced-patterns.md).

## References (load on demand)

- [Advanced patterns](references/advanced-patterns.md) — Mindset structural facts, all 21 Step-0 expert behaviors, remediation playbooks, condition-strength table, Clean Rooms internals, recent features
- [Diagnostic commands](references/diagnostic-commands.md) — pagination sweep procedure and live-account pre-flight checks
- [Error handling](references/error-handling.md) — malformed JSON, throttled pagination, missing cleanroomsml permissions

## Domain

AWS CloudOps / Clean Rooms Collaboration Privacy & Compliance.

## AWS documentation

- **Service documentation** — AWS Clean Rooms User Guide: https://docs.aws.amazon.com/clean-rooms/latest/userguide/what-is.html
- **Security** — Clean Rooms Security: https://docs.aws.amazon.com/clean-rooms/latest/userguide/security.html
- **API reference** — Clean Rooms API Reference: https://docs.aws.amazon.com/clean-rooms/latest/APIReference/
- **CLI reference** — Clean Rooms CLI Reference: https://docs.aws.amazon.com/cli/latest/reference/cleanrooms/
- **Differential privacy in Clean Rooms** — https://docs.aws.amazon.com/clean-rooms/latest/userguide/differential-privacy.html
