---
name: cloudtrail-lake-operator
description: >-
  Operates AWS CloudTrail Lake end-to-end — Event Data Store (EDS)
  creation with the full ingestion surface (CloudTrail management
  events, CloudTrail data events for S3/Lambda, AWS Config
  snapshots, Audit Manager evidence, non-AWS events via Partner
  integrations, CloudTrail Insights), organization scope and
  SSE-KMS encryption, PartiQL queries (WHERE on eventTime/
  eventSource/eventName/userIdentity, JOIN across same-Region EDS,
  aggregation via GROUP BY/COUNT/SUM/AVG), query optimization via
  partitioning and columnar tuning, Athena federation via the
  CloudTrailLake connector for cross-account/cross-Region queries,
  QuickSight dashboards on top of Athena, and non-AWS ingestion
  via PutAuditEvents with registered Partner sources. Runs
  deterministic pre-checks behind a CONFIRM gate and emits a READY,
  BLOCKED, or COMPLETED verdict.
  Use when creating or modifying an EDS, configuring organization
  ingestion, writing PartiQL queries, diagnosing slow or empty
  queries, federating via Athena, or ingesting non-AWS events.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). No AWS CLI required for offline plan
  classification. Live-account operations use aws cloudtrail
  create-event-data-store, update-event-data-store,
  delete-event-data-store, list-event-data-stores,
  get-query, start-query, describe-query, get-query-results,
  get-event-data-store, list-queries, put-audit-events (with
  partner-type), aws lakeformation grant permissions (for Athena
  federation), aws athena start-query-execution, get-query-results,
  and aws kms describe-key / get-key-policy (AWS CLI v2, SSO or
  key-based credentials).
keywords:
  - AWS CloudTrail Lake
  - CloudTrail Lake
  - Event Data Store
  - EDS
  - PartiQL
  - CloudTrail query
  - federated query Athena
  - Athena CloudTrail Lake connector
  - non-AWS events CloudTrail
  - PutAuditEvents
  - CloudTrail data events
  - CloudTrail management events
  - AWS Config configuration snapshots
  - AWS Audit Manager evidence
  - CloudTrail Insights
  - organization trail Lake
  - multi-account CloudTrail Lake
  - Lake query optimization
  - CloudTrail Lake partitioning
  - QuickSight CloudTrail Lake
tags: [aws, cloudtrail, lake, governance, audit, security, partiql, athena, quicksight, operate]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Governance
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY | BLOCKED | COMPLETED"
  when_to_use: >-
    Creating or modifying an Event Data Store (EDS), configuring
    multi-account or organization-level ingestion into CloudTrail
    Lake, ingesting non-AWS events (SaaS apps, on-prem) via
    PutAuditEvents, writing PartiQL queries (SELECT, WHERE, JOIN,
    aggregation, time-window analytics), diagnosing a slow or empty-
    result query, federating Lake queries via Athena for cross-
    account or cross-Region analysis, building QuickSight dashboards
    on top of Athena-federated CloudTrail Lake, or configuring
    CloudTrail Insights events ingestion.
  activation_triggers:
    - "create Event Data Store"
    - "CloudTrail Lake EDS"
    - "PartiQL query CloudTrail"
    - "federated query Athena"
    - "Athena CloudTrail Lake connector"
    - "non-AWS events CloudTrail"
    - "PutAuditEvents"
    - "ingest SaaS audit logs to AWS"
    - "CloudTrail data events to Lake"
    - "CloudTrail management events to Lake"
    - "AWS Config snapshots to Lake"
    - "Audit Manager evidence to Lake"
    - "CloudTrail Insights to Lake"
    - "organization CloudTrail Lake"
    - "multi-account CloudTrail Lake"
    - "CloudTrail Lake query slow"
    - "CloudTrail Lake empty results"
    - "QuickSight CloudTrail Lake"
  invocation_schema: >-
    Input: either (a) a CloudTrail Lake Event Data Store
    configuration (get-event-data-store, list-event-data-stores,
    get-query, get-query-results) plus the intended operation
    (create-eds, update-eds, run-query, diagnose-empty-query,
    diagnose-slow-query, federate-via-athena, configure-non-aws-
    ingestion, configure-quicksight), OR (b) a specific EDS + PartiQL
    SQL pair for live-account execution. Output: deterministic
    OPERATION / VERDICT / PRE_CHECKS / STEPS / POST_VERIFY / NOTES
    block per operation, where VERDICT is one of READY, BLOCKED,
    COMPLETED.
---

# AWS CloudTrail Lake Operator

## What this skill does

Executes AWS CloudTrail Lake operations correctly and safely across
the full ingestion-to-query surface. Runs deterministic pre-checks
before any state-changing CLI — Event Data Store (EDS) Region
selection (Lake is a Regional service; cross-Region ingestion
requires organization-level EDS), KMS encryption configuration
(SSE-KMS via customer-managed key + key policy grant to
`cloudtrail.amazonaws.com`), ingestion-source compatibility
(allowed event categories: `CloudTrail management`, `CloudTrail
data`, `Config configuration snapshots`, `Audit Manager evidence`,
`non-AWS events via Partner`, `CloudTrail Insights`), organization
ingestion (`isOrganizationService: true` requires the EDS be
created by the management account), retention-period validity (90
to 3653 days, or `INDEFINITE`), partitioning strategy (Lake
auto-partitions on event time, but custom partition keys can be
derived from `eventTime`, `eventSource`, `userIdentity.accountId`),
PartiQL query syntax validity (SELECT, WHERE on `eventTime`,
`eventSource`, `eventName`, `userIdentity` fields; JOIN across EDS
in the same Region), Athena federation prerequisites (the Athena
CloudTrailLake data source connector deployed, Lake Formation
grants on the connector, workgroup configured), QuickSight
permissions (QuickSight service role allowed to assume the Athena
workgroup role), and non-AWS ingestion setup (a Partner event
source registered, the partner IAM role with
`cloudtrail:PutAuditEvents`). Executes the change behind a CONFIRM
gate, then verifies by running a smoke-test query and confirming
row count and approximate latency within expected bounds.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds (BLOCKED/READY/COMPLETED) + pre-check priority | Before any operation |
| **§ Mindset** | Why Lake is a Regional columnar store; the partition-or-perish trap; the no-schema-flex trap | Understanding the safety model |
| **§ Pre-flight** | EDS + Athena federation gate — KMS, ingestion source, organization scope, query workgroup | Before executing any CLI |
| **§ Process** | Per-operation planning: create-eds, update-eds, run-query, diagnose-empty-query, diagnose-slow-query, federate-via-athena, configure-non-aws-ingestion, configure-quicksight | When choosing which operation to run |
| **§ Output format** | STRICT output contract — OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY/NOTES template | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that strand events or produce empty query results | Review before risky operations |
| **§ Pre-flight safety** | Capture pre-state, KMS key policy, organization scope, Athena workgroup | Defense-in-depth |
| **§ Expert heuristic** | Lake is a columnar store — never assume a query that compiles is fast | Avoiding the partition-or-perish trap |

## STRICT output contract

EVERY response MUST end with a single fenced text block in this exact
shape (the operator's downstream tooling greps for it). No deviations:

```text
OPERATION: <create-eds | update-eds | run-query | diagnose-empty-query | diagnose-slow-query | federate-via-athena | configure-non-aws-ingestion | configure-quicksight>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <eds-id> (region: <region>, ingestion: <sources>) (query: <sql-or-"none">)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated, or "(none — pre-checks failed)">
  2. <wait / monitoring command>
POST_VERIFY:
  - [PASS] <verification description> | (pending execution)
  - [FAIL] <verification description> — <reason>
NOTES: <schedule, monitoring, caveats>
```

Rules of the contract:

- VERDICT is exactly one of `READY`, `BLOCKED`, `COMPLETED`. No other
  values. `READY` means pre-checks passed and a CONFIRM gate is
  pending; `BLOCKED` means at least one pre-check failed — do NOT
  emit STEPS that mutate state; `COMPLETED` means post-verification
  passed after execution.
- If PRE_CHECKS has any `[FAIL]`, VERDICT MUST be `BLOCKED` and STEPS
  MUST be `(none — pre-checks failed)`.
- If VERDICT is `READY`, STEPS[1] MUST be the CONFIRM prompt and
  STEPS[2] MUST be the actual CLI.
- If VERDICT is `COMPLETED`, POST_VERIFY MUST contain at least one
  `[PASS]` and no `[FAIL]`.
- Never wrap the block in JSON, never abbreviate the field names,
  never omit a section. If a section is empty, write `(none)`.

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (EDS Region mismatch vs ingestion target, KMS key policy missing `cloudtrail.amazonaws.com` grant, organization EDS created by member account, retention period outside 90-3653 days, event category not in the allowed list, Athena workgroup missing, Lake Formation grant absent on the connector, partner event source not registered, QuickSight service role cannot assume the Athena workgroup role, PartiQL syntax error, JOIN across EDS in different Regions) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Query returned `QueryStatus: FINISHED` AND post-verification passed (rows match expected count, latency within expected bound, no `QueryStatus: FAILED` or `CANCELLED`) | Emit verification results, monitoring plan |

**Priority order for pre-checks (apply in this sequence, all must pass
for READY):**

1. **EDS exists and is `Status: ENABLED`.** A `DELETING` or
   `PENDING_DELETION` EDS cannot be queried or written to.
2. **Region alignment.** Lake is Regional; a query can only reference
   EDS in the same Region as the query API call. Cross-Region
   analysis requires Athena federation or EDS replication.
3. **Ingestion source compatibility.** The EDS `EventCategory` list
   must include the intended source(s): `Management`, `Data`,
   `ConfigConfiguration`, `AuditManagerEvidence`, `NetworkActivity`,
   `Insights`, or non-AWS (Partner). Mismatches produce zero rows
   in queries.
4. **KMS encryption chain.** For SSE-KMS EDS, the customer-managed
   key policy MUST grant `cloudtrail.amazonaws.com`
   `kms:GenerateDataKey`, `kms:Decrypt`, and the caller needs
   `kms:Decrypt` to read results.
5. **Organization scope.** `isOrganizationService: true` EDS can
   only be created by the management account. Member accounts can
   only create standalone EDS for their own events.
6. **Retention period validity.** 90 to 3653 days, or the literal
   string `INDEFINITE`. Anything outside this range is rejected.
7. **Multi-account ingestion.** For an org EDS, the management
   account must enable AWS Organizations access for CloudTrail.
8. **PartiQL syntax.** `SELECT` is the only DML allowed (no INSERT,
   UPDATE, DELETE — non-AWS ingestion uses `PutAuditEvents` API).
   WHERE must reference supported columns. Aggregation functions
   (`COUNT`, `SUM`, `AVG`, `MIN`, `MAX`) and `GROUP BY` are
   supported. JOIN across EDS in the same Region is supported.
9. **Athena federation prerequisites.** Athena CloudTrailLake
   connector deployed (Lambda-backed), Lake Formation grant on the
   connector to the caller, Athena workgroup configured with output
   location.
10. **Non-AWS ingestion setup.** Partner event source registered;
    partner IAM role has `cloudtrail:PutAuditEvents` plus
    `kms:GenerateDataKey` on the EDS KMS key.

**Cost/time baselines (2026):**

- Ingestion: $0.10 per 100,000 events for the first 25M events per
  account per Region per month; $0.05 per 100,000 above 25M. Data
  events (S3/Lambda) typically dominate volume.
- Storage: $0.05 per GB-month for ingested events retained beyond
  the free tier.
- Query: $0.005 per GB scanned. Lake is columnar; selecting fewer
  columns reduces bytes scanned.
- Athena federation: standard Athena pricing ($5/TB scanned) PLUS
  Lake query cost on the underlying EDS. Federation is for
  cross-account/cross-Region convenience, not cost savings.
- Typical first-query latency on a 100 GB EDS: 10-30 seconds for a
  partitioned time-window query; 5-15 minutes for a full-table
  scan without partition pruning.

## Mindset

**One-line takeaway:** CloudTrail Lake is a Regional columnar store
with a fixed event schema — a query that compiles is not necessarily
fast, and a zero-row result is more often a partition-miss than an
empty source. Driven by three Lake realities:

- **Lake is Regional.** An EDS in `us-east-1` cannot be queried from
  `eu-west-1` via the Lake API directly. Cross-Region or cross-account
  analysis requires Athena federation (with the CloudTrailLake
  connector) or replicating events into a second EDS. Operators
  routinely assume Lake is global like CloudTrail itself; it is NOT.
- **Partition pruning is the only performance lever.** Lake
  auto-partitions on event time; a WHERE clause on `eventTime` is
  the single most impactful filter. Without a time bound, every
  query is a full-table scan. Other partition keys (`eventSource`,
  `eventName`) can help but are secondary to time.
- **Non-AWS events require an explicit Partner integration.** The
  EDS must declare `EventCategory: non-AWS` (Partner) and the
  Partner event source must be registered. `PutAuditEvents` from a
  non-Partner IAM role is rejected. Operators routinely assume any
  external audit log can be pushed to Lake; only Partners in the
  CloudTrail Lake partner program are supported.

## Pre-flight: EDS + Athena federation gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `list-event-data-stores` paginates at 50.
`list-queries` paginates at 50 by default. `get-query-results`
paginates up to 1,000 rows per call; for larger results iterate.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws cloudtrail list-event-data-stores` — find the target EDS by
   `Name`, capture `EventDataStoreArn`, `Status`, `KmsKeyId`,
   `IsOrganizationsEnabled`, `EventConfigurations`.
2. `aws cloudtrail get-event-data-store --event-data-store <id>` —
   capture `Status` (`ENABLED`, `DELETING`, `PENDING_DELETION`),
   `AdvancedEventSelectors`, `RetentionPeriod`, `TerminationProtectionEnabled`.
3. For SSE-KMS EDS: `aws kms describe-key --key-id <kms-key-id>` and
   `get-key-policy --key-id <kms-key-id> --policy-name default` —
   confirm `cloudtrail.amazonaws.com` has `kms:GenerateDataKey`,
   `kms:Decrypt`.
4. `aws organizations describe-organization` — if the EDS is
   org-scoped, confirm the caller is the management account.
5. `aws cloudtrail describe-query --event-data-store <id> --query-id
   <id>` — for the most recent query, capture `QueryStatus`,
   `QueryRunTimeInSeconds`, `BytesScanned`, `ResultsCount`.
6. `aws cloudtrail get-query` (deprecated alias: `get-query`) — for
   diagnosing a failed query, capture `ErrorMessage`.
7. For Athena federation: `aws athena list-work-groups` — confirm
   the workgroup exists; `aws lakeformation list-permissions` —
   confirm the CloudTrailLake connector Lambda has permissions on
   the underlying EDS.
8. For QuickSight: `aws quicksight describe-account-settings` —
   confirm QuickSight is registered; check that the QuickSight
   service role can assume the Athena workgroup role.
9. For non-AWS ingestion: `aws cloudtrail list-partner-event-sources`
   (deprecated) — or `list-event-data-stores` filtering by
   `EventCategory: non-AWS` — confirm the Partner event source is
   registered and points to the intended EDS.
10. For multi-account ingestion: confirm the management account has
    `AWSServiceRoleForCloudTrail` and any service-linked roles
    enabled.

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: EDS or query configuration
is not valid JSON or is missing required fields — cannot plan.` and
`REMEDIATION: Re-fetch with aws cloudtrail get-event-data-store
--event-data-store <id> --output json and re-plan.`

| EDS / query attribute | Effect on operation |
|---|---|
| EDS `Status: DELETING` | create-eds BLOCKED; queries BLOCKED. Wait or pick another EDS. |
| EDS `Status: PENDING_DELETION` | Recovery requires `undelete-event-data-store` within 7 days. Otherwise gone. |
| `KmsKeyId` set but key policy missing `cloudtrail.amazonaws.com` | BLOCKED; key policy MUST grant cloudtrail `kms:GenerateDataKey`, `kms:Decrypt`. |
| `IsOrganizationsEnabled: true` EDS created by member account | BLOCKED at creation; org EDS must be created by management account. |
| `EventCategory` list missing the intended source | Queries return zero rows even when source data exists. |
| `RetentionPeriod: 30` (< 90) | BLOCKED at creation; min is 90 days. |
| `RetentionPeriod: 4000` (> 3653) | BLOCKED at creation; max is 3653 days (10 years). |
| `TerminationProtectionEnabled: true` and operator wants `delete-eds` | BLOCKED; disable protection first via `update-event-data-store`. |
| Query SQL missing `WHERE eventTime BETWEEN ...` | WARNING; full-table scan. Always include a time bound. |
| Query SQL references column not in Lake schema (e.g., `region`) | BLOCKED at runtime; only `awsRegion`, not `region`. |
| Query SQL uses `JOIN` across EDS in different Regions | BLOCKED at runtime; JOIN is same-Region only. |
| Query SQL uses DML other than `SELECT` | BLOCKED; Lake is read-only via PartiQL. |
| Athena workgroup missing | BLOCKED; create or pick existing workgroup. |
| Lake Formation grant missing on connector Lambda | BLOCKED; federated query returns `AccessDenied`. |
| Partner event source not registered | BLOCKED; `PutAuditEvents` from partner role is rejected. |
| Partner role missing `cloudtrail:PutAuditEvents` | BLOCKED; attach the IAM policy. |
| QuickSight service role cannot assume Athena workgroup role | BLOCKED; add trust policy on the Athena role. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious CloudTrail Lake behaviors

These behaviors are easy to misjudge without operational Lake
experience. Each changes a plan if ignored:

- **Lake is Regional.** Each EDS lives in a specific Region. The
  Lake query API only references EDS in the same Region as the API
  call. Cross-Region analysis requires Athena federation with the
  CloudTrailLake connector (deploy the connector Lambda in each
  Region you want to query).

- **The EDS schema is fixed and event-category-scoped.** A single
  EDS can ingest one or more event categories
  (`Management`, `Data`, `ConfigConfiguration`,
  `AuditManagerEvidence`, `NetworkActivity`, `Insights`, non-AWS).
  But the columns available in a query depend on the category. A
  `Management`-only EDS does not expose `configSnapshot` fields; a
  non-AWS EDS exposes `userIdentity` differently than AWS events.

- **`eventTime` is THE partition key.** Lake auto-partitions on
  event time. A query without a `WHERE eventTime BETWEEN ...` clause
  scans every partition. Always include a time bound — even a wide
  one (last 90 days) is dramatically faster than no bound.

- **JOIN across EDS is supported only within the same Region.**
  `SELECT ... FROM edsa, edsb WHERE ...` works if both EDS are in
  the Region of the query API. Cross-Region JOINs require Athena
  federation with multiple connector instances.

- **Non-AWS events require a Partner integration.** Direct
  `PutAuditEvents` from any IAM role fails UNLESS the role is a
  registered Partner. As of 2026 there are 30+ partners (CrowdStrike,
  Datadog, Splunk, Wiz, etc.). Operators cannot self-register; the
  Partner initiates registration.

- **Multi-account ingestion requires an org-level EDS.** To ingest
  events from all accounts in an AWS Organization, the EDS must be
  created by the management account with
  `is-organization-service: true`. Member accounts can only create
  standalone EDS for their own events.

- **`TerminationProtectionEnabled: true` is the default for new
  EDS.** To delete a protected EDS, first call
  `update-event-data-store --no-termination-protection-enabled`,
  then `delete-event-data-store`. The 7-day recovery window starts
  at deletion.

- **Athena federation adds a hop, not a shortcut.** A federated
  query runs a Lake query on the underlying EDS, then Athena scans
  the returned rows. Cost = Lake query cost + Athena scan cost.
  Federation is for cross-account/cross-Region/cross-EDS
  convenience, NOT cost savings.

- **QuickSight on top of Athena-on-Lake is the canonical BI
  pattern.** QuickSight cannot query Lake directly; it must go
  through Athena. Configure the Athena workgroup first, then add
  Athena as a QuickSight data source.

- **CloudTrail Insights events are a separate event category.** An
  EDS configured for Insights-only events has zero Management or
  Data events. Most operators want a Management EDS and a separate
  Insights EDS.

- **Data events for S3 are the highest-volume ingestion source.** A
  busy S3 workload can generate millions of data events per hour.
  Tune AdvancedEventSelectors to ingest only the prefixes/buckets
  needed; otherwise storage and query costs explode.

- **Config configuration snapshots are bulk events.** Each snapshot
  is one event per resource; a 100,000-resource account generates
  100,000 events per snapshot interval. Tune the EDS to ingest
  snapshots only for specific resource types.

- **Audit Manager evidence ingestion requires an evidence-safe EDS.**
  The EDS must declare `AuditManagerEvidence` in its event
  categories, and the Audit Manager assessment must be configured
  to send evidence to the EDS.

- **`PutAuditEvents` (non-AWS) takes a `sessionToken`.** The session
  token is generated by CloudTrail on Partner registration and is
  unique per Partner per EDS. Tokens expire; rotate per Partner
  contract.

- **Query results are NOT auto-persisted.** `get-query-results`
  returns rows in the API response. For large results, configure
  the query to write to an S3 bucket via Athena federation; the
  native Lake API does not have an output location.

- **`start-query` returns a `QueryId` immediately.** Poll
  `describe-query` until `QueryStatus: FINISHED`, `FAILED`, or
  `CANCELLED`. Typical latency 10-30s for partitioned queries; 5-15
  min for full-table scans.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL pre-checks for the chosen operation. If ANY fails, the verdict
is BLOCKED with the failed checks in PRE_CHECKS. Do NOT execute.

**For ALL operations:**
1. EDS `EventDataStoreArn` exists (or operator is creating new) in
   the expected account/Region.
2. EDS `Status: ENABLED` (not `DELETING`, `PENDING_DELETION`).
3. Caller has `cloudtrail:GetQuery`, `cloudtrail:StartQuery` on the
   EDS ARN.

**For create-eds (new `create-event-data-store`):**
4. Caller is the management account IF `--is-organization-service`
   is set.
5. `--retention-period` is between 90 and 3653 days, or the literal
   `INDEFINITE`.
6. `--kms-key-id` (if set) exists; key policy grants
   `cloudtrail.amazonaws.com` `kms:GenerateDataKey`, `kms:Decrypt`.
7. `--advanced-event-selectors` reference valid event categories
   (`Management`, `Data`, `ConfigConfiguration`,
   `AuditManagerEvidence`, `NetworkActivity`, `Insights`, non-AWS).
8. `--termination-protection-enabled` set (default true).
9. For non-AWS: the Partner event source is registered.

**For update-eds:**
5. EDS exists.
6. `TerminationProtectionEnabled` not blocking the update (deletion
   requires first disabling).
7. New `EventConfigurations` is internally consistent.
8. Pre-state captured (full prior configuration).

**For run-query:**
5. PartiQL SQL is syntactically valid.
6. SQL includes `WHERE eventTime BETWEEN ...` (partition pruning).
7. SQL references only Lake-supported columns (`eventTime`,
   `eventSource`, `eventName`, `awsRegion`, `userIdentity.*`,
   `requestParameters.*`, `responseElements.*`, etc.).
8. If `JOIN`, both EDS exist in the same Region.
9. The EDS `EventCategory` list includes the categories the SQL
   filters on.

**For diagnose-empty-query (read-only, no BLOCKED gate):**
4. Read the failure-mode table to identify the root cause from
   `QueryStatus`, `BytesScanned`, `ResultsCount`.

**For diagnose-slow-query (read-only, no BLOCKED gate):**
4. Inspect `describe-query` for `BytesScanned`,
   `QueryRunTimeInSeconds`. The fix is partition pruning or column
   reduction.

**For federate-via-athena:**
5. Athena workgroup exists.
6. CloudTrailLake connector Lambda deployed in the Region.
7. Lake Formation grant on the connector Lambda for the EDS.
8. Athena workgroup role has `cloudtrail:GetQuery`,
   `cloudtrail:StartQuery`, `cloudtrail:GetQueryResults` on the EDS,
   plus `kms:Decrypt` if SSE-KMS.

**For configure-non-aws-ingestion:**
5. Partner event source registered (Partner name matches a known
   CloudTrail Lake partner).
6. Partner IAM role has `cloudtrail:PutAuditEvents` on the EDS.
7. Partner IAM role has `kms:GenerateDataKey` on the EDS KMS key.
8. EDS `EventCategory` includes non-AWS.

**For configure-quicksight:**
5. QuickSight account registered.
6. Athena workgroup exists and is configured for QuickSight.
7. QuickSight service role can assume the Athena workgroup role.
8. QuickSight SPICE capacity available (if importing).

**CloudTrail Lake failure-mode table (use during diagnose-empty-query
and diagnose-slow-query):**

| Symptom | Root cause | Fix |
|---|---|---|
| `QueryStatus: FINISHED`, `ResultsCount: 0`, EDS has events | EDS `EventCategory` list does not include the queried event source | `update-event-data-store` to add the missing category. |
| `ResultsCount: 0`, `eventTime` filter outside retention | Events aged out past `RetentionPeriod`. | Tighten the time window OR extend `RetentionPeriod` (only future events). |
| `ResultsCount: 0`, `awsRegion` filter wrong | Operator queried `region=...`; Lake column is `awsRegion`. | Fix SQL: `awsRegion = 'us-east-1'`. |
| `QueryStatus: FAILED`, `ErrorMessage: "Column not found"` | SQL references a non-Lake column. | Use only supported columns (`eventTime`, `eventSource`, `eventName`, `awsRegion`, `userIdentity.*`, etc.). |
| `QueryStatus: FAILED`, `ErrorMessage: "EDS not in this Region"` | Cross-Region query. | Use Athena federation OR move the query to the EDS's Region. |
| `QueryRunTimeInSeconds > 600`, `BytesScanned` huge | No partition pruning (missing `eventTime` filter). | Add `WHERE eventTime BETWEEN timestamp1 AND timestamp2`. |
| `QueryRunTimeInSeconds > 600`, `BytesScanned` moderate | Too many columns selected (`SELECT *`). | Select only needed columns; Lake is columnar. |
| `QueryStatus: FAILED`, `AccessDenied` | Caller missing `cloudtrail:GetQuery`/`StartQuery` on EDS ARN. | Attach the IAM policy. |
| `QueryStatus: FAILED`, `KMS AccessDenied` | Caller missing `kms:Decrypt` on EDS KMS key. | Grant `kms:Decrypt` to the caller. |
| Non-AWS `PutAuditEvents` returns `AccessDenied` | Partner event source not registered, or role missing `cloudtrail:PutAuditEvents`. | Confirm Partner registration; attach IAM policy. |
| `QueryStatus: FAILED`, `JOIN across Regions` | JOIN only works same-Region. | Use Athena federation with two connector instances. |
| Athena federated query returns `AccessDenied` | Lake Formation grant missing on connector Lambda. | `aws lakeformation grant-permissions --principal <connector-lambda-role> --permissions ...`. |
| QuickSight cannot connect | QuickSight role cannot assume Athena workgroup role. | Add trust policy on the Athena workgroup role. |

### Step 2: READY — emit operation plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI
sequence and the CONFIRM gate. The plan includes:

- The exact AWS CLI command with all flags populated. For
  `start-query` this is the SQL with the EDS ARN(s).
- Expected query latency (10-30s partitioned; 5-15 min full scan).
- Expected cost ($0.005/GB scanned; partition pruning is the lever).
- The CONFIRM gate prompt.
- The monitoring step (`describe-query` poll until
  `QueryStatus: FINISHED`).

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`create-event-data-store`, `update-event-data-store`,
  `delete-event-data-store`, `start-query`, `restore-event-data-store`,
  `undelete-event-data-store`), emit: `CONFIRM: About to <operation>
  on EDS <eds-id> in account <account> region <region>. This will
  <consequence>. Proceed? (yes/no)`. Do NOT execute until the
  operator confirms.
- Capture pre-state for rollback: `aws cloudtrail get-event-data-store
  --event-data-store <id> --output json > /tmp/<id>-pre-$(date +%s).json`.
- Execute the CLI. For `start-query`, the API returns a `QueryId`
  immediately; the query runs asynchronously.
- Poll `describe-query --query-id <id>` every 10 seconds (or longer
  for big scans) until `QueryStatus` is `FINISHED`, `FAILED`, or
  `CANCELLED`.

### Step 4: Post-verification — COMPLETED

After `QueryStatus: FINISHED`, run post-verification. ALL checks
must pass for `COMPLETED`.

1. `describe-query` returns `QueryStatus: FINISHED`.
2. `ResultsCount` matches the operator's expected row count (or
   falls within a stated tolerance).
3. `QueryRunTimeInSeconds` is within the expected bound (10-30s
   partitioned; 5-15 min full scan).
4. `BytesScanned` is reasonable for the time window (e.g., a 7-day
   window on a 100 GB EDS scans ~7/90 * 100 = ~7.8 GB).
5. `get-query-results` returns rows with the expected columns.
6. For aggregation queries: spot-check 3 aggregates against raw
   rows.
7. For Athena federated queries: Athena `query-execution` returns
   `SUCCEEDED`; output location has the result object.

If ANY verification fails, emit `VERDICT: ERROR` with the failure
details — do not claim COMPLETED. Route the failure back to
diagnose-empty-query or diagnose-slow-query.

## Output format (per operation)

See § STRICT output contract above. The block MUST appear exactly in
that shape.

### Worked example — create-eds (Management + Data, SSE-KMS, org-scoped)

```text
OPERATION: create-eds
VERDICT: READY
TARGET: new EDS "org-governance-edS" (region: us-east-1,
          ingestion: Management + Data events, organization scope)
PRE_CHECKS:
  - [PASS] Caller is the management account 111111111111
  - [PASS] --retention-period 365 within [90, 3653]
  - [PASS] --kms-key-id arn:aws:kms:us-east-1:111111111111:key/edS-cmk
    exists, key policy grants cloudtrail.amazonaws.com
    kms:GenerateDataKey + kms:Decrypt
  - [PASS] AdvancedEventSelectors reference Management + Data
    categories
  - [PASS] --is-organization-service: AWS Organizations access for
    CloudTrail is enabled
  - [PASS] --termination-protection-enabled: true (default)
STEPS:
  1. CONFIRM: About to create organization-scoped Event Data Store
     "org-governance-edS" in account 111111111111 region us-east-1.
     Ingests Management + Data events for ALL accounts in org
     o-abc123def. Retention: 365 days. SSE-KMS with key edS-cmk.
     First-day ingestion: ~5-50M events depending on activity.
     Proceed? (yes/no)
  2. aws cloudtrail create-event-data-store \
       --name org-governance-edS \
       --kms-key-id arn:aws:kms:us-east-1:111111111111:key/edS-cmk \
       --retention-period 365 \
       --termination-protection-enabled \
       --is-organization-service \
       --advanced-event-selectors file:///tmp/selectors.json
  3. aws cloudtrail list-event-data-stores --name-suffix org-governance-edS
POST_VERIFY: (pending execution)
NOTES:
  - This EDS ingests Management + Data events from ALL member
    accounts in org o-abc123def. Data events for S3 dominate volume;
    tune AdvancedEventSelectors to limit to specific buckets/prefixes
    to control cost.
  - Cost estimate at 25M events/day: ~$25/day ingestion +
    ~$0.05/GB-month storage. Lake Formation grants required for any
    downstream reader.
  - The KMS key policy MUST list cloudtrail.amazonaws.com — without
    it, ingestion silently fails. Verify with
    aws kms get-key-policy --key-id edS-cmk --policy-name default.
  - This EDS is org-scoped; member accounts CANNOT create their own
    org EDS. Member-account standalone EDS for their own events is
    still allowed.
```

### Worked example — diagnose-empty-query (BLOCKED with fix)

```text
OPERATION: diagnose-empty-query
VERDICT: BLOCKED
TARGET: EDS org-governance-edS (region: us-east-1)
        (query: SELECT userIdentity.accountId, eventName, COUNT(*)
         FROM edS WHERE eventTime >= '2026-08-01' AND eventSource =
         's3.amazonaws.com' GROUP BY userIdentity.accountId, eventName)
PRE_CHECKS:
  - [PASS] EDS exists, Status: ENABLED
  - [PASS] SQL syntactically valid
  - [PASS] SQL references Lake-supported columns
  - [FAIL] EDS EventCategory list: [Management] only. The query
    filters on eventSource = 's3.amazonaws.com' for S3 data events,
    which require the Data category. Management events only include
    S3 control-plane APIs (CreateBucket, etc.), not object-level
    GetObject/PutObject.
  - [PASS] SQL includes eventTime partition filter
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
NOTES:
  - Root cause: the EDS "org-governance-edS" was created with
    EventCategory: Management only. The query expects S3 object-level
    data events (GetObject, PutObject, etc.) which require
    EventCategory: Data. The Management category only includes
    S3 control-plane events (CreateBucket, DeleteBucket, etc.).
  - Fix: update the EDS to add the Data category:
    aws cloudtrail update-event-data-store \
      --event-data-store arn:aws:cloudtrail:us-east-1:111111111111:event-data-store/eds-001 \
      --advanced-event-selectors file:///tmp/selectors-with-data.json
    New events arriving after the update will include Data events.
    Historical events before the update are NOT backfilled.
  - If you only need Management events, fix the query instead:
    drop the eventSource = 's3.amazonaws.com' filter or change it
    to target Management-only sources like
    'cloudtrail.amazonaws.com'.
```

### Worked example — federate-via-athena (COMPLETED)

```text
OPERATION: federate-via-athena
VERDICT: COMPLETED
TARGET: EDS org-governance-edS (region: us-east-1) federated via
        Athena workgroup gov-analytics
        (query: cross-account correlation of IAM API calls)
PRE_CHECKS:
  - [PASS] Athena workgroup gov-analytics exists, state ENABLED
  - [PASS] CloudTrailLake connector Lambda deployed in us-east-1
  - [PASS] Lake Formation grant: connector Lambda role has SELECT
    on the underlying EDS
  - [PASS] Athena workgroup role has cloudtrail:GetQuery,
    cloudtrail:StartQuery, cloudtrail:GetQueryResults on EDS
  - [PASS] Athena workgroup role has kms:Decrypt on edS-cmk
STEPS:
  1. CONFIRM: About to run a federated Athena query against
     org-governance-edS via the CloudTrailLake connector in
     workgroup gov-analytics. Output goes to
     s3://athena-results-111111111111/gov/. Athena + Lake scan
     costs apply. Proceed? (yes/no)
  2. aws athena start-query-execution \
       --query-string "SELECT userIdentity.accountId, eventName, eventTime FROM lambda:cloudtraillake(org-governance-edS) WHERE eventTime >= date_add('day', -7, now()) AND eventName IN ('AssumeRole','ConsoleLogin') ORDER BY eventTime DESC LIMIT 1000" \
       --work-group gov-analytics \
       --result-configuration OutputLocation=s3://athena-results-111111111111/gov/
  3. aws athena get-query-results --query-execution-id <exec-id>
POST_VERIFY:
  - [PASS] Athena QueryExecution State: SUCCEEDED
  - [PASS] Result rows: 842 (within expected 500-1500 band)
  - [PASS] Athena DataScannedInBytes: 4.2 GB (within 1-10 GB bound)
  - [PASS] Lake describe-query QueryStatus: FINISHED, BytesScanned
    3.9 GB (close to Athena DataScanned; federation overhead small)
  - [PASS] Output object exists at
    s3://athena-results-111111111111/gov/<exec-id>.csv
  - [PASS] Spot-check 3 rows: userIdentity.accountId, eventName,
    eventTime match raw Lake query
NOTES:
  - Federated query cost = Athena $5/TB * 0.0042 TB + Lake
    $0.005/GB * 3.9 GB ~= $0.02 + $0.019 = $0.04 total. Federation
    overhead is small.
  - For recurring analytics, consider materializing results to S3
    via CTAS (CREATE TABLE AS SELECT) in Athena, then point
    QuickSight at the materialized table to avoid re-scanning Lake.
  - The CloudTrailLake connector Lambda runs in the same Region as
    the EDS. For multi-Region federation, deploy connector
    instances in each Region.
```

## Anti-Patterns — NEVER

- NEVER assume CloudTrail Lake is global. Each EDS lives in a
  specific Region; cross-Region queries require Athena federation
  with the CloudTrailLake connector. Hard-coded "global" assumptions
  produce `EDS not in this Region` failures.

- NEVER run a Lake query without a `WHERE eventTime BETWEEN ...`
  filter. Lake auto-partitions on event time; without a time bound,
  every query scans every partition. Add even a wide window (last
  90 days) before narrowing.

- NEVER assume a zero-row result means the EDS is empty. The
  `EventCategory` list may not include the queried source, the
  `eventTime` window may be outside retention, or the column name
  may be wrong (`region` vs `awsRegion`). Always verify the EDS
  config before concluding emptiness.

- NEVER create an organization-scoped EDS from a member account.
  Org-scoped EDS must be created by the management account. Member
  accounts can only create standalone EDS for their own events.

- NEVER set `--retention-period` outside [90, 3653] days. Values
  below 90 or above 3653 are rejected by the API. Use
  `INDEFINITE` (literal string) for unlimited retention.

- NEVER assume `PutAuditEvents` works for any non-AWS source. Only
  registered CloudTrail Lake Partners can push non-AWS events.
  Operators cannot self-register; the Partner initiates.

- NEVER delete an EDS without first checking
  `TerminationProtectionEnabled`. If true (default for new EDS),
  the delete fails. First call `update-event-data-store
  --no-termination-protection-enabled`.

- NEVER assume Athena federation is free. A federated query incurs
  Athena scan cost ($5/TB) on top of Lake query cost ($0.005/GB).
  Federation is for convenience, not cost savings.

- NEVER SELECT * in a Lake query. Lake is columnar; selecting fewer
  columns reduces bytes scanned and cost. Always project only the
  columns needed.

- NEVER use a column name other than what Lake exposes. Common
  mistake: `region` instead of `awsRegion`, `time` instead of
  `eventTime`. Always reference the Lake schema.

- NEVER JOIN EDS across Regions via the native Lake API. JOIN is
  same-Region only. Cross-Region JOINs require Athena federation
  with multiple connector instances.

- NEVER assume Lake Formation grants are inherited. The
  CloudTrailLake connector Lambda MUST have an explicit Lake
  Formation grant on the underlying EDS. IAM alone is not
  sufficient.

- NEVER configure non-AWS ingestion without verifying Partner
  registration. `PutAuditEvents` from a non-Partner role fails
  silently in some configurations.

- NEVER auto-execute a state-changing CloudTrail Lake CLI without
  the CONFIRM gate. `delete-event-data-store` (after disabling
  termination protection) is irreversible past the 7-day recovery
  window.

- NEVER skip capturing pre-state before `update-event-data-store`.
  The prior configuration (event selectors, retention, KMS) is
  overwritten; capture for rollback.

- NEVER assume QuickSight connects to Lake directly. QuickSight
  must go through Athena. Configure the Athena workgroup first,
  then add Athena as a QuickSight data source.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation (`create-event-data-store`, `update-event-data-store`,
  `delete-event-data-store`, `start-query`,
  `restore-event-data-store`, `undelete-event-data-store`),
  emit: `CONFIRM: About to <operation> on EDS <eds-id> in account
  <account> region <region>. This will <consequence>. Proceed?
  (yes/no)`. Do NOT execute until the operator confirms.

- **Capture pre-state for rollback.** Before any EDS change:
  `aws cloudtrail get-event-data-store --event-data-store <id>
  --output json > /tmp/<id>-pre-$(date +%s).json`. This is the
  only rollback path — `update-event-data-store` overwrites
  event selectors and retention.

- **Verify KMS key policies, not just IAM.** SSE-KMS EDS require
  the key policy to grant `cloudtrail.amazonaws.com`
  `kms:GenerateDataKey`, `kms:Decrypt`. IAM alone is not
  sufficient.

- **Verify the EDS EventCategory list before queries.** A query
  against an EDS missing the relevant category returns zero rows
  without an error. Always cross-check the categories.

- **Verify organization scope.** Org-scoped EDS can only be created
  by the management account. Member-account queries against an org
  EDS require the management account's permission delegation.

- **Prefer additive changes over destructive ones.** Adding an
  EventCategory to an existing EDS is reversible; deleting an EDS
  is irreversible past 7 days.

- **Validate the SQL before `start-query`.** Run a smoke-test query
  with a tight `eventTime` window and `LIMIT 10` first; only scale
  up once the smoke test returns the expected columns.

## Expert heuristic: the partition-or-perish rule

CloudTrail Lake is a Regional columnar store with a fixed event
schema. The single highest-leverage rule for operating it safely is:

> A Lake query without a `WHERE eventTime BETWEEN ...` filter is a
> full-table scan. Always include a time bound, even a wide one.
> Partition pruning on `eventTime` is the only meaningful
> performance lever; everything else (column projection, indexes on
> `eventSource`) is secondary.

**Why this rule exists:** Lake auto-partitions on `eventTime` at
roughly hourly granularity. The query planner prunes partitions based
on the `eventTime` filter. Without a filter, every partition is
scanned. For a 100 GB EDS over 90 days, a no-filter query scans all
100 GB; a 7-day filter scans ~7.8 GB. The latency and cost
difference is 10x or more.

**Concrete verification techniques:**

| Technique | Mechanism | What it proves |
|---|---|---|
| `describe-query` `BytesScanned` vs EDS size | Compare post-query | Partition pruning worked (or didn't) |
| `QueryRunTimeInSeconds` < 60 for a 7-day window | Latency check | Partitioned query on a reasonably-sized EDS |
| `ResultsCount` matches expected row count | Cross-check against raw event volume | Query semantics correct |
| `get-query-results` first row spot-check | Manual review | Columns and values match expectation |
| Athena federated `DataScannedInBytes` close to Lake `BytesScanned` | Compare both | Federation overhead is small (Lambda marshalling) |

**Three-point verification protocol (apply on every new query):**

1. **Smoke test:** Run with a tight `eventTime` window (1 hour) and
   `LIMIT 10`. Confirm `QueryStatus: FINISHED`,
   `ResultsCount > 0`, expected columns present.
2. **Time-window scale:** Scale the `eventTime` window to the
   intended range. Confirm `BytesScanned` scales linearly (e.g., a
   7-day window scans ~7/90 of the EDS).
3. **Row-count plausibility:** Compare `ResultsCount` against the
   raw event volume estimate (e.g., for S3 GetObject on a known
   bucket, estimate from CloudWatch `NumberOfObjectsUploaded`).
   Order-of-magnitude match is the floor.

**Surface in the output:** for any query, include
`PARTITION_PRUNING: <verified | missing>` and the `BytesScanned` vs
EDS-size ratio. If `PARTITION_PRUNING` is `missing`, do NOT mark the
operation COMPLETED — recommend adding a time-bound filter first.

**Detection of slow queries post-deploy:** CloudWatch alarm on
`QueryRunTimeInSeconds > 300` for any new query in the workgroup
AND a daily Lambda that runs a 1-hour smoke test against the EDS
and confirms `QueryStatus: FINISHED` in under 60 seconds. The daily
smoke catches regression (e.g., EDS size grew, event selectors
widened).

## Recent AWS features (2024-2026)

- **Non-AWS events via Partner integrations (2023 GA, expanded
  2024-2025):** 30+ Partners (CrowdStrike, Datadog, Splunk, Wiz,
  etc.) can push non-AWS audit events into a Lake EDS via
  `PutAuditEvents`. Requires Partner registration; operators cannot
  self-register.

- **Athena CloudTrailLake connector (2023 GA, performance
  improvements 2024-2025):** Lambda-backed data source connector
  for Athena that federates Lake queries. Required for cross-account
  and cross-Region analysis. Lake Formation grant on the connector
  Lambda is mandatory.

- **NetworkActivity event category (2024):** VPC Flow Log-style
  network telemetry ingested into Lake. Requires an EDS configured
  with `EventCategory: NetworkActivity`.

- **Config configuration snapshots (2023 GA):** Bulk ingestion of
  AWS Config snapshots as Lake events. One event per resource per
  snapshot interval.

- **Audit Manager evidence ingestion (2023 GA):** Direct evidence
  flow from Audit Manager assessments into a Lake EDS. Requires
  `EventCategory: AuditManagerEvidence`.

- **CloudTrail Insights in Lake (2024):** Anomalies detected by
  CloudTrail Insights can be ingested as a separate event category
  in a Lake EDS. Most operators want a Management EDS + a separate
  Insights EDS.

- **`INDEFINITE` retention (2024):** EDS can now be configured with
  unlimited retention via the literal string `INDEFINITE` (vs the
  max 3653 days previously).

- **EDS replication (2025):** A Lake EDS can be replicated to a
  second EDS in another Region for DR or cross-Region analysis.
  Replication is async; RPO depends on event volume.

- **`undelete-event-data-store` recovery window (2024):** Deleted
  EDS can be recovered within 7 days via
  `undelete-event-data-store`. Past 7 days, gone permanently.

- **QuickSight-Athena-Lake native integration (2024-2025):**
  QuickSight can consume Athena workgroups that federate to Lake
  with one-click setup. Athena workgroup + Lake Formation grants +
  QuickSight service role trust all configured.

- **Multi-column partitioning (2025):** Lake now auto-partitions on
  `eventTime` + `eventSource` (in addition to time alone). Improves
  query latency for source-specific queries.

## Domain

AWS CloudOps / CloudTrail Lake, governance audit, multi-account
security analytics, and non-AWS event ingestion.

## AWS documentation

- **CloudTrail Lake User Guide** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake.html
- **Create an Event Data Store** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/query-event-data-store.html
- **CloudTrail Lake PartiQL queries** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/query-federation.html
- **CloudTrail Lake non-AWS events** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/query-non-aws-events.html
- **Athena CloudTrail Lake federation** — https://docs.aws.amazon.com/athena/latest/ug/cloudtrail-lake.html
- **CloudTrail Lake pricing** — https://aws.amazon.com/cloudtrail/pricing/
- **CloudTrail Lake organization ingestion** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/organization-event-data-store.html
- **CloudTrail Lake queries with JOIN** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/query-language.html
- **CloudTrail Lake KMS encryption** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/encryption-with-kms.html
- **CloudTrail API Reference** — https://docs.aws.amazon.com/awscloudtrail/latest/APIReference/Welcome.html
- **CloudTrail CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/cloudtrail/
