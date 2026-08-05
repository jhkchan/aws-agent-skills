---
description: Audit a Lake Formation data lake for catalog-level super-grants, cross-account principals, ColumnWildcard SELECT without DataCellsFilter, WithGrantablePermissions delegation, unregistered S3 locations, DataLakeAdmins composition, and IAMAllowedPrincipals mixed-mode databases.
nl_triggers:
  - "audit lake formation data lake"
  - "check lake formation permissions"
  - "lf permissions audit"
  - "cross-account data lake share"
  - "column wildcard lake formation"
  - "data cells filter gap"
  - "iamallowedprincipals mixed mode"
  - "data lake admin list"
  - "withgrantablepermissions delegation"
  - "registered location gap"
  - "lake formation grant review"
  - "lf-tag policy audit"
  - "hardening lake formation"
  - "data lake security audit"
routes_to: lakeformation-data-lake-auditor
---

# /aws:audit-lakeformation-data-lake

Activate the `lakeformation-data-lake-auditor` skill and audit one or more
Lake Formation data-lake configurations (grants + settings + resources) for
security exposure.

## What it does

Reads Lake Formation `list-permissions` output paired with
`get-data-lake-settings`, `list-resources`, and `list-data-cells-filter`
metadata, and applies the ordered classification logic:

1. Pre-flight data-lake state gate — short-circuit disabled LF, empty
   admins, and empty registered-locations.
2. Catalog-level super grants — `Permissions: ALL` on `Catalog` to a
   non-admin is admin escalation (OVERPERMISSIVE_GRANT).
3. External account principal — `DataLakePrincipalIdentifier` from a
   different account is cross-account sharing (EXTERNAL_ACCOUNT).
4. Wildcard / column-wildcard grants — `ALL` on DB/Table, SELECT on `Table`
   (not `TableWithColumns`), or `ColumnWildcard: {}` (OVERPERMISSIVE_GRANT).
5. `WithGrantablePermissions` delegation — non-empty to a non-admin chains
   unbounded (OVERPERMISSIVE_GRANT).
6. Registered locations audit — grant on a table whose S3 path is not under
   any registered location is ineffective (CONFIG_GAP).
7. `DataLakeAdmins` audit — empty list, external principal, or > 5 admins.
8. Cell-level filter audit — sensitive table without a wired
   `DataCellsFilter` (CONFIG_GAP).
9. `IAMAllowedPrincipals` mixed-mode — DB with the special principal AND
   explicit LF grants on its tables (CONFIG_GAP).
10. Aggregation — worst finding wins (OVERPERMISSIVE_GRANT > EXTERNAL_ACCOUNT
    > CONFIG_GAP > OK).

Emits a deterministic VERDICT per data lake:

```text
LAKE: <catalog-id or account-id>
VERDICT: OVERPERMISSIVE_GRANT | EXTERNAL_ACCOUNT | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step>
FINDINGS:
  - [OVERPERMISSIVE_GRANT] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste Lake Formation permissions + settings output and ask any of:

- "audit this lake formation data lake"
- "check LF permissions"
- "is my data lake shared cross-account"
- "audit lake formation grants"
- "is my DataCellsFilter wired"
- "IAMAllowedPrincipals mixed mode"
- "data lake admin list review"
- "WithGrantablePermissions delegation"
- "registered location gap"

A bare catalog id or account id + any audit verb ("audit this data lake",
"check LF grants") also routes here via the orchestrator.

## Inputs

- `list-permissions` output (JSON) — the grants under review.
- `get-data-lake-settings` output — `DataLakeAdmins`,
  `CreateDatabaseDefaultPermissions`, `CreateTableDefaultPermissions`.
- `list-resources` output — registered S3 locations and their `RoleArn`.
- `list-data-cells-filter` output — existing row-level filters.
- (Optional) `get-resource-lf-tags` — tag-to-resource mapping for
  ABAC-scoped grants.
- (Optional) `describe-organization` — confirms LF is enabled.

## Outputs

- One VERDICT block per data lake (multiple findings aggregate to the worst
  severity).
- Enumerated FINDINGS list with per-finding verdict and step citation.
- Specific remediation: revoke Catalog `ALL`, replace `ColumnWildcard` with
  explicit `ColumnNames`, register the S3 path, scope the cross-account
  principal from root to a named role, wire the `DataCellsFilter`, pick LF
  OR IAM per database.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Lake Formation / Analytics security).
- `/aws:audit-iam-least-privilege` for IAM policy analysis of roles that
  may interact with LF resources via the IAMAllowedPrincipals fallback.
- `/aws:audit-kms-key-policy` for the KMS keys backing the S3 registered
  locations (LF grants are dead if the underlying S3 SSE-KMS key is pending
  deletion).
