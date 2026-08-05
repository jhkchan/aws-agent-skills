---
name: athena-workgroup-auditor
description: >-
  Audits Amazon Athena workgroups for query-result encryption gaps (S3 + KMS),
  missing data-scan limits (BytesScannedCutoffPerQuery), workgroup enforcement
  posture (EnforceWorkGroupConfiguration — the keystone control that makes
  every other setting binding vs advisory), query-history retention beyond
  Athena's fixed 45-day API window, and named-query IAM exposure. Emits a
  deterministic category verdict (NO_ENCRYPTION | NO_LIMITS | CONFIG_GAP | OK)
  per workgroup with enumerated findings and CLI remediation. Use when
  reviewing Athena workgroups, checking result-encryption posture, validating
  per-query cost bounds, confirming client-override enforcement, auditing
  Athena query-history retention, or scoping named-query IAM before granting
  cross-team access.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline workgroup-config classification.
  Live-account audits use aws athena get-work-group, list-work-groups,
  get-named-query, and list-named-queries (AWS CLI v2, SSO or key-based
  credentials), plus aws cloudtrail describe-trail and get-event-selectors
  for the data-event coverage dimension.
keywords:
  - Athena
  - workgroup
  - EnforceWorkGroupConfiguration
  - BytesScannedCutoffPerQuery
  - data scan limit
  - query result encryption
  - SSE-KMS
  - SSE-S3
  - OutputLocation
  - named query IAM
  - query history retention
  - CloudTrail data events
  - primary workgroup
  - AthenaSpark
  - cost blast radius
  - data exfiltration
  - Athena audit
  - workgroup remediation
tags: [athena, analytics, security, cost-control, workgroup, encryption, dsl, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Analytics
  verdict_shape: "NO_ENCRYPTION | NO_LIMITS | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing an Athena workgroup before production rollout, checking that
    query-result encryption (SSE-KMS with a CMK) is configured and enforced,
    validating that BytesScannedCutoffPerQuery caps runaway cost, confirming
    EnforceWorkGroupConfiguration is true (the keystone control), auditing
    long-term query history beyond Athena's fixed 45-day API window, or
    scoping named-query IAM to prevent SQL exfiltration via GetNamedQuery.
  activation_triggers:
    - "audit this Athena workgroup"
    - "is my Athena workgroup enforced"
    - "check Athena query result encryption"
    - "is BytesScannedCutoffPerQuery set"
    - "Athena data scan limit"
    - "primary workgroup defaults"
    - "Athena query history retention"
    - "named query IAM exposure"
    - "EnforceWorkGroupConfiguration false"
    - "Athena cost blast radius"
  invocation_schema: >-
    Input: either (a) an Athena workgroup Configuration block (the JSON
    returned by aws athena get-work-group), optionally paired with the
    workgroup Name/State/Description and any named-query + IAM context,
    OR (b) a workgroup name for live-account audit. Output: deterministic
    WORKGROUP/VERDICT/REASON/FINDINGS/REMEDIATION block per workgroup,
    where VERDICT ∈ {NO_ENCRYPTION, NO_LIMITS, CONFIG_GAP, OK, ERROR}.
---

# Athena Workgroup Auditor

## Mindset

**One-line takeaway:** Athena workgroups are the only native boundary
between a caller with `athena:StartQueryExecution` and an unbounded,
plaintext-result scan of your data lake. Three controls decide whether
that boundary is real or decorative — `EnforceWorkGroupConfiguration`
(the keystone), `EncryptionConfiguration` (result-set confidentiality),
and `BytesScannedCutoffPerQuery` (cost + data-volume blast radius).

A workgroup is not a security principal and not a network — it is a
configuration template applied at query time. The operator's intent is
encoded in `Configuration`; the question is whether that intent is
binding or advisory:

- **`EnforceWorkGroupConfiguration: true`** makes the workgroup's
  `ResultConfiguration` (OutputLocation, EncryptionConfiguration) and
  `BytesScannedCutoffPerQuery` authoritative — client-supplied overrides
  in `StartQueryExecution` are silently ignored. This is the only mode
  in which the workgroup acts as a real boundary.
- **`EnforceWorkGroupConfiguration: false`** (historically the default
  for the `primary` workgroup) reduces every setting below to a
  suggestion — any caller can write results to a bucket in another
  account, disable encryption, or scan unbounded bytes. Treat the
  workgroup as decorative in this state.

A workgroup with `EnforceWorkGroupConfiguration: true`, SSE-KMS with a
customer-managed key, and a sane `BytesScannedCutoffPerQuery` is OK. Any
other combination produces a category verdict describing the worst gap.

## Quick reference — verdict priority

Apply the priority in order — the first matching row is the verdict.
Where multiple findings apply, the **highest-priority category** wins
(NO_ENCRYPTION > NO_LIMITS > CONFIG_GAP > OK).

| Condition | Verdict | Rule |
|---|---|---|
| `EnforceWorkGroupConfiguration: true` AND `EncryptionConfiguration` ABSENT | **NO_ENCRYPTION** | Step 3 — definitive plaintext result objects |
| `EnforceWorkGroupConfiguration: false` AND `EncryptionConfiguration` ABSENT (any workgroup, incl. `primary`) | **NO_ENCRYPTION** | Step 3 — clients inherit no-encryption default |
| `EnforceWorkGroupConfiguration: true` AND `EncryptionConfiguration` present AND `BytesScannedCutoffPerQuery` ABSENT | **NO_LIMITS** | Step 4 — unbounded cost + data-scan blast radius |
| `EnforceWorkGroupConfiguration: false` AND (`EncryptionConfiguration` AND `BytesScannedCutoffPerQuery` both present) | **CONFIG_GAP** | Step 2 — controls present but advisory |
| `EnforceWorkGroupConfiguration: true` AND no CloudTrail Athena data-event capture | **CONFIG_GAP** | Step 5 — query history falls off the 45-day API cliff |
| Named-query IAM grants `athena:GetNamedQuery`/`StartNamedQuery` to `Principal: "*"` or cross-account | **CONFIG_GAP** | Step 6 — SQL exfiltration surface |
| All controls present, enforced, and history/IAM scoped | **OK** | Step 7 |

See the ordered steps below for edge cases (Spark workgroups, SSE-S3
acceptance, workgroup deletion mid-flight, primary-workgroup defaults).
Deep Athena internals (engine version coupling, Glue/Lake Formation
interaction, multi-region model) are in the
[Deep reference](#deep-reference-athena-workgroup-internals) section.

## Pre-flight: workgroup metadata gate (run before classification)

Several workgroup attributes **short-circuit** the audit —
misclassifying them produces false positives.

**Account-wide sweep note (pagination):** `aws athena list-work-groups`
returns at most 50 workgroups per page. Use `--next-token` from the
prior `NextToken` to page through; iterating only the first page
silently skips stale workgroups (the ones most likely to be
unenforced). For each workgroup, also page
`aws athena list-named-queries --work-group <name>` (50/page) and
`aws athena list-query-executions --work-group <name>` (50/page) —
both silently truncate.

**Live-account pre-flight checks (skip if doing offline config audit):**
1. Verify the caller can run `athena:GetWorkGroup` — read-only auditor
   roles usually can, but cross-account workgroup audits require the
   workgroup to be shared via Resource-based policy (rare). Surface
   AccessDenied BEFORE the operator approves any remediation.
2. Confirm which CloudTrail trail is capturing Athena events in the
   workgroup's region. Athena management events (`StartQueryExecution`,
   `StopQueryExecution`, `CreateNamedQuery`) are on by default; Athena
   **data events** (`BatchGetQueryExecution`, `GetQueryExecution`,
   `GetQueryResults`) must be explicitly enabled on the trail's
   `AdvancedEventSelectors`. Without data events, post-45-day forensics
   have no signal.
3. Snapshot `aws athena get-work-group --work-group <name>` BEFORE any
   `UpdateWorkGroup` call — workgroup configs are not versioned and
   there is no rollback. The CLI returns the full Configuration block;
   save it to a file for diff/recovery.

| Attribute | Value | Effect on audit |
|---|---|---|
| `Name` | `primary` | **AWS-created default workgroup.** Cannot be deleted (API returns `InvalidRequestException`). Historically created with `EnforceWorkGroupConfiguration: false`. Treat as high-priority — every principal with `athena:StartQueryExecution` + `athena:GetWorkGroup` on `primary` can run unbounded, unencrypted queries unless the field has been explicitly flipped to `true`. |
| `Name` | any user-created | Proceed with full audit. |
| `State` | `DISABLED` | Workgroup rejects all `StartQueryExecution` calls with `InvalidRequestException`. Note as operational risk (consumer outage) but skip the rest of the audit — the workgroup cannot produce live findings. |
| `Configuration.EngineVersion.SelectedEngineVersion` | `Athena engine version 3` (PySpark-compatible) | **Athena Spark / notebook workgroup.** `BytesScannedCutoffPerQuery` does NOT apply to Spark sessions — it governs interactive SQL only. Spark compute limits are governed by session Coarse/executor sizing. Do NOT flag a Spark workgroup as NO_LIMITS based on a missing DSL; flag it as CONFIG_GAP (Spark sizing not bounded) instead. |
| `Configuration.EngineVersion.SelectedEngineVersion` | `Athena engine version 3` (SQL) or `Athena engine version 2` | Standard SQL workgroup. Proceed with full audit. |
| `State` | `ENABLED` + workgroup has running `QueryExecution` states `QUEUED`/`RUNNING` | Live workgroup — findings have current blast radius. |
| `Description` | non-empty | Read but do NOT trust for classification. The description is the de-facto data-classification surface (no native tagging pre-2022); it often encodes environment (prod/dev) and data sensitivity. Use it to prioritize remediation order, not to set verdict. |

**If the workgroup Configuration JSON is malformed** (invalid JSON,
missing `ResultConfiguration`, missing `WorkGroupConfiguration`), output:

```text
WORKGROUP: <name>
VERDICT: ERROR
REASON: Workgroup Configuration block is not valid JSON or is missing required fields — cannot classify.
REMEDIATION: Retrieve the canonical config with `aws athena get-work-group --work-group <name> --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious Athena behaviors that change classification

These behaviors are easy to misjudge without operational Athena experience.
Each changes a verdict if ignored:

- **`EnforceWorkGroupConfiguration` is a binary contract, not a
  suggestion.** When `true`, client-supplied `ResultConfiguration` in
  `StartQueryExecution` (OutputLocation, EncryptionConfiguration) is
  **silently ignored** — the caller cannot widen the workgroup's
  controls. When `false`, every client override is honored, including
  setting a different OutputLocation (potentially a bucket in another
  account for exfiltration), disabling encryption, or pointing at a
  weaker KMS key. A workgroup with `EnforceWorkGroupConfiguration: false`
  is a suggestion box, not a boundary. **This is the single most
  misunderstood Athena control** and the root cause of most "Athena
  cost-surprise" incidents.

- **`BytesScannedCutoffPerQuery` counts compressed S3 bytes IN, not
  uncompressed row count.** Parquet/ORC columnar pruning can reduce a
  1 TB table scan to 50 MB for a selective query; a CSV scan of the
  same table reads the full 1 TB. A DSL tuned for Parquet (e.g., 100 GB)
  will reject legitimate CSV analytical queries. Always consider source
  format when evaluating whether a DSL value is reasonable. Absent a
  DSL, a single `SELECT *` against an S3 Inventory export can scan
  double-digit TB.

- **`BytesScannedCutoffPerQuery` ABSENT ≠ 0.** The field is optional;
  absence means "no limit." A value of `0` also blocks every query
  (every scan exceeds 0 bytes) and is a misconfiguration, distinct from
  "no limit configured." Treat ABSENT as NO_LIMITS; treat `0` as
  CONFIG_GAP (the workgroup is non-functional).

- **`EncryptionConfiguration` covers OutputLocation writes only.** It
  does NOT encrypt:
  (1) CloudTrail logs of `StartQueryExecution` (those are CloudTrail's
  responsibility); (2) the source data in S3 / Glue Data Catalog
  (separate bucket encryption); (3) `GetQueryExecution` /
  `GetQueryResults` API responses (plaintext over TLS); (4) the
  workgroup metadata itself (account-level AWS-owned key); (5) named
  queries (`GetNamedQuery` returns plaintext SQL).
  So `EncryptionConfiguration: SSE_KMS` ≠ "all Athena data is
  encrypted" — only the result-set objects in S3 are. Be precise in
  the FINDINGS text; do not overstate coverage.

- **`SSE_S3` (S3-managed key) is still encryption at rest.** It is
  acceptable for many workgroups. However, it does NOT give you a
  CloudTrail data-event trail of KMS `Decrypt` calls (there are none —
  S3 manages the key), and it does NOT let you set a per-workgroup key
  policy. For compliance frameworks that require customer-managed keys
  (HIPAA, FedRAMP, PCI-DSS in some interpretations), note SSE_S3 as a
  COMPLIANCE_NOTE — do NOT classify as NO_ENCRYPTION.

- **Query history retention is NOT a workgroup setting.** Athena's
  `GetQueryExecution` / `ListQueryExecutions` APIs return a fixed
  **45-day rolling window** with no tunable parameter. There is no
  `QueryHistoryRetentionInDays` field — operators expecting "retain 7
  years of queries" via Athena are confused. Long-term retention
  requires shipping Athena events to CloudWatch Logs / S3 via CloudTrail
  (with long retention on the destination), or a CloudTrail Lake. A
  workgroup with no CloudTrail Athena data-event capture loses all
  query history past 45 days — flag as CONFIG_GAP.

- **`primary` workgroup is undeletable.** `DeleteWorkGroup` on `primary`
  returns `InvalidRequestException`. It is created automatically in
  every account in every region where Athena is activated. Its
  historical default is `EnforceWorkGroupConfiguration: false` with no
  OutputLocation, no encryption, no DSL — an open door for any principal
  with `athena:StartQueryExecution`. Always audit `primary` first; if
  it cannot be deleted, it must be locked down (`EnforceWorkGroupConfiguration: true`
  + SSE-KMS + DSL) or quarantined via IAM (`Deny` on
  `athena:StartQueryExecution` for `aws:ResourceTag/Workgroup = primary`
  — requires workgroup tagging, available post-2022).

- **Named queries persist SQL in plaintext.** `athena:CreateNamedQuery`
  stores the SQL string in the workgroup; `athena:GetNamedQuery` returns
  it verbatim. A named query containing hardcoded identifiers, customer
  IDs, or sensitive predicates is a data leak to any principal with
  `athena:GetNamedQuery` on the workgroup ARN. Named-query SQL is NOT
  encrypted by the workgroup's `EncryptionConfiguration`. Treat any
  named query accessible to `Principal: "*"` or a cross-account
  principal as a CONFIG_GAP finding.

- **`athena:GetQueryResults` is a data-exfiltration vector.** A
  principal with `athena:StartQueryExecution` + `athena:GetQueryResults`
  on a workgroup can run `SELECT * FROM sensitive_table` and read the
  entire result set, regardless of Glue Data Catalog fine-grained
  access control. The workgroup does not enforce column-level or
  row-level filters — only Lake Formation on the source table does.
  Scope `athena:GetQueryResults` to specific workgroups and named roles.

- **OutputLocation bucket policy must be aligned with the workgroup's
  EncryptionConfiguration.** If the bucket enforces SSE-KMS via a
  bucket policy (e.g., `s3:x-amz-server-side-encryption: aws:kms`
  deny-otherwise), a workgroup with `EncryptionConfiguration: SSE_S3`
  or absent will fail query execution at result write — the bucket
  rejects the plaintext or SSE-S3 PUT. The workgroup config must match
  the bucket policy. Mismatch manifests as silent query failures
  (`State: FAILED`, `StateChangeReason: ...AccessDenied...` on the S3
  PUT), not as a security verdict — flag as CONFIG_GAP for operational
  reliability.

- **Workgroup to KMS key policy coupling for SSE-KMS.** When the
  workgroup's `EncryptionConfiguration.EncryptionOption` is `SSE_KMS`
  or `CSE_KMS`, the named `KmsKey` MUST have a key policy permitting
  both `kms:GenerateDataKey` and `kms:Decrypt` to the Athena service
  principal `athena.<region>.amazonaws.com` (and, transitively, to the
  caller's role for result-read). Without this, query execution fails
  at the first result write with `AccessDeniedException` from KMS. This
  is the most common cause of "Athena SSE-KMS queries fail day 1"
  incidents.

- **Athena API quotas are account-region, not per-workgroup.**
  `StartQueryExecution` is rate-limited to ~100 concurrent queries per
  account-region by default (adjustable via Service Quotas). A
  workgroup without a DSL can saturate this quota with a single
  runaway `SELECT *` — the blast radius includes EVERY OTHER
  workgroup in the account-region (they queue behind the runaway).
  This is why NO_LIMITS is a HIGH-severity finding: it is not just
  cost, it is a cross-workgroup availability impact.

- **Spark workgroups ignore `BytesScannedCutoffPerQuery`.** When
  `EngineVersion` indicates AthenaSpark (notebook sessions), the DSL
  field has no effect — Spark compute is bounded by executor sizing,
  not SQL byte scans. A Spark workgroup with no DSL is NOT NO_LIMITS;
  it is CONFIG_GAP ("Spark sizing not bounded"). Confirm engine type
  before applying Step 4.

- **`PublishCloudWatchMetricsEnabled: false` is an observability gap,
  not a security verdict.** Flag as a note in FINDINGS but it does not
  drive the verdict — workgroup metrics are useful for DSL tuning, not
  for the verdict categories defined here.

- **Workgroup tags (post-2022) do NOT propagate to query results.**
  Tagging the workgroup does not tag the OutputLocation S3 objects.
  Object tags require an S3 lifecycle rule or Batch Operations. ABAC
  policies conditioned on `aws:ResourceTag/Environment` on the
  OutputLocation will not match workgroup tags.

- **Workgroup deletion is a soft delete.** `DeleteWorkGroup` on a
  workgroup with running queries leaves the queries to complete — they
  are not killed. The workgroup disappears from `ListWorkGroups`
  immediately for new queries. This is an availability risk during
  cleanup: a deletion mid-batch leaves the batch running with no
  visible workgroup to manage it.

### Step 1: Pre-flight gate — primary workgroup and engine type

Apply the Pre-flight table above. If the workgroup is `primary`, flag
a PRIMARY_DEFAULT note (the workgroup is undeletable and historically
defaulted to permissive settings). If the engine is AthenaSpark, route
DSL evaluation to Step 4b (Spark sizing) instead of Step 4.

### Step 2: Enforcement gate — `EnforceWorkGroupConfiguration`

This step is the keystone. All subsequent findings depend on it.

- **`EnforceWorkGroupConfiguration: true`** → the workgroup's
  Configuration is binding. Proceed to Steps 3-6; findings reflect the
  workgroup's actual enforced posture.
- **`EnforceWorkGroupConfiguration: false`** → the workgroup's
  ResultConfiguration (encryption, OutputLocation) is advisory; the DSL
  is binding (see Deep reference — there is no per-query DSL parameter
  in `StartQueryExecution`). Two sub-cases:
  - **ResultConfiguration or DSL ABSENT** → the verdict is driven by
    that absent control, NOT by enforcement-off, because the effective
    posture is "no control + clients can widen ResultConfiguration
    further." A workgroup with enforce=false AND no encryption is
    NO_ENCRYPTION (Step 3); a workgroup with enforce=false AND no DSL
    is NO_LIMITS (Step 4). Note the enforcement gap as a compounding
    finding.
  - **ResultConfiguration AND DSL both present** → the DSL is binding
    (good), but `EncryptionConfiguration` and `OutputLocation` are
    advisory — any client can override them at query time. This is
    **CONFIG_GAP (enforcement off)** — the single most common Athena
    misconfiguration. The workgroup looks secure in `GetWorkGroup`
    output but the encryption/OutputLocation dimensions are decorative.

Do NOT skip Step 2 even when all controls are present — the
enforcement flag is the difference between a security boundary and a
documentation page.

### Step 3: Encryption evaluation

Evaluate `Configuration.ResultConfiguration.EncryptionConfiguration`:

- **`EncryptionConfiguration` ABSENT** (or `ResultConfiguration` itself
  absent) → **NO_ENCRYPTION**. Result-set objects are written to S3 as
  plaintext. Any principal with `s3:GetObject` on the OutputLocation
  prefix can read every query result, including `SELECT * FROM
  sensitive_table`. This is the highest-priority category because it
  is direct at-rest data exposure.
  - If `EnforceWorkGroupConfiguration: false`, the finding is
    compounded: clients can ALSO inject a different OutputLocation
    (cross-account exfiltration). Note this in FINDINGS.
  - If the workgroup is `primary`, this is the default-historic state —
    treat as NO_ENCRYPTION with elevated priority.

- **`EncryptionOption: SSE_S3`** → Encryption is present (S3-managed
  key). Acceptable for most workgroups. Emit a COMPLIANCE_NOTE if the
  workload is subject to a framework requiring customer-managed keys;
  do NOT classify as NO_ENCRYPTION. Continue to Step 4.

- **`EncryptionOption: SSE_KMS` with `KmsKey` set** → Customer-managed
  key encryption. Verify the KMS key policy permits Athena (see Step 0
  expert note). If the KmsKey ARN is an AWS-managed key (`aws/s3`), it
  is functionally equivalent to SSE_S3 for compliance — emit a
  COMPLIANCE_NOTE. Otherwise, encryption dimension is OK.

- **`EncryptionOption: CSE_KMS`** → Client-side encryption (rare).
  Encryption is present. Note that CSE_KMS requires client libraries
  and is not transparent to Athena engine — flag as COMPLIANCE_NOTE
  for compatibility.

### Step 4: Data-scan limit evaluation (SQL workgroups)

**Step 4a: SQL workgroups (engine is not AthenaSpark).** Evaluate
`Configuration.BytesScannedCutoffPerQuery`:

- **Field ABSENT** → **NO_LIMITS**. No per-query byte cap. A single
  `SELECT *` can scan the entire S3 backing of the largest Glue table
  in the account — common runaway queries hit double-digit TB at
  triple-digit USD per execution. This is HIGH-severity because (1) it
  is uncapped cost, (2) it can saturate the account-region
  StartQueryExecution quota and queue every other workgroup's queries.
  - If `EnforceWorkGroupConfiguration: false`, the finding is
    compounded: even a client-respected DSL would be advisory.

- **Field present and > 0** → DSL exists. Sanity-check the value:
  - `< 1073741824` (< 1 GB) → likely too tight; legitimate analytical
    queries will fail with `QueryExceedsBytesScannedLimit`. Emit a
    CONFIG_NOTE (operational, not a verdict driver).
  - `1073741824 - 1099511627776` (1 GB - 1 TB) → reasonable range for
    most analytical SQL on Parquet.
  - `> 1099511627776` (> 1 TB) → generous; legitimate for heavy CSV
    analytical workloads but flag as a COST_NOTE.
  - `> 9007199254740992` (> 8 PB, approaching Long.MAX_VALUE) →
    effectively absent; the DSL was set to "disable" via a huge value.
    Treat as NO_LIMITS (the operator has defeated the cap).

- **Field present and `== 0`** → CONFIG_GAP. Every query exceeds 0
  bytes; the workgroup is non-functional. The operator has mis-set the
  value; remediation is to set a real DSL or remove the field.

**Step 4b: Spark workgroups (engine is AthenaSpark).**
`BytesScannedCutoffPerQuery` does NOT apply. Skip Step 4a. Instead,
note Spark sizing as a separate dimension: if the workgroup has no
executor sizing constraints (no `AdditionalArtifacts` /
notebook-session sizing), flag as CONFIG_GAP ("Spark sizing not
bounded"). Otherwise OK on this dimension.

### Step 5: Query history retention evaluation

Athena's `GetQueryExecution` / `ListQueryExecutions` APIs return a
fixed **45-day rolling window**. There is no workgroup setting to
extend this. Long-term query history requires shipping Athena events
out of Athena via CloudTrail.

Evaluate the CloudTrail data-event coverage for the workgroup's region:

- **CloudTrail trail exists with Athena data events enabled** →
  query history is captured beyond 45 days (trail retention governs
  the horizon). OK on this dimension.
- **CloudTrail trail exists but Athena data events NOT enabled**
  (only management events) → only `StartQueryExecution`,
  `CreateNamedQuery`, `UpdateWorkGroup` etc. are captured (which
  include the SQL in `requestParameters.QueryString` for management
  events — usually sufficient). Emit a HISTORY_NOTE that
  `GetQueryResults` data events are not captured (forensics for
  result-set reads are absent). Not a verdict driver by itself.
- **No CloudTrail trail in the workgroup's region** → **CONFIG_GAP**.
  Query history past 45 days is gone. For regulated workloads, this is
  a finding driver if no other dimension produces a higher-priority
  verdict.

### Step 6: Named-query IAM evaluation

For each named query in the workgroup (via
`aws athena list-named-queries --work-group <name>` →
`aws athena get-named-query --named-query-id <id>`), evaluate the IAM
grants on the workgroup ARN:

- **Any identity-based or resource-based policy grants
  `athena:GetNamedQuery` or `athena:StartNamedQuery` to
  `Principal: "*"`** → **CONFIG_GAP**. The named query's SQL is
  readable by any AWS account principal (subject to their identity
  policy). If the SQL contains hardcoded identifiers, customer IDs, or
  sensitive predicates, it is a data leak.
- **Cross-account grant of `athena:GetNamedQuery`** (any principal ARN
  whose 12-digit account ID differs from the workgroup's account) →
  **CONFIG_GAP**. External account can read the SQL.
- **Same-account grant of `athena:GetNamedQuery` to a broad role**
  (e.g., `arn:aws:iam::ACCOUNT:role/*`) → HISTORY_NOTE (broad but
  in-account; not a verdict driver unless SQL contains secrets).
- **Named queries scoped to specific role ARNs** → OK on this dimension.

For live-account audits, enumerate named queries via the API; for
offline audits, accept a list of `(NamedQueryId, NamedQuerySql,
IamGrants)` tuples as input.

### Step 7: Aggregation — worst verdict wins

The final verdict is the **highest-priority category** across all
findings, where NO_ENCRYPTION > NO_LIMITS > CONFIG_GAP > OK:

```text
verdict = max_priority(encryption_finding, dsl_finding, enforcement_finding,
                       history_finding, named_query_iam_finding)
```

If no findings (all dimensions OK), the verdict is **OK**.

## Output format (per workgroup)

```text
WORKGROUP: <name>
VERDICT: NO_ENCRYPTION | NO_LIMITS | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
FINDINGS:
  - [NO_ENCRYPTION] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — primary workgroup, all controls missing

```text
WORKGROUP: primary
VERDICT: NO_ENCRYPTION
REASON: primary workgroup (undeletable) has EnforceWorkGroupConfiguration false
and no EncryptionConfiguration — every caller inherits plaintext result writes
and can override to widen exposure (Step 3). No DSL compounds the cost blast.
FINDINGS:
  - [NO_ENCRYPTION] EncryptionConfiguration absent; result objects written to S3 as plaintext (Step 3)
  - [NO_LIMITS] BytesScannedCutoffPerQuery absent; single query can scan unbounded S3 bytes (Step 4)
  - [CONFIG_GAP] EnforceWorkGroupConfiguration false — all controls advisory (Step 2)
  - [PRIMARY_DEFAULT] Workgroup is 'primary' — undeletable; must be locked down or IAM-quarantined (Step 1)
REMEDIATION:
  1. Set EnforceWorkGroupConfiguration: true via UpdateWorkGroup (Step 2 remediation).
  2. Configure ResultConfiguration.EncryptionConfiguration with SSE_KMS + a CMK ARN.
  3. Set BytesScannedCutoffPerQuery to a sane value (start with 1099511627776 = 1 TB; tune down).
  4. If the primary workgroup is not used, add an IAM Deny on athena:StartQueryExecution for the primary ARN.
```

## Edge-case handling

- **Partially malformed Configuration.** If the Configuration JSON parses
  but individual fields are missing (`ResultConfiguration`,
  `WorkGroupConfiguration`), classify each present dimension normally
  and emit an ERROR note for each malformed sub-block. Do NOT classify
  the entire workgroup as ERROR when only one sub-block is broken.

- **Workgroup with `ResultConfiguration.OutputLocation` absent but
  `EnforceWorkGroupConfiguration: true`.** Athena requires an
  OutputLocation to write results; if absent AND enforce=true, queries
  fail with `InvalidRequestException`. This is an operational config
  error — emit CONFIG_GAP (workgroup is non-functional), not
  NO_ENCRYPTION.

- **OutputLocation bucket enforces SSE-KMS via bucket policy, workgroup
  has SSE_S3 or absent encryption.** Queries fail at result-write time
  with `State: FAILED`, `StateChangeReason: ...AccessDenied...`. This
  is a CONFIG_GAP (operational mismatch), not NO_ENCRYPTION — the
  bucket policy is enforcing encryption; the workgroup is just
  misconfigured to mismatch it.

- **Spark workgroup with BytesScannedCutoffPerQuery set.** The DSL is a
  no-op for Spark sessions. Do NOT classify as OK on the limits
  dimension based on a set DSL — instead emit CONFIG_GAP ("DSL is
  ineffective for Spark engine; bound Spark sizing instead").

- **Workgroup `State: DISABLED` with controls absent.** The workgroup
  cannot run queries — the absent controls have no live blast radius.
  Emit VERDICT: OK with a STATE_NOTE: "Workgroup is DISABLED —
  findings inactive until re-enabled." Do not produce a NO_ENCRYPTION
  or NO_LIMITS verdict for a workgroup that cannot execute queries.

- **OutputLocation is a cross-account bucket.** The workgroup writes
  results to a bucket in another AWS account. Flag as CONFIG_GAP
  (results are outside the workgroup owner's control — the bucket
  owner can read, modify, or delete them; the workgroup's
  EncryptionConfiguration is still applied but the bucket policy
  governs access).

- **Workgroup with no named queries.** Step 6 returns no findings — the
  named-query dimension is OK by absence. Do not emit CONFIG_GAP for
  "no named queries" — it is a healthy state.

## Anti-Patterns — NEVER

- NEVER classify a workgroup with `EncryptionOption: SSE_S3` as
  NO_ENCRYPTION. SSE_S3 is encryption at rest (S3-managed key). It is
  acceptable for most workloads. Confusing SSE_S3 with "no encryption"
  produces false positives and erodes trust in the audit. The
  NO_ENCRYPTION verdict is reserved for ABSENT EncryptionConfiguration
  (or `ResultConfiguration` absent).

- NEVER evaluate `BytesScannedCutoffPerQuery` without first checking
  `EnforceWorkGroupConfiguration`. A DSL of 1 TB on a workgroup with
  enforcement OFF is decorative — every client can override it. The
  finding is CONFIG_GAP (enforcement off), not "DSL is set, OK on
  limits."

- NEVER flag a Spark workgroup as NO_LIMITS based on a missing
  BytesScannedCutoffPerQuery. The DSL field does not apply to Spark
  sessions — flag as CONFIG_GAP (Spark sizing not bounded) instead.
  Confirm `EngineVersion` is SQL before applying Step 4a.

- NEVER treat Athena's 45-day `GetQueryExecution` window as a tunable
  workgroup setting. It is a fixed service-side retention. There is no
  `QueryHistoryRetentionInDays` field. Operators asking to "extend
  Athena query history" must be routed to CloudTrail data events /
  CloudTrail Lake — not to a workgroup config change.

- NEVER recommend deleting the `primary` workgroup as remediation.
  `DeleteWorkGroup` on `primary` returns `InvalidRequestException`. The
  primary workgroup is undeletable — remediation is either lock it
  down (`EnforceWorkGroupConfiguration: true` + SSE-KMS + DSL) or
  IAM-quarantine it (Deny `athena:StartQueryExecution` on the primary
  ARN).

- NEVER assume `EnforceWorkGroupConfiguration: true` prevents the
  client from setting a different `ResultConfiguration` in
  `StartQueryExecution`. It does — the override is silently ignored —
  but the inverse (assuming enforcement=false is fine because "clients
  follow convention") is the single most common Athena incident
  pattern. Treat enforcement=false as a finding.

- NEVER conflate `EncryptionConfiguration` on result objects with
  source-data encryption. The workgroup's EncryptionConfiguration
  covers ONLY the OutputLocation writes. Source S3 bucket encryption,
  Glue Data Catalog encryption, and KMS key policies on the source are
  separate audits. State the scope precisely in FINDINGS.

- NEVER overlook named-query SQL as a leak surface. Named queries are
  plaintext in `GetNamedQuery` responses; they are NOT encrypted by
  the workgroup's EncryptionConfiguration. A named query containing
  hardcoded customer IDs or sensitive predicates is a leak to any
  principal with `athena:GetNamedQuery` on the workgroup ARN.

- NEVER treat `BytesScannedCutoffPerQuery: 0` as "no limit." Zero
  blocks every query (every scan exceeds 0 bytes). The workgroup is
  non-functional — CONFIG_GAP. The "no limit" state is field ABSENT.

- NEVER treat a `BytesScannedCutoffPerQuery` value near Long.MAX_VALUE
  (e.g., 9223372036854775807) as "DSL is set." Values that large are
  the operator's way of defeating the cap — effectively NO_LIMITS.

- NEVER assume OutputLocation bucket policy aligns with the workgroup's
  EncryptionConfiguration. A bucket enforcing SSE-KMS will reject
  workgroup writes configured for SSE_S3 or plaintext — manifesting as
  silent query failures. Always cross-reference the bucket policy in
  the operational remediation guidance.

- NEVER scope `athena:GetQueryResults` to `Resource: "*"` in IAM. It is
  a data-exfiltration vector equivalent to `s3:GetObject` on the result
  prefix — a principal with `athena:StartQueryExecution` +
  `athena:GetQueryResults` on a workgroup can read entire sensitive
  tables via `SELECT *`. Scope to specific workgroup ARNs.

- NEVER recommend `CSE_KMS` as a remediation. It requires client-side
  libraries and breaks Athena engine integration for most workloads.
  Prefer `SSE_KMS` with a customer-managed key — same compliance
  posture, transparent to the engine.

- NEVER classify a `State: DISABLED` workgroup as NO_ENCRYPTION or
  NO_LIMITS based on absent controls. A disabled workgroup cannot run
  queries — the findings are inactive. Emit VERDICT: OK with a
  STATE_NOTE so the operator knows to re-audit if re-enabled.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`UpdateWorkGroup`, `DeleteWorkGroup`, `CreateNamedQuery`,
  `PutResourcePolicy`), the auditor MUST emit:
  `CONFIRM: About to <action> on workgroup <name> in account <account>,
  region <region>. This affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms. This gate
  prevents automated pipelines from silently modifying Athena workgroups
  mid-batch.
- **`UpdateWorkGroup` is unversioned.** There is no rollback — the prior
  Configuration is irretrievable unless the operator snapshotted it.
  BEFORE any UpdateWorkGroup, capture:
  `aws athena get-work-group --work-group <name> --output json >
  /tmp/<name>-backup-$(date +%s).json`
- **Flipping `EnforceWorkGroupConfiguration` from false to true is a
  breaking change for clients relying on per-query overrides.** Any
  client passing a custom `ResultConfiguration` in `StartQueryExecution`
  will have that override silently ignored post-flip. Surface this
  before the operator approves — query pipelines may fail with
  unexpected OutputLocation or encryption behavior.
- **Setting `BytesScannedCutoffPerQuery` too low breaks legitimate
  analytical queries.** Start with a generous value (1 TB =
  1099511627776 bytes) and tune down based on observed query
  statistics (`aws athena get-query-execution` Statistics).
- **Verify the KMS key exists and is enabled before pointing SSE_KMS at
  it.** `aws kms describe-key --key-id <id>` — fail closed (skip
  remediation) if the key is Disabled or PendingDeletion.
- **For SSE-KMS, verify the key policy permits Athena.** The key policy
  must allow `kms:GenerateDataKey` and `kms:Decrypt` to
  `athena.<region>.amazonaws.com` (and to the caller's role for
  result-read). Without this, queries will fail at result write.
- **Prefer additive changes over destructive ones.** Add a
  `BytesScannedCutoffPerQuery` (new field) BEFORE removing an
  OutputLocation override; flip `EnforceWorkGroupConfiguration` to true
  BEFORE deleting the `primary` workgroup's IAM grants.
- **For `primary` workgroup remediation**, prefer IAM-quarantine
  (`Deny athena:StartQueryExecution` on the primary ARN) over
  configuration change — primary is shared infrastructure and other
  teams may have undocumented dependencies.

## Remediation guidance

**Ordering principle:** always prefer additive changes (add a DSL,
add an EncryptionConfiguration, add an IAM Deny) over destructive
changes (remove a statement, delete a named query). Additive changes
are reversible and do not risk breaking existing query pipelines.

### For NO_ENCRYPTION — EncryptionConfiguration absent

1. Identify the OutputLocation bucket. If absent, set one:
   `aws athena update-work-group --work-group <name>
   --configuration-updates ResultConfigurationUpdates={
   OutputLocation=s3://athena-results-<account>-<region>/}`
2. Create or identify a customer-managed KMS key in the workgroup's
   region. Verify the key policy grants `kms:GenerateDataKey` +
   `kms:Decrypt` to `athena.<region>.amazonaws.com`.
3. Enable SSE-KMS on the workgroup:
   `aws athena update-work-group --work-group <name>
   --configuration-updates ResultConfigurationUpdates={
   EncryptionConfiguration={EncryptionOption=SSE_KMS,
   KmsKey=arn:aws:kms:<region>:<account>:key/<id>}}`
4. Verify with `aws athena get-work-group --work-group <name>` —
   confirm `EncryptionConfiguration` is present.
5. If `EnforceWorkGroupConfiguration` is false, also flip it to true
   (see CONFIG_GAP enforcement remediation).
6. Re-encrypt or rotate any plaintext result objects already in the
   OutputLocation prefix from the exposure window — they remain
   readable to anyone with `s3:GetObject`.

### For NO_LIMITS — BytesScannedCutoffPerQuery absent

1. Inspect recent query statistics to calibrate the DSL:
   `aws athena list-query-executions --work-group <name>` → for each,
   `aws athena get-query-execution --query-execution-id <id>` →
   read `Statistics.DataScannedInBytes`.
2. Set the DSL to the 95th-percentile of recent scans, with a
   safety margin. For Parquet-backed analytical SQL, start at 1 TB
   (1099511627776 bytes); for CSV-backed, start at 100 GB
   (107374182400 bytes). Adjust down over time.
3. Apply:
   `aws athena update-work-group --work-group <name>
   --configuration-updates BytesScannedCutoffPerQuery=1099511627776`
4. Verify with `aws athena get-work-group` and confirm queries that
   would exceed the DSL now fail fast with
   `QueryExceedsBytesScannedLimit` (State: FAILED).
5. Consider CloudWatch alarm on `Microsoft.Athena` /
   `ProcessedBytes` metric to alert on queries approaching the DSL.

### For CONFIG_GAP — EnforceWorkGroupConfiguration false

1. **Before flipping**, enumerate every client pipeline that calls
   `StartQueryExecution` against this workgroup and check whether any
   passes a custom `ResultConfiguration`. Those callers will break
   silently post-flip — their overrides will be ignored.
2. Snapshot the current workgroup config (see Pre-flight safety).
3. Flip:
   `aws athena update-work-group --work-group <name>
   --configuration-updates EnforceWorkGroupConfiguration=true`
4. Verify with `aws athena get-work-group` — confirm the field reads
   `true`.
5. Monitor CloudTrail `StartQueryExecution` events for 1-2 weeks for
   `StateChangeReason` indicating config-override failures. Fix the
   client pipelines to rely on the workgroup's enforced config.

### For CONFIG_GAP — no CloudTrail Athena data events

1. Identify the CloudTrail trail capturing the workgroup's region
   (`aws cloudtrail describe-trails`).
2. Update the trail's `EventSelectors` or `AdvancedEventSelectors` to
   include Athena data events:
   `aws cloudtrail put-event-selectors --trail-name <trail>
   --event-selectors '[{...includeManagementEvents=true,
   ReadWriteTypeType=All, DataResources=[{Type="AWS::Athena::Workgroup",
   Values=["arn:aws:athena:<region>:<account>:workgroup/<name>"]}]}]'`
   For org trails, apply at the org level.
3. Verify with `aws cloudtrail get-event-selectors --trail-name <trail>`
   and confirm Athena data resources appear.
4. Set the trail's S3 destination bucket lifecycle to retain logs for
   the compliance horizon (e.g., 2555 days for 7-year retention).
5. For SQL-level query text retention past 45 days, also consider a
   CloudTrail Lake that includes `aws.athena` event sources.

### For CONFIG_GAP — named query IAM over-permissive

1. Identify the named queries:
   `aws athena list-named-queries --work-group <name>` → for each,
   `aws athena get-named-query --named-query-id <id>`.
2. For each named query containing sensitive SQL, scope the IAM grant
   to specific role ARNs:
   ```json
   {
     "Effect": "Allow",
     "Action": ["athena:GetNamedQuery", "athena:StartNamedQuery"],
     "Resource": "arn:aws:athena:<region>:<account>:workgroup/<name>",
     "Condition": {
       "StringEquals": {
         "aws:PrincipalArn": "arn:aws:iam::<account>:role/<specific-role>"
       }
     }
   }
   ```
3. Remove any `Principal: "*"` or cross-account grants on the
   workgroup ARN.
4. If the named query contains hardcoded identifiers, rotate them
   (assume leak during the exposure window) and replace with
   parameterized SQL via `athena:StartQueryExecution` with
   `ExecutionParameters` (Athena engine v3).

### For OK

1. No remediation required for the current posture.
2. Recommend verifying the KMS key policy still permits Athena
   (defense-in-depth — key policies drift).
3. Recommend verifying the OutputLocation bucket policy aligns with
   the workgroup's EncryptionConfiguration (operational reliability).
4. Recommend a periodic re-audit cadence (workgroup configs drift via
   `UpdateWorkGroup` from operators outside the security team).

## Deep reference: Athena workgroup internals

### Workgroup evaluation at query time

When a caller invokes `StartQueryExecution` with a `WorkGroup` and a
client-side `ResultConfiguration`, Athena evaluates the workgroup's
config in this order:

1. **`State`** — if `DISABLED`, reject with `InvalidRequestException`.
2. **`EnforceWorkGroupConfiguration`** — if `true`, ignore the
   client-supplied `ResultConfiguration` entirely; use the workgroup's
   `Configuration.ResultConfiguration`. If `false`, the client's
   `ResultConfiguration` (if present) overrides; fall back to the
   workgroup's config if the client omits a field.
3. **`BytesScannedCutoffPerQuery`** — applied regardless of the
   enforcement flag. The `StartQueryExecution` API has NO parameter
   for a per-query DSL override, so the workgroup's value is binding
   even when `EnforceWorkGroupConfiguration: false`. This is the one
   control that cannot be client-overridden via the query API. (Note:
   this is asymmetric with `ResultConfiguration`, which IS
   client-overridable when enforcement is off.)
4. **Engine routing** — if the workgroup engine is AthenaSpark, route
   to the Spark runtime (the DSL is ignored).

The implication for classification: **the DSL is the one control that
is binding even with `EnforceWorkGroupConfiguration: false`.** Update
Step 4 accordingly — a workgroup with enforcement=false BUT a DSL set
still has a binding DSL. However, encryption and OutputLocation remain
advisory. This does not change the verdict categories, but it does
change the FINDINGS text: do not say "DSL is advisory" — say "DSL is
binding but encryption/OutputLocation are advisory."

### Workgroup vs. IAM evaluation order

Effective permissions for an Athena query are computed as:

1. **Organizations SCP** — sets the maximum permissions.
2. **IAM identity-based policy** — must allow `athena:StartQueryExecution`
   + `athena:GetWorkGroup` on the workgroup ARN (+ optionally
   `athena:GetQueryResults`).
3. **Resource-based policy on the workgroup** (via
   `aws athena put-resource-policy`) — for cross-account workgroup
   sharing (rare). Both identity-based AND resource-based must allow.
4. **Workgroup Configuration** — applied at query time (the
   enforcement gate described above). This is NOT an IAM evaluation;
   it is a service-side configuration applied after IAM authorizes.
5. **Lake Formation** (on source Glue tables) — the only native
   row/column-level filter. The workgroup does NOT enforce
   column-level or row-level filters.

A caller authorized by IAM to run a query is NOT authorized to read
the source table unless Lake Formation (or Glue Data Catalog
fine-grained access) also permits. The workgroup cannot substitute
for Lake Formation — it governs result writes, not source reads.

### `primary` workgroup lifecycle

The `primary` workgroup is auto-created in every account-region where
Athena is activated. It cannot be deleted (`DeleteWorkGroup` returns
`InvalidRequestException` with `"Cannot delete workgroup primary"`).
Historical defaults (pre-2022):

- `EnforceWorkGroupConfiguration: false`
- No `ResultConfiguration.OutputLocation`
- No `EncryptionConfiguration`
- No `BytesScannedCutoffPerQuery`

Newer accounts (post-2022) may have `EnforceWorkGroupConfiguration: true`
with an auto-populated OutputLocation (`s3://aws-athena-query-results-<account>-<region>/`)
— but this is not guaranteed across all regions and partitions. Always
audit `primary` explicitly; do not assume defaults.

### Workgroup tagging (post-2022)

Workgroup tagging (`TagResource`, `UntagResource`, `ListTagsForResource`)
was added in 2022. Tags do NOT propagate to query results — the S3
objects in OutputLocation are tagged only by bucket lifecycle policy
or S3 Batch Operations. ABAC policies conditioned on
`aws:ResourceTag/Environment` on the OutputLocation will not match
workgroup tags.

### AthenaSpark workgroups

When `EngineVersion.SelectedEngineVersion` is `Athena Spark` (or the
workgroup has `AdditionalArtifacts` indicating notebook sessions),
the workgroup governs Spark compute sessions, not interactive SQL.
The `BytesScannedCutoffPerQuery` field has no effect. Spark sizing
is governed by session executor configuration, not by workgroup
Configuration. Treat Spark workgroups as a separate audit surface
(the verdict categories still apply, but the DSL evaluation is
skipped in favor of Spark sizing checks).

## Domain

AWS CloudOps / Athena Analytics Security, Cost Control & Compliance.
