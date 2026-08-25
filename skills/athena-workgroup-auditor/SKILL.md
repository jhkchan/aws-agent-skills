---
name: athena-workgroup-auditor
description: Audits Amazon Athena workgroups for query-result encryption gaps (S3 + KMS), missing data-scan limits (BytesScannedCutoffPerQuery), workgroup enforcement posture (EnforceWorkGroupConfiguration — the keystone control that makes every other setting binding vs advisory), query-history retention beyond Athena's fixed 45-day API window, and named-query IAM exposure. Emits a deterministic category verdict (NO_ENCRYPTION | NO_LIMITS | CONFIG_GAP | OK) per workgroup with enumerated findings and CLI remediation. Use when reviewing Athena workgroups, checking result-encryption posture, validating per-query cost bounds, confirming client-override enforcement, auditing Athena query-history retention, or scoping named-query IAM before granting cross-team access.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline workgroup-config classification. Live-account audits use aws athena get-work-group, list-work-groups, get-named-query, and list-named-queries (AWS CLI v2, SSO or key-based credentials), plus aws cloudtrail describe-trail and get-event-selectors for the data-event coverage dimension.
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  verdict_shape: NO_ENCRYPTION | NO_LIMITS | CONFIG_GAP | OK
  when_to_use: Reviewing an Athena workgroup before production rollout, checking that query-result encryption (SSE-KMS with a CMK) is configured and enforced, validating that BytesScannedCutoffPerQuery caps runaway cost, confirming EnforceWorkGroupConfiguration is true (the keystone control), auditing long-term query history beyond Athena's fixed 45-day API window, or scoping named-query IAM to prevent SQL exfiltration via GetNamedQuery.
  activation_triggers: audit this Athena workgroup, is my Athena workgroup enforced, check Athena query result encryption, is BytesScannedCutoffPerQuery set, Athena data scan limit, primary workgroup defaults, Athena query history retention, named query IAM exposure, EnforceWorkGroupConfiguration false, Athena cost blast radius
  invocation_schema: 'Input: either (a) an Athena workgroup Configuration block (the JSON returned by aws athena get-work-group), optionally paired with the workgroup Name/State/Description and any named-query + IAM context, OR (b) a workgroup name for live-account audit. Output: deterministic WORKGROUP/VERDICT/REASON/FINDINGS/REMEDIATION block per workgroup, where VERDICT ∈ {NO_ENCRYPTION, NO_LIMITS, CONFIG_GAP, OK, ERROR}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Athena, workgroup, EnforceWorkGroupConfiguration, BytesScannedCutoffPerQuery, data scan limit, query result encryption, SSE-KMS, SSE-S3, OutputLocation, named query IAM, query history retention, CloudTrail data events, primary workgroup, AthenaSpark, cost blast radius, data exfiltration, Athena audit, workgroup remediation
  tags: athena, analytics, security, cost-control, workgroup, encryption, dsl, audit
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

Account-wide sweep pagination note and the three live-account pre-flight checks (`athena:GetWorkGroup` permission, CloudTrail Athena data-event confirmation, config snapshot before any `UpdateWorkGroup`): [Diagnostic commands](references/diagnostic-commands.md).

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
ERROR-verdict output block for a malformed Configuration block: [Error handling](references/error-handling.md).

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious Athena behaviors that change classification

All sixteen Step-0 expert behaviors — `EnforceWorkGroupConfiguration` is a binary contract, DSL counts compressed S3 bytes, DSL absent ≠ 0, `EncryptionConfiguration` covers OutputLocation writes only, SSE_S3 is still encryption, query history is a fixed 45-day window, `primary` is undeletable, named queries persist SQL in plaintext, `GetQueryResults` is a data-exfiltration vector, OutputLocation bucket-policy alignment, workgroup-to-KMS key-policy coupling, API quotas are account-region, Spark workgroups ignore the DSL, `PublishCloudWatchMetricsEnabled` is an observability note, tags do not propagate to results, deletion is a soft delete: [Advanced patterns](references/advanced-patterns.md).

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

Edge cases — partially malformed Configuration, OutputLocation absent with enforce=true, bucket-policy SSE-KMS mismatch, Spark DSL no-op, `State: DISABLED`, cross-account OutputLocation bucket, no named queries: [Advanced patterns](references/advanced-patterns.md).

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

Full per-verdict remediation playbooks with CLI (NO_ENCRYPTION, NO_LIMITS, CONFIG_GAP enforcement-off / CloudTrail data events / named-query IAM, OK): [Advanced patterns](references/advanced-patterns.md).

## Deep reference: Athena workgroup internals

Workgroup internals — evaluation order at query time (the DSL binds even when enforcement is off), workgroup vs. IAM evaluation order, `primary` lifecycle, tagging, AthenaSpark: [Advanced patterns](references/advanced-patterns.md).

## Recent AWS features (2024-2026)

Recent AWS features (capacity reservations, Spark/notebook workgroups, parameterized queries, cross-account workgroup queries): [Advanced patterns](references/advanced-patterns.md).

## References (load on demand)

- [Advanced patterns](references/advanced-patterns.md) — Step-0 expert behaviours, edge-case catalog, per-verdict remediation playbooks, workgroup-internals deep reference, recent AWS features
- [Diagnostic commands](references/diagnostic-commands.md) — account-wide sweep pagination and live-account pre-flight checks
- [Error handling](references/error-handling.md) — ERROR-verdict block for malformed workgroup Configuration JSON

## Domain

AWS CloudOps / Athena Analytics Security, Cost Control & Compliance.

## AWS documentation

- **Amazon Athena User Guide** — https://docs.aws.amazon.com/athena/latest/ug/what-is.html
- **Athena security** — https://docs.aws.amazon.com/athena/latest/ug/security.html
- **Athena API Reference** — https://docs.aws.amazon.com/athena/latest/APIReference/
- **Athena CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/athena/
- **Athena workgroups** — https://docs.aws.amazon.com/athena/latest/ug/workgroups.html
