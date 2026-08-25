# Advanced Patterns — Lake Formation Data Lake Auditor

Load-on-demand deep dives moved verbatim from SKILL.md.

## Step 0 — Expert knowledge: non-obvious Lake Formation behaviours (moved from SKILL.md)

Each behaviour below changes a verdict if ignored:

- **No Deny exists in Lake Formation.** Permissions are purely additive. The
  only way to block access is to refrain from granting or call
  `RevokePermissions`. There is no `Effect: Deny` analogue. A "least-
  privilege boundary" is enforced by *not granting* — you cannot layer a
  Deny on an over-broad Allow as in IAM.

- **`IAMAllowedPrincipals` is a SPECIAL PRINCIPAL, not a group of IAM
  users.** A grant to `IAMAllowedPrincipals` delegates authorisation to IAM
  policy on that resource — the "external" table model used by Athena, EMR,
  and some Glue modes. The grant does NOT mean "all IAM principals" — it
  means "IAM, not LF, decides". If the same DB also has explicit LF grants
  to other principals, you are in MIXED MODE — both layers evaluate and
  EITHER allowing grants access. This is rarely intentional and a frequent
  leakage source when IAM policy is broader than the LF grant it replaces.

- **`Permission: "ALL"` is the LF super-permission for its scope.** Unlike
  IAM (where `*` is needed), LF has a literal `"ALL"` value. `ALL` on
  `Catalog` is functionally data-lake administrator — the grantee can grant
  anything to anyone, including themselves. `ALL` on a Database includes
  DROP, ALTER, CREATE_TABLE, DESCRIBE, and re-grant ability.

- **`WithGrantablePermissions` is the LF analogue of `kms:CreateGrant` —
  and it chains UNBOUNDED.** Unlike KMS grants (cap at 2 levels), LF grants
  with `WithGrantablePermissions` can be re-delegated indefinitely. Any
  grant where `WithGrantablePermissions` contains `ALL`, `ALTER`, or any
  grant-delegating permission on broad resources is a privilege-widening
  vector.

- **`ColumnWildcard` vs `ColumnNames: ["*"]` are different.**
  `ColumnNames: ["*"]` is a literal column named `*` (almost never exists) —
  a sure sign of broken automation; the grant is silently empty.
  `ColumnWildcard: {}` is the actual wildcard (all current and future
  columns). Confusing them produces a false sense of security.

- **`Table` and `TableWithColumns` are SEPARATE resource types.** SELECT on
  `Resource: {Table: {...}}` is implicit "all columns, all rows" — no column
  or row scoping exists at the Table resource type. To column-scope, the
  grant must be on `Resource: {TableWithColumns: {...}}` with an explicit
  `ColumnNames` list.

- **`DataCellsFilter` must be CREATED and then WIRED via grant.** Creating
  a row-level filter does nothing on its own — the principal must ALSO have
  a SELECT grant that the filter scopes. A filter that exists but is not
  referenced by any grant is a SILENT gap. Cross-reference
  `aws lakeformation list-data-cells-filter` against active SELECT grants.

- **Cross-account sharing uses RAM under the hood.** When a Database or
  Table is shared cross-account via LF, the recipient sees NOTHING until an
  admin in the recipient account creates a RESOURCE LINK AND grants on it.
  Auditing only the source account overstates access. Always check both
  sides — a wide source grant with no recipient resource link moved zero
  data.

- **`Principal: {"DataLakePrincipalIdentifier": "arn:aws:iam::ACCOUNT:root"}`
  covers EVERY principal in that account.** This is the account-wide grant.
  To scope to one role, use `arn:aws:iam::ACCOUNT:role/role-name`. A root-
  level principal is not necessarily wrong, but ANY new role in that account
  inherits access — a top source of data leaks when the recipient account
  later creates broad-privilege roles.

- **`CREATE_TABLE` does NOT include SELECT on the resulting table.** A
  principal who creates a table cannot read it back without a separate
  SELECT grant, UNLESS they hold `ALL` on the database (which auto-grants
  via `CreateTableDefaultPermissions`). This is a frequent source of over-
  broad `ALL` grants used as a workaround.

- **Quota: 50,000 LF permission grants per account (soft cap).** Past this,
  `CreatePermissions` returns `ResourceNumberLimitExceededException`. When
  proposing remediation that ADDS grants (e.g. converting a wildcard to many
  narrow grants), estimate grant-count growth — the cure can hit the quota
  and fail silently.

- **Registered-location `RoleArn` is the service role LF uses to read S3.**
  If the role is deleted (or its trust policy broken), LF cannot read the
  underlying data — every grant on tables under that location is dead, and
  the failure is silent (queries return `AccessDenied` from S3, not LF).

- **Hybrid access mode (2023+) means LF AND IAM both evaluate.** A query
  against a hybrid-mode table passes BOTH the LF grant check AND the IAM
  policy check — EITHER allowing grants access. Without hybrid mode, the
  old rule applies: LF grant = LF sole authority; `IAMAllowedPrincipals` =
  IAM sole authority. Hybrid mode is opt-in per resource and easy to miss.

- **`DROP` and `ALTER` are destructive super-permissions.** A non-admin
  with DROP on a production database can delete every table's metadata
  instantaneously. Treat DROP+ALTER on Database/Table to a non-admin as
  OVERPERMISSIVE_GRANT, same severity class as a wildcard SELECT.

- **LFTag-policy grants are evaluated at QUERY TIME, not GRANT TIME.** If
  you grant SELECT on LFTag `environment=prod`, and later add the
  `environment=prod` tag to a NEW table, the grantee AUTOMATICALLY has
  access to the new table with no additional grant. This is the ABAC power
  AND the ABAC risk — any future-tagged resource is silently covered by the
  existing grant. Audit tag-to-resource mappings
  (`aws lakeformation get-resource-lf-tags`) alongside the grant, not just
  the grant text.

- **`TagValues: ["*"]` in an LFTag grant matches ANY value, including
  future ones.** Distinct from listing explicit values
  (`TagValues: ["prod","staging"]`), the wildcard form is a forward-
  compatible super-permission on that tag key. Treat `TagValues: ["*"]` as
  OVERPERMISSIVE_GRANT — the grantee gets access to every current and
  future value of that key. The sneaky case: `TagKey: "environment",
  TagValues: []` (empty list) is NOT "no values" — LF interprets it as
  "any value", same as `["*"]`.

- **`PermissionsWithGrantOptions` is PER-PERMISSION, not per-grant.** Each
  entry in the `Permissions` list has a corresponding entry (by index) in
  `PermissionsWithGrantOptions`. You can grant `SELECT` (grantable) +
  `DESCRIBE` (not grantable) in the SAME grant. A naive audit that treats
  the field as grant-scoped over- or under-reports the delegation surface.
  Always zip the two lists positionally when evaluating Step 4.

- **`BatchGrantPermissions` is atomic PER BATCH, not across batches.** If
  one permission in a batch fails validation, the ENTIRE batch rolls back.
  But two separate `BatchGrantPermissions` calls are independent — a partial
  failure across batches leaves the grant state half-applied with no
  automatic rollback. When proposing multi-grant remediation, prefer a
  single batch over multiple calls; when auditing a half-applied state,
  suspect a cross-batch partial failure.

- **The Glue API and the Lake Formation API are DIFFERENT surfaces.**
  `glue:GetTable` and `lakeformation:GetTable` are not the same call — the
  Glue API may bypass LF enforcement in configurations where the calling
  principal has an IAM grant on the catalog resource, while the LF API
  always checks. Athena routes through LF; the Glue console and some EMR
  modes route through Glue. An analyst using Athena is LF-checked; the same
  analyst using the Glue console may see table metadata that LF would
  deny. Cross-reference the access path, not just the principal.

## Edge-case handling

- **Grant with both `ColumnNames` and `ColumnWildcard`.** LF rejects this at
  create (`InvalidInputException`), but stale snapshots may show it. Treat
  as OVERPERMISSIVE_GRANT (the wildcard wins if it ever existed).
- **Principal is an IAM role assumed via SSO.** The role ARN is the
  principal — SSO identity is not visible at the LF layer. SSO session
  policies do NOT apply to LF grants (they apply to IAM, not LF).
- **Grant on an LFTag resource.** `Resource: {LFTag: {...}}` grants on the
  tag, not on resources — SELECT on an LFTag is SELECT on EVERY table that
  bears the tag. Treat as OVERPERMISSIVE_GRANT if the tag is broadly applied.
- **Cross-account grant via RAM (not direct LF grant).** RAM shares appear
  in `aws ram list-resources` but may not appear in `list-permissions` in
  the source account. Cross-reference RAM for cross-account shares.
- **Empty `Permissions` list.** A grant with `Principal` and `Resource` but
  empty `Permissions` is a no-op. Note as CONFIG_GAP (stale grant litter).
- **Resource Link pointing at a deleted source table.** The link exists;
  querying returns `EntityNotFoundException`. Note as CONFIG_GAP (stale
  link — recipient-side cleanup needed).

## Remediation guidance — per-verdict walkthroughs (moved from SKILL.md)

### For OVERPERMISSIVE_GRANT — Catalog ALL (Step 1)

1. Identify whether the principal is in `DataLakeAdmins`. If yes, the grant
   is redundant — remove as cleanup. If no, this is an escalation path.
2. Replace Catalog `ALL` with the minimum scope:
   - Data engineer: `DESCRIBE` + `CREATE_TABLE` on specific databases.
   - Analyst: `DESCRIBE` on Catalog + `SELECT` (column-scoped) on specific
     tables.
3. Revoke:
   `aws lakeformation revoke-permissions --principal <arn> --permissions ALL --resource '{"Catalog":{}}'`
4. Audit CloudTrail for `lakeformation:GrantPermissions` by the principal
   during exposure — they may have created additional self-grants.

### For OVERPERMISSIVE_GRANT — ColumnWildcard SELECT (Step 3)

1. Identify needed columns (derive from Athena query history in CloudTrail).
2. Grant the narrow replacement BEFORE revoking:
   `aws lakeformation grant-permissions --principal <arn> --permissions SELECT --resource '{"TableWithColumns":{"DatabaseName":"db","Name":"tbl","ColumnNames":["col1","col2"]}}'`
3. Revoke the wildcard:
   `aws lakeformation revoke-permissions --principal <arn> --permissions SELECT --resource '{"TableWithColumns":{"DatabaseName":"db","Name":"tbl","ColumnWildcard":{}}}'`
4. If PII-tagged, add a `DataCellsFilter` for row-scoping.

### For EXTERNAL_ACCOUNT (Step 2)

1. Confirm the cross-account grant is intentional. If not, revoke.
2. If intentional, scope from account-root (`arn:aws:iam::OTHER:root`) to a
   specific role (`arn:aws:iam::OTHER:role/named-role`).
3. Verify the recipient account has created a Resource Link — without it,
   the grant is invisible. Run `aws lakeformation list-resources` in the
   recipient account.
4. Add a `DataCellsFilter` if the shared table contains data the recipient
   should not see row-wise.
5. Document the share in a registry — stale shares are a top leak source.

### For CONFIG_GAP — empty DataLakeAdmins (Step 6)

1. Designate 1-3 break-glass roles (SSO-federated, not IAM users) as admins.
2. Apply:
   `aws lakeformation put-data-lake-settings --data-lake-settings '{"DataLakeAdmins":[{"DataLakePrincipalIdentifier":"arn:aws:iam::111111111111:role/lf-break-glass"}]}'`
3. Verify with `get-data-lake-settings`.
4. Document the break-glass procedure — admins bypass LF grants.

### For CONFIG_GAP — grant on unregistered path (Step 5)

1. Identify registered locations: `aws lakeformation list-resources`.
2. If the table's `StorageDescriptor.Location` is not under any registered
   path, either:
   - Register the path:
     `aws lakeformation register-resource --resource-arn arn:aws:s3:::bucket/prefix/ --use-service-linked-role`, OR
   - Move the table data under an already-registered path.
3. Verify via a test query as the principal.

### For CONFIG_GAP — IAMAllowedPrincipals mixed mode (Step 8)

1. Decide per database: LF OR IAM, not both.
2. For new databases, do NOT grant to `IAMAllowedPrincipals` — use LF
   grants only.
3. For legacy databases that must use IAM, ensure NO explicit LF grants
   exist on their tables (remove the mixed-mode condition).
4. Migrate legacy DBs to LF during a maintenance window — the transition is
   not transparent to queries.

### For OK

1. No remediation required for current posture.
2. Recommend periodic re-audit — LF grants accumulate and have no expiry.
3. Recommend a `DataCellsFilter` even for non-sensitive tables as defense-
   in-depth.

## Deep reference: Lake Formation authorisation internals

### Authorisation evaluation pipeline

1. **IAM auth on the API call.** The principal's IAM policy must allow
   `glue:GetTable`, `athena:StartQueryExecution`, etc.
2. **Lake Formation grant check.** For resources registered to LF, LF
   evaluates Principal + Resource + Permission. If yes, access granted.
3. **IAMAllowedPrincipals fallback.** If the resource has a grant to
   `IAMAllowedPrincipals`, LF delegates to IAM — step 2 is skipped.
4. **Hybrid mode (opt-in per resource).** Both LF (step 2) AND IAM (step 3)
   evaluate — EITHER allowing grants access.
5. **Data lake admin bypass.** If the principal is in `DataLakeAdmins`, ALL
   LF checks are skipped. IAM still applies.

### Cross-account sharing mechanics

Cross-account LF sharing uses AWS RAM: source grants via `GrantPermissions`
→ LF creates a RAM resource share automatically → recipient admin must
`create-resource-link` AND `GrantPermissions` on the link → source revoke
does NOT delete recipient resource links (they go stale, returning
`EntityNotFoundException`).

### Grant quotas and limits

- **50,000 LF permission grants per account** (soft cap; past this,
  `ResourceNumberLimitExceededException`).
- **10,000 Resource Links per account** (soft cap).
- **1 DataCellsFilter per table** (multiple filters not supported).
- **50 LF-tags per resource** (hard cap).
- **Grant depth: unbounded** — any grantee with `WithGrantablePermissions`
  can re-delegate (no chain-depth limit like KMS's 2-level cap).

LF grants have **no version history**. `GrantPermissions` and
`RevokePermissions` modify the grant set in place — no diff, no rollback.
Treat every grant modification as irreversible.

## Recent AWS features (2024-2026)

- **Lake Formation governed tables and Apache Iceberg support (2024-2025):** Lake Formation now supports Apache Iceberg table format with governed table features (ACID transactions, time travel). Auditors should verify that Iceberg tables have appropriate LF-tag policies and that cross-account access to governed tables uses Lake Formation grants (not S3 bucket policies directly).
- **Row-level and column-level security enhancements (2024):** Enhanced cell-level security with DataCellsFilter improvements. Auditors should verify that sensitive columns have DataCellsFilter rules and that `ColumnWildcard` SELECT is not granted without a corresponding filter.
- **LF-tags governance (2024-2025):** Improved LF-tag-based access control with tag inheritance. Auditors should verify that LF-tag policies are not overly broad (e.g., `dba:*` tag granting full access to all databases).
- **Amazon Q integration (2024):** Lake Formation integrates with Amazon Q for natural-language data queries. Auditors should verify that Q's IAM role is scoped to only the data it should access.
