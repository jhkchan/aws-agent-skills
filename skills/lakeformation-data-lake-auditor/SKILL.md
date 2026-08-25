---
name: lakeformation-data-lake-auditor
description: Audits AWS Lake Formation data-lake posture for catalog-level super-grants, cross-account principals, ColumnWildcard SELECT without DataCellsFilter, WithGrantablePermissions delegation chains, grants on unregistered S3 locations, data-lake admin composition, IAMAllowedPrincipals mixed-mode databases, and sensitive-table cell-filter wiring. Emits a deterministic verdict (OVERPERMISSIVE_GRANT | EXTERNAL_ACCOUNT | CONFIG_GAP | OK) per data lake with enumerated findings and CLI remediation. Use when reviewing Lake Formation permissions, auditing LF-tag policies, checking cross-account data shares, validating cell-level filtering, or hardening data-lake posture before production deployment.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline grant-document classification. Live-account audits use aws lakeformation list-permissions, list-resources, get-data-lake-settings, list-data-cells-filter, and describe-organization (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  verdict_shape: OVERPERMISSIVE_GRANT | EXTERNAL_ACCOUNT | CONFIG_GAP | OK
  when_to_use: Reviewing Lake Formation permissions before production deployment, auditing a data lake for cross-account sharing, checking whether ColumnWildcard SELECT grants are backed by a DataCellsFilter, validating that grants target registered S3 locations, reviewing the DataLakeAdmins break-glass list, or diagnosing IAMAllowedPrincipals mixed-mode leakage.
  activation_triggers: audit this Lake Formation data lake, check LF permissions, is my data lake shared cross-account, audit Lake Formation grants, column wildcard SELECT exposure, is my DataCellsFilter wired, IAMAllowedPrincipals mixed mode, data lake admin list review, WithGrantablePermissions delegation, registered location gap, hardening Lake Formation
  invocation_schema: 'Input: either (a) a Lake Formation grant/permission JSON document (list-permissions output) paired with list-resources and get-data-lake-settings metadata, OR (b) a catalog/account id for live-account audit. Output: deterministic LAKE/VERDICT/REASON/FINDINGS/ REMEDIATION block per data lake, where VERDICT is in {OVERPERMISSIVE_GRANT, EXTERNAL_ACCOUNT, CONFIG_GAP, OK, ERROR}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Lake Formation, data lake, LF-tag, LF permissions, ColumnWildcard, DataCellsFilter, IAMAllowedPrincipals, DataLakeAdmins, WithGrantablePermissions, cross-account data share, Resource Link, registered location, cell-level filter, Glue Data Catalog, ABAC, row-level security, data lake audit, Lake Formation quota
  tags: lakeformation, analytics, security, data-lake, lf-tag, abac, cross-account, cell-filter, audit
---

# Lake Formation Data Lake Auditor

## Mindset

**One-line takeaway:** Lake Formation permissions are ADDITIVE — there is no
Deny — so every grant is permanent until revoked, and three patterns dominate
the worst findings: `Permission: ALL` on `Catalog` (data-lake admin via
grant), `ColumnWildcard` SELECT without a wired `DataCellsFilter`, and
`IAMAllowedPrincipals` silently disabling LF on a mixed-mode database.

Lake Formation is the authorisation layer ABOVE IAM for data-lake tables in
the Glue Data Catalog. Once a resource is registered to LF, IAM alone is NOT
sufficient — LF must also grant. Three behaviours break the natural mental
model:

- **No Deny exists.** You can only refrain from granting or call
  `RevokePermissions`. A "least-privilege boundary" is enforced by *not
  granting* — you cannot layer a Deny on top of an over-broad Allow.
- **Admins bypass grants.** `DataLakeAdmins` from `get-data-lake-settings`
  are SUPER-USERS, NOT subject to LF grants. Listing a role here = full
  data-lake admin, equivalent to a Catalog `ALL` grant at a different layer.
- **IAMAllowedPrincipals opts out of LF.** A grant to
  `Principal: {"DataLakePrincipalIdentifier": "IAMAllowedPrincipals"}`
  delegates the resource to IAM policy — LF grants on the same resource may
  or may not apply depending on hybrid mode.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| `Permissions: ["ALL"]` on `Resource: {Catalog: {}}` to non-admin principal | **OVERPERMISSIVE_GRANT** | 1 |
| `WithGrantablePermissions` non-empty on Catalog/DB/Table to non-admin | **OVERPERMISSIVE_GRANT** | 1 |
| Principal `DataLakePrincipalIdentifier` from a different AWS account | **EXTERNAL_ACCOUNT** | 2 |
| `Permissions: ["ALL"]` on Database or Table to non-admin | **OVERPERMISSIVE_GRANT** | 3 |
| SELECT on `Table` resource (not `TableWithColumns`) to non-admin | **OVERPERMISSIVE_GRANT** | 3 |
| SELECT on `TableWithColumns` with `ColumnWildcard: {}` | **OVERPERMISSIVE_GRANT** | 3 |
| `DROP` or `ALTER` on production Database/Table to non-admin | **OVERPERMISSIVE_GRANT** | 3 |
| Grant on a Table whose S3 path is NOT under any registered location | **CONFIG_GAP** | 5 |
| Registered location's `RoleArn` is deleted or broken | **CONFIG_GAP** | 5 |
| `DataLakeAdmins` is empty | **CONFIG_GAP** | 6 |
| `DataLakeAdmins` contains an external-account principal | **EXTERNAL_ACCOUNT** | 6 |
| Sensitive (PII-tagged) table has no wired `DataCellsFilter` | **CONFIG_GAP** | 7 |
| DB has `IAMAllowedPrincipals` grant AND explicit LF grants on its tables | **CONFIG_GAP** | 8 |
| Named perms on named TableWithColumns, scoped same-account principal, filter wired | **OK** | 9 |

Precedence (worst finding wins): **OVERPERMISSIVE_GRANT > EXTERNAL_ACCOUNT > CONFIG_GAP > OK**.

## Pre-flight: data-lake state gate

Before evaluating individual grants, classify the data lake's global state.
Several account-level attributes short-circuit the audit.

**Live-account sweep (pagination):** `aws lakeformation list-permissions`
returns at most 100 grants per page — always drain `NextToken`. `list-resources`
and `list-data-cells-filter` also paginate. A common mistake is auditing only
the first page and missing the long tail of stale grants on decommissioned
tables (the ones most likely to be over-broad).

**Live pre-flight checks (skip for offline grant-doc audit):**

1. Verify LF is enabled via `aws lakeformation describe-organization` (or
   `get-data-lake-principals`). If LF is NOT enabled, every grant is a no-op
   — IAM is the sole authority. Flag as CONFIG_GAP and DO NOT score grant
   over-permissiveness (the grants enforce nothing).
2. Capture `aws lakeformation get-data-lake-settings` BEFORE any change —
   it returns `DataLakeAdmins`, `CreateDatabaseDefaultPermissions`,
   `CreateTableDefaultPermissions`, and `TrustedResourceOwners`.
3. Snapshot `aws lakeformation list-permissions --output json` (paged) —
   LF grants have NO version history; `RevokePermissions` is irreversible
   without a backup.
4. Confirm `aws lakeformation list-resources` returns at least one entry.
   An account with grants but ZERO registered locations is broken — grants
   cannot enforce.

| Attribute | Effect on audit |
|---|---|
| LF not enabled (`describe-organization`) | All grants are no-ops. Emit CONFIG_GAP. Do NOT score grant severity. |
| `DataLakeAdmins: []` | No break-glass admin. CONFIG_GAP. |
| `DataLakeAdmins` contains external-account ARN | EXTERNAL_ACCOUNT and OVERPERMISSIVE_GRANT. |
| `CreateDatabaseDefaultPermissions` grants ALL to `IAMAllowedPrincipals` | New DBs default to IAM-only mode. Note for every DB audit (Step 8). |
| `list-resources` empty | No S3 locations registered. CONFIG_GAP. |
| Hybrid access mode enabled on catalog/table | LF and IAM BOTH evaluate — EITHER allowing grants access. Audit both layers. |

If the grant JSON is malformed (invalid JSON, missing `Principal`,
`Permissions`, or `Resource`), output:

```text
LAKE: <catalog-id or principal-id>
VERDICT: ERROR
REASON: Grant document is not valid JSON or is missing required fields (Principal, Permissions, Resource) — cannot classify.
REMEDIATION: Retrieve canonical grants with `aws lakeformation list-permissions --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious Lake Formation behaviours that change classification

The non-obvious LF behaviours (no Deny, IAMAllowedPrincipals, ALL, WithGrantablePermissions,
ColumnWildcard, quotas, hybrid mode, Glue-vs-LF surfaces) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

### Step 1: Catalog-level super grants (highest priority — admin escalation)

For each grant, if `Resource` is `{"Catalog": {}}` (the entire data catalog):

- `Permissions` includes `ALL` OR (`ALTER` AND `DROP`) →
  **OVERPERMISSIVE_GRANT**, UNLESS the principal is already in
  `DataLakeAdmins` (then it is redundant — note but do not flag).
- `WithGrantablePermissions` includes `ALL`, `ALTER`, or any grant-delegating
  permission → **OVERPERMISSIVE_GRANT** (the principal can become effective
  admin via re-grant).

Catalog is evaluated first because a Catalog-level grant makes every narrower
grant irrelevant — the principal already holds everything.

### Step 2: External account principal (cross-account sharing)

For each grant, examine `Principal.DataLakePrincipalIdentifier`:

- Identifier is an IAM ARN whose 12-digit account ID differs from the
  catalog-owning account → **EXTERNAL_ACCOUNT**.
- Identifier is `arn:aws:iam::OTHER:root` → EXTERNAL_ACCOUNT and note
  "account-wide — any new role in OTHER inherits access".
- Identifier is a SAML or federation provider ARN from another account →
  EXTERNAL_ACCOUNT.

External account grants are NOT necessarily wrong (data-lake sharing is a
legitimate LF use case), but they MUST be verdict-flagged so the operator
confirms intent. A cross-account grant that no one remembers creating is a
stale sharing path — a top source of data leaks.

### Step 3: Wildcard and column-wildcard grants

For each grant on a Database, Table, or TableWithColumns resource:

- `Permissions: ["ALL"]` on Database or Table to a non-admin principal →
  **OVERPERMISSIVE_GRANT** (`ALL` includes DROP/ALTER and re-grant).
- SELECT on `Resource: {Table: {...}}` (NOT TableWithColumns) →
  **OVERPERMISSIVE_GRANT** — Table grants have no column or row scoping.
- SELECT on `Resource: {TableWithColumns: {...}}` with `ColumnWildcard: {}`
  → **OVERPERMISSIVE_GRANT** (equivalent to a Table grant — all columns,
  no row filter).
- `DROP` or `ALTER` on a production Database or Table to a non-admin →
  **OVERPERMISSIVE_GRANT** (destructive super-permission).
- `WithGrantablePermissions` including any of the above →
  **OVERPERMISSIVE_GRANT** (delegation chains unbounded).

**`ColumnNames: ["*"]` vs `ColumnWildcard: {}` distinction:** if the grant
uses `ColumnNames: ["*"]`, flag as CONFIG_GAP (broken automation — the grant
is silently empty; the operator believes access was granted but the principal
cannot query).

### Step 4: WithGrantablePermissions delegation audit

- Non-empty `WithGrantablePermissions` to a non-admin principal → flag as
  OVERPERMISSIVE_GRANT unless the permissions are narrow (DESCRIBE only) AND
  the resource is a single named table.
- `WithGrantablePermissions: ["ALL"]` on any resource → always
  OVERPERMISSIVE_GRANT.

### Step 5: Registered locations audit

For each Table or Database resource in a grant, verify the backing S3 path is
under a registered location:

1. Pull `aws lakeformation list-resources` (paged — drain `NextToken`).
2. For each registered resource, record the `ResourceArn` (an S3 path like
   `arn:aws:s3:::bucket/prefix/`).
3. For each grant on a Table, look up the table's `StorageDescriptor.Location`
   (from Glue) and check it is UNDER a registered path.

Findings:

- Grant on a table whose S3 path is NOT under any registered location →
  **CONFIG_GAP** (grant is ineffective; LF cannot enforce). The principal
  receives `AccessDenied` from S3 even though LF shows the grant.
- No registered locations at all → **CONFIG_GAP** (the entire data lake is
  unenforced).
- Registered location is `arn:aws:s3:::bucket/` (entire bucket) where a
  prefix would suffice → minor CONFIG_GAP (non-data-lake objects also fall
  under LF).
- Registered location's `RoleArn` is deleted or its trust policy revokes
  `lakeformation.amazonaws.com` → **CONFIG_GAP** (LF cannot read S3; grants
  are dead).

### Step 6: Data lake admin principals audit

From `get-data-lake-settings` → `DataLakeAdmins`:

- Empty list → **CONFIG_GAP** (no break-glass admin).
- Contains a principal whose account differs from the catalog owner →
  **EXTERNAL_ACCOUNT** AND **OVERPERMISSIVE_GRANT** (admin bypasses all
  grants — an external admin is total data-lake compromise).
- Contains > 5 principals → flag as CONFIG_GAP (over-delegation; admins
  should be 1-3 break-glass roles).
- Contains a human IAM user (not a role) → flag as CONFIG_GAP (humans
  rotate, leave, get phished — admins should be SSO-federated roles).

### Step 7: Cell-level filter audit

For each table with sensitive data (identify by LF-tags like
`data_classification=PII` or `confidentiality=restricted`):

1. Pull `aws lakeformation list-data-cells-filter` (paged).
2. For each sensitive table, verify a `DataCellsFilter` exists AND is
   referenced by at least one SELECT grant.
3. A `DataCellsFilter` that exists but is not wired into any grant →
   **CONFIG_GAP** (silent gap — operator believes row-filtering is in
   effect; it is not).
4. A sensitive table with NO `DataCellsFilter` AND a SELECT grant with
   `ColumnWildcard` → already OVERPERMISSIVE_GRANT from Step 3; cell-filter
   absence is an ADDITIVE finding.
5. A sensitive table with NO `DataCellsFilter` AND a column-scoped SELECT
   (explicit `ColumnNames`) → **CONFIG_GAP** (column-scoping is good but
   row-level exposure remains — every row is readable).

### Step 8: IAMAllowedPrincipals / mixed-mode audit

For each database, check for a grant with
`Principal: {"DataLakePrincipalIdentifier": "IAMAllowedPrincipals"}`:

- A database with `IAMAllowedPrincipals` AND no other explicit LF grants on
  its tables → expected (the DB is IAM-managed). Note but do not flag.
- A database with `IAMAllowedPrincipals` AND explicit LF grants on its
  tables → **CONFIG_GAP** (mixed mode — both IAM and LF evaluate; the IAM
  policy (which you may not have audited) can grant what LF would deny).
- A table with `IAMAllowedPrincipals` grant in a database that otherwise
  uses LF → **CONFIG_GAP** (one table silently opts out of LF).

The `IAMAllowedPrincipals` group is the LF escape hatch — used for backwards
compatibility with pre-LF workloads. New databases should NOT mix modes.

### Step 9: Least-privilege check (OK)

A grant is OK when ALL of:

- Resource is a named Database, Table, or TableWithColumns (not Catalog).
- Principal is a same-account role ARN (not root, not external, not
  `IAMAllowedPrincipals`).
- Permissions are a subset of `{DESCRIBE, SELECT, INSERT}` (no ALL, DROP,
  ALTER).
- For SELECT on TableWithColumns: explicit `ColumnNames` list (not
  `ColumnWildcard`).
- `WithGrantablePermissions` is empty or absent.
- The backing S3 path is under a registered location with a healthy
  `RoleArn`.
- For sensitive tables: a `DataCellsFilter` is wired into the grant.

→ **OK**.

### Step 10: Aggregation — worst finding wins

Per data lake (or per principal), the verdict is the **maximum** finding:

```text
OVERPERMISSIVE_GRANT > EXTERNAL_ACCOUNT > CONFIG_GAP > OK
```

If no findings, the verdict is **OK**.

## Output format

```text
LAKE: <catalog-id or account-id>
VERDICT: OVERPERMISSIVE_GRANT | EXTERNAL_ACCOUNT | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [OVERPERMISSIVE_GRANT] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — ColumnWildcard SELECT on a PII table without cell filter

```text
LAKE: 111111111111/prod-catalog (column-wildcard-select-no-filter)
VERDICT: OVERPERMISSIVE_GRANT
REASON: analyst role holds SELECT with ColumnWildcard on customers_pii table
(Step 3) — full-column read on a PII-tagged table. No DataCellsFilter is
wired (Step 7).
FINDINGS:
  - [OVERPERMISSIVE_GRANT] SELECT with ColumnWildcard on
    table.customers_pii to arn:aws:iam::111111111111:role/analyst (Step 3)
  - [CONFIG_GAP] No DataCellsFilter references table.customers_pii (Step 7)
REMEDIATION:
  1. Replace the ColumnWildcard grant with an explicit ColumnNames list
     excluding PII columns (ssn, email, phone).
  2. Create and grant a DataCellsFilter for region-scoping:
     aws lakeformation create-data-cells-filter --table-data '<...>'
  3. Re-audit via list-permissions to confirm the wildcard grant is revoked.
```


## Anti-Patterns — NEVER

- NEVER classify `Permissions: ["ALL"]` on `Catalog` to a non-admin as
  anything other than OVERPERMISSIVE_GRANT. `ALL` on Catalog is the LF
  super-permission — functionally equivalent to adding the principal to
  `DataLakeAdmins`.

- NEVER treat `Principal: {"DataLakePrincipalIdentifier":
  "IAMAllowedPrincipals"}` as "all IAM users". It is a SPECIAL PRINCIPAL
  that opts the resource OUT of LF enforcement — IAM policy becomes the sole
  authority. Treating it as a wildcard grantee misses the real risk (IAM
  policy may be broader than the LF grant it replaces).

- NEVER assume a `DataCellsFilter` enforces row-level security just because
  it exists. The filter must be referenced by a SELECT grant to take effect.
  A created-but-unwired filter is a silent gap.

- NEVER audit only the source account for a cross-account share. LF cross-
  account sharing uses RAM; the recipient sees nothing until an admin
  creates a Resource Link AND grants on it. The source grant may be wide,
  but if the recipient never created the link, no data moved.

- NEVER treat `ColumnNames: ["*"]` as a column wildcard. It is a literal
  column named `*` — almost certainly a bug. The real wildcard is
  `ColumnWildcard: {}`. Confusing them produces a false sense of security.

- NEVER flag a grant to a principal already listed in `DataLakeAdmins` as
  OVERPERMISSIVE_GRANT. The admin already bypasses all checks via the admin
  list — the grant is redundant, not a new exposure. Note it as cleanup.

- NEVER assume Lake Formation is enabled just because grants exist.
  `describe-organization` (or `get-data-lake-principals`) is the source of
  truth. Many accounts have legacy grants from a brief LF trial that was
  later disabled — the grants enforce nothing. Flag as CONFIG_GAP.

- NEVER propose remediation that adds new grants without checking the
  50,000-grant account quota. Converting one wildcard grant into 200 narrow
  grants can push the account over the cap and fail silently.

- NEVER overlook `DROP` and `ALTER` as destructive super-permissions. A
  non-admin with DROP on a production database can delete every table's
  metadata instantaneously.

- NEVER assume a registered location's `RoleArn` is healthy. If the role is
  deleted, LF cannot read S3 and every grant on tables under that location
  is dead. The grant list looks clean; queries fail. Verify via
  `aws iam get-role`.

- NEVER assume hybrid access mode is off. Hybrid-mode resources evaluate
  BOTH LF grants AND IAM policies — EITHER allowing grants access. An LF-
  only audit of a hybrid-mode table misses the IAM policy dimension.

- NEVER assume `Permission: SELECT` on a `Table` resource type is column-
  scoped. Only `TableWithColumns` supports column scoping; `Table` always
  means all-columns-all-rows.

- NEVER treat a grant to `arn:aws:iam::SAME_ACCOUNT:root` as scoped. Unlike
  IAM where root is one identity, an LF grant to same-account root covers
  EVERY principal in the account — every role, every user, every future
  role. It is the same exposure surface as `arn:aws:iam::OTHER:root`, just
  inside the fence. If the intent is "all current and future analysts",
  use an LF-tag policy instead — root-principal grants are un-auditable
  in practice because every new role silently inherits access.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing LF operation
  (`RevokePermissions`, `GrantPermissions`, `PutDataLakeSettings`,
  `CreateDataCellsFilter`, `RegisterResource`), emit:
  `CONFIRM: About to <action> on resource <resource> in catalog <catalog>.
  This affects <consequence>. Proceed? (yes/no)`. Do NOT execute until the
  operator confirms. LF grants have no version history — `RevokePermissions`
  is irreversible without a backup.

- **Capture grant state for rollback:**
  `aws lakeformation list-permissions --output json > /tmp/lf-grants-backup-$(date +%s).json`
  BEFORE any modification. LF does not version grants — no undo.

- **Verify the principal still exists** before revoking:
  `aws iam get-role --role-name <name>` — revoking for a deleted role is
  harmless but pollutes the audit trail.

- **For `CreateDataCellsFilter`:** confirm the table has no in-flight
  queries — adding a filter changes the row set visible to existing sessions
  on the NEXT query, which can break dashboards mid-render.

- **For `RegisterResource`:** the `RoleArn` MUST have a trust policy allowing
  `lakeformation.amazonaws.com` to assume it. A misconfigured role silently
  breaks all grants on the registered path.

- **For cross-account revocation:** revoking a grant in the source account
  does NOT delete resource links in the recipient account. The recipient
  sees stale links that return `EntityNotFoundException`. Note recipient-
  side cleanup as a separate step.

- **For `PutDataLakeSettings` (admin changes):** changes to `DataLakeAdmins`
  take effect immediately and are NOT reversible without another
  `PutDataLakeSettings` call. Verify the new admin list includes at least
  one break-glass role before applying.

- Prefer revoking over adding compensating grants. LF has no Deny — the
  only way to remove access is `RevokePermissions`. There is no "add a Deny"
  remediation as in IAM/KMS.

- For OVERPERMISSIVE_GRANT findings (Catalog ALL, ColumnWildcard), treat as
  incident-response — assume data has been queried during the exposure
  window. Audit CloudTrail for `glue:GetTable`,
  `athena:StartQueryExecution`, `lakeformation:GetTable` during exposure.

## Remediation guidance

**Ordering principle:** always revoke the broad grant AFTER the narrow
replacement is in place. Safe sequence: (1) snapshot grants, (2) add the
narrow grant (explicit ColumnNames, named table), (3) verify via
`list-permissions` or a test query, (4) revoke the broad grant. Reversing
this order produces an access-denied window.

Per-verdict remediation walkthroughs (Catalog ALL, ColumnWildcard, EXTERNAL_ACCOUNT, empty
admins, unregistered path, mixed mode, OK) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).



## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert knowledge (non-obvious LF behaviours), edge-case handling, per-verdict remediation guidance, Lake Formation authorisation internals, and Recent AWS features moved from SKILL.md.

## Domain

AWS CloudOps / Lake Formation Data Lake Security & Compliance.

## AWS documentation

- **AWS Lake Formation Developer Guide** — https://docs.aws.amazon.com/lake-formation/latest/dg/what-is-lake-formation.html
- **Lake Formation Security** — https://docs.aws.amazon.com/lake-formation/latest/dg/security.html
- **Lake Formation API Reference** — https://docs.aws.amazon.com/lake-formation/latest/dg/aws-lake-formation-api-ref.html
- **Lake Formation CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/lakeformation/
- **LF-tag-based access control** — https://docs.aws.amazon.com/lake-formation/latest/dg/security-lf-tags.html
