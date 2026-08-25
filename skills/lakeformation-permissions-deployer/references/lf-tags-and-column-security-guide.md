# LF-tags and Column Security Guide — Lake Formation Permissions Deployer

Deep reference on LF-tag strategy and design, column-level security
patterns, data cells filter row-level conditions, resource link
cross-database access, hybrid access mode migration, IAM Identity
Center principal mapping, DataZone LF-tag integration, the full NEVER
list, edge-case handling, and pre-flight safety CLI.

## LF-tag strategy and design

### Tag key selection

Choose 3-5 tag keys that map to organizational dimensions. The tag
model is the access control abstraction layer — it determines how
analysts, engineers, and services discover and access data.

| Tag key | Values | Use case |
|---|---|---|
| `environment` | production, staging, dev | Separate access by lifecycle stage |
| `department` | finance, engineering, marketing | Organizational boundary |
| `sensitivity` | public, internal, restricted, pii | Data classification |
| `region` | us-east-1, eu-west-1, ap-southeast-2 | Geographic compliance |
| `cost_center` | cc-1001, cc-1002 | Chargeback alignment |

Rules:
- **NEVER create more than 7 tag keys.** Too many keys make the
  permission model unmaintainable. Analysts cannot reason about access
  when there are 10+ dimensions.
- **Tag keys are immutable.** Once created, a tag key cannot be
  renamed. Plan carefully.
- **Tag values can be added** via `update-lf-tag`. Removing a value
  requires updating all resources and grants that reference it first.

### LF-tag inheritance

| Resource level | Inheritance |
|---|---|
| Database | Tables inherit database LF-tags unless overridden |
| Table | Columns inherit table LF-tags unless overridden |
| Column | Column LF-tags override table LF-tags |

Use column-level LF-tags for PII or sensitive columns that need
different access from the table. For example, a `sensitivity=restricted`
table may have `sensitivity=pii` columns that need stricter access.

## Column-level security patterns

### Pattern 1: Column grant (simple exclusion)

Grant SELECT on a subset of columns. PII columns are implicitly
excluded (not granted).

```bash
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "<principal-arn>"}' \
  --permissions SELECT \
  --resource '{"TableWithColumns": {"DatabaseName": "<db>", "Name": "<table>", "ColumnNames": ["id", "amount", "currency"]}}'
```

Best for: static column sets that rarely change.

### Pattern 2: Column deny via revoke (explicit exclusion)

Explicitly revoke SELECT on specific columns. Stronger than
exclusion — overrides any future table-level grant.

```bash
aws lakeformation batch-revoke-permissions \
  --entries '[{
    "Id": "deny-pii",
    "Principal": {"DataLakePrincipalIdentifier": "<principal-arn>"},
    "Permissions": ["SELECT"],
    "Resource": {"TableWithColumns": {"DatabaseName": "<db>", "Name": "<table>", "ColumnNames": ["ssn", "credit_card"]}}
  }]'
```

Best for: PII columns that should NEVER be accessible by a principal.

### Pattern 3: Data cells filter (row + column)

Use `ColumnWildcard.ExcludedColumnNames` to grant all columns except
PII, with a row filter for regional access.

```json
{
  "RowFilter": {"FilterExpression": "region = 'us-east-1'"},
  "ColumnWildcard": {"ExcludedColumnNames": ["ssn", "credit_card"]}
}
```

Best for: complex access patterns with both row and column filtering.

## Data cells filter row-level conditions

### Filter expression syntax

| Expression | Example | Use case |
|---|---|---|
| Equality | `region = 'us-east-1'` | Regional access |
| IN list | `department IN ('finance', 'engineering')` | Multi-department |
| Comparison | `amount < 10000` | Threshold-based |
| AND | `region = 'us-east-1' AND department = 'finance'` | Compound |
| OR | `region = 'us-east-1' OR region = 'eu-west-1'` | Multi-region |

Rules:
- **Use simple equality for high-throughput tables.** Complex
  expressions add query overhead.
- **Avoid `IN` lists with > 100 values.** Performance degrades.
  Use a dimension table join instead.
- **`AllRowsWildcard` without a `FilterExpression`** defeats row-level
  security — it grants access to all rows with only column-level
  filtering. NEVER use this pattern for PII tables.

## Resource link cross-database access

### How resource links work

A resource link is a pointer in a target database to a source table
in another database. The principal queries the link (in the target
database) and Lake Formation resolves the access against the source
table's permissions.

### Required permissions for resource link queries

| Permission | Resource | Why |
|---|---|---|
| DESCRIBE | Resource link (in target database) | To see the link in catalog |
| SELECT | Source table (in source database) | To read the underlying data |
| DESCRIBE | Source database | To resolve the catalog reference |

Rules:
- **Grant BOTH link DESCRIBE and table SELECT.** Without both, queries
  fail with "table not found" or "access denied."
- **Resource links do not copy LF-tags.** The link is a pointer; the
  source table's LF-tags control access.
- **Cross-account resource links** require a RAM resource share. NEVER
  create cross-account links without a RAM share.

## Hybrid access mode migration

### What hybrid access mode does

Hybrid access mode enables a table to be accessed via BOTH Lake
Formation permissions AND IAM/IAM policies simultaneously. This is
the recommended migration path from IAM-based to Lake Formation-based
access control.

### Migration steps

1. Enable hybrid access mode on the table.
2. Verify existing IAM policy-based access still works.
3. Create Lake Formation permissions for all principals.
4. Verify Lake Formation permissions work via Athena/Redshift.
5. Remove IAM table policies (switch to Lake Formation-only mode).

Rules:
- **Lake Formation is the effective permission layer** in hybrid
  mode. IAM policies that conflict with Lake Formation are silently
  overridden.
- **Test before production migration.** Use a non-production account
  to validate the migration path.
- **NEVER disable hybrid access mode while IAM policies still grant
  table access.** This breaks access for IAM-based workloads.

## IAM Identity Center principal mapping

### Principal types

| Principal type | ARN format | Use case |
|---|---|---|
| IAM role | `arn:aws:iam::<acct>:role/<role>` | Service-to-service access |
| IAM user | `arn:aws:iam::<acct>:user/<user>` | Individual IAM user |
| Identity Center permission set | `arn:aws:sso:::permissionSet/<ins>/<ps>` | SSO session-based access |
| Identity Center group | `arn:aws:sso:::group/<ins>/<group>` | Group-based SSO access |
| SAML federated | `arn:aws:iam::<acct>:saml-provider/<provider>` | SAML federation |

Rules:
- **Prefer Identity Center for human-principal access.** Identity
  Center provides session-based, auditable access via SSO.
- **IAM roles are for service-to-service access** (ETL pipelines,
  Lambda functions, Glue jobs).
- **NEVER mix IAM role principals and Identity Center principals for
  the same access pattern.** Choose one model per access pattern.

## DataZone LF-tag integration

### How DataZone uses LF-tags

DataZone catalog assets map to LF-tag expressions. When a project
subscribes to a listing backed by LF-tags, DataZone auto-grants Lake
Formation permissions to the project's execution role.

### Subscription workflow

1. Data owner publishes a DataZone asset backed by LF-tag expression
   (e.g., `environment=production AND department=finance`).
2. Analyst requests a subscription to the asset.
3. Data owner approves (or auto-approval for trusted projects).
4. DataZone auto-grants Lake Formation permissions via LF-tags.
5. Analyst accesses the data via Athena/Redshift Spectrum.

Rules:
- **LF-tags are the bridge.** Ensure LF-tags on resources match the
  DataZone classification.
- **DataZone manages the subscription lifecycle.** Unsubscribing
  revokes the Lake Formation permissions automatically.
- **Use DataZone for analyst-facing self-service.** Reduces the admin
  burden of manual grants.

## NEVER (full list)

1. NEVER grant Lake Formation permissions without a registered data
   lake admin. Without an admin, grants fail with
   `AccessDeniedException`.
2. NEVER use `AdministratorAccess` IAM role as the data lake admin.
   Use a dedicated `LFDataLakeAdmin` role with scoped permissions.
3. NEVER grant table-level SELECT to a principal that should only see
   non-PII columns. Use column-level grants or data cells filter.
4. NEVER create LF-tag-based grants without attaching LF-tags to
   resources first. The grant matches nothing — silent failure.
5. NEVER mix IAM role principals and Identity Center principals for
   the same access pattern. Choose one model per pattern.
6. NEVER create more than 7 LF-tag keys. Too many keys make the model
   unmaintainable.
7. NEVER use `AllRowsWildcard` without a `FilterExpression` in data
   cells filter. It defeats row-level security.
8. NEVER create resource links without granting BOTH link DESCRIBE
   and table SELECT. Queries fail with "table not found."
9. NEVER disable hybrid access mode while IAM policies still grant
   table access. This breaks IAM-based workloads.
10. NEVER leave data lake admin as a single principal. Register at
    least 2 for operational redundancy.
11. NEVER create cross-account resource links without a RAM resource
    share. The link resolves to nothing without the share.
12. NEVER skip CloudTrail auditing for LF-tag and permission changes.
    All grants and revokes must be auditable for compliance.

## Pre-flight safety CLI

```bash
# Data lake admin registered
aws lakeformation list-data-lake-settings --query 'DataLakeSettings.DataLakeAdmins'

# Glue database exists
aws glue get-database --name <database>

# Glue table exists
aws glue get-table --database-name <database> --name <table>

# IAM principal exists
aws iam get-role --role-name <role-name>

# S3 location registered
aws lakeformation list-resources --query 'ResourceInfoList[*].ResourceArn'

# LF-tags exist
aws lakeformation list-lf-tags

# LF-tags on resources
aws lakeformation get-resource-lf-tags --resource '{"Database": {"Name": "<database>"}}'
aws lakeformation get-resource-lf-tags --resource '{"Table": {"DatabaseName": "<database>", "Name": "<table>"}}'

# Identity Center instance (if SSO)
aws sso-admin list-instances --query 'Instances[*].InstanceArn'

# DataZone domain (if DataZone)
aws datazone list-domains --query 'items[*].id'
```

## Edge-case handling

- **Cross-account LF-tag grants:** use RAM resource shares to share
  LF-tag-based permissions across accounts. The receiving account
  must accept the RAM invitation before grants take effect.
- **LF-tag on partitioned tables:** LF-tags on partitioned tables
  apply to all partitions. Column-level LF-tags apply to partition
  columns too — ensure partition columns (e.g., `dt`, `region`) have
  appropriate tags.
- **Governed Tables and Lake Formation:** Governed Tables are
  managed entirely by Lake Formation — IAM table policies are
  ignored. Ensure all access is via Lake Formation grants.
- **Hybrid access mode conflicts:** when both IAM and Lake Formation
  permissions exist, Lake Formation is the effective permission
  layer. IAM policies that conflict with Lake Formation are silently
  overridden. Test before production migration.
- **Data cells filter performance:** complex filter expressions add
  query overhead. Use simple equality filters (`region = 'us-east-1'`)
  for high-throughput tables. Avoid `IN` lists with > 100 values.
- **Resource link and LF-tag interaction:** resource links do not
  inherit LF-tags from the source table. The principal needs access
  to BOTH the link (DESCRIBE) and the target table (SELECT via
  LF-tag or named resource).
- **Identity Center session duration:** Identity Center sessions
  expire after the configured duration (default 8 hours). Long-running
  queries may fail at session expiry. Use service roles for ETL
  pipelines instead of Identity Center sessions.
- **DataZone subscription approval:** DataZone subscriptions require
  approval from the data owner. Configure auto-approval for trusted
  projects or manual approval for sensitive data.
