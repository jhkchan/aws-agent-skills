---
name: lakeformation-permissions-deployer
description: 'Deploys AWS Lake Formation permissions with production-grade config: LF-tag based access control (tag keys and values, tag-based grants on databases, tables, columns), database and table permissions (DESCRIBE, SELECT, INSERT, DROP, ALTER), column-level security (column grant and deny, data cells filter for row and column filtering), data lake admin registration (IAM principals), resource links (cross-database table references), external data filtering, and latest features (Lake Formation with IAM Identity Center, LF-tags with Amazon DataZone, hybrid access mode, Governed Tables). Emits a READY_TO_DEPLOY checklist. Use when granting Lake Formation permissions, setting up LF-tag based access control, configuring column-level security, registering a data lake admin, or creating resource links. Triggers: Lake Formation, LF-tags, LF-tag based access control, data lake permissions, column-level security, data cells filter, resource links, IAM Identity Center, DataZone, data lake admin.'
license: Apache-2.0
compatibility: 'Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with lakeformation, glue, iam, ram, and s3 access. Works with Terraform aws_lakeformation_* resources, CloudFormation AWS::LakeFormation::* resources, and the AWS Console Lake Formation Permissions wizard.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Governance
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, lakeformation, lake-formation, cloudops, deploy, governance, permissions
  dependencies: aws-orchestrator
  keywords: aws, lakeformation, lake-formation, lf-tags, data-lake, cloudops, deploy, governance, permissions, column-level-security, data-cells-filter, resource-links, iam-identity-center, datazone, data-lake-admin
  when_to_use: Invoke when the user wants to grant Lake Formation permissions on databases or tables, set up LF-tag based access control, configure column-level or row-level security via data cells filter, register a data lake admin IAM principal, create resource links for cross-database table access, integrate Lake Formation with IAM Identity Center, or configure LF-tags for Amazon DataZone. Do NOT invoke for Glue Data Catalog setup without Lake Formation (use glue-crawler-job-auditor), S3 bucket policy provisioning (use s3-bucket-policy-deployer), or Macie data classification (use macie-data-classification-auditor).
---

# Lake Formation Permissions Deployer

An AWS CloudOps agent skill that deploys AWS Lake Formation permissions
with correct production defaults. Emits a READY_TO_DEPLOY checklist
verifying every configuration item.

## Quick navigation

| Need | Section |
|---|---|
| What MUST be in the response | "STRICT output contract" |
| Why admin-before-grants order matters | "Reasoning framework" |
| What to verify before deploying | "Prerequisites" |
| The ordered deployment steps | "Deployment procedure" |
| Common silent-failure pitfalls | "NEVER" |
| Permission-model decision matrix | "Workload matrix" |
| 2024-2026 feature changes | "Recent AWS features" |
| Deep CLI sequences | `references/cli-commands-and-iac.md` |
| LF-tags, column security, full NEVER | `references/lf-tags-and-column-security-guide.md` |

## STRICT output contract

When this skill is invoked with a Lake Formation permissions deployment
request, the agent MUST respond with the READY_TO_DEPLOY checklist
defined in "Output format" using the literal all-caps labels
`PERMISSION_DEPLOYMENT:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines.

### Required output structure

1. `PERMISSION_DEPLOYMENT: <deployment-name>` — the Lake Formation
   permission deployment being applied.
2. `VERDICT: READY_TO_DEPLOY` OR `VERDICT: PREREQUISITES_MISSING`.
3. `CHECKLIST:` followed by indented lines with status markers
   (`[✓]`, `[✗]`, `[OPTIONAL]`, `[INPUT NEEDED]`).
4. `VERIFICATION_COMMANDS:` followed by indented
   `aws lakeformation ...` commands.

### FORBIDDEN output patterns

- **No prose preamble before `PERMISSION_DEPLOYMENT:`** — first
  non-empty line MUST be `PERMISSION_DEPLOYMENT:`.
- **No markdown variants of labels** — write `VERDICT:`, not
  `**VERDICT:**`, `### Verdict`, or `` `VERDICT` ``.
- **No swapping verdict tokens** — exactly `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING`.
- **No omitting `VERIFICATION_COMMANDS:`** — include even when
  PREREQUISITES_MISSING.
- **No extra sections after `VERIFICATION_COMMANDS:`** — the
  checklist block is the entire response.
- **No status marker drift** — use only `[✓]`, `[✗]`, `[OPTIONAL]`,
  `[INPUT NEEDED]`.

### Perfect example (copy the shape exactly)

```text
PERMISSION_DEPLOYMENT: analytics-team-lf-tag-access
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Data lake admin — arn:aws:iam::123456789012:role/LFDataLakeAdmin (registered)
  [✓]      LF-tag keys — environment (values: production, staging), department (values: finance, engineering)
  [✓]      LF-tag on database — analytics_db: environment=production, department=finance
  [✓]      LF-tag on table — transactions: environment=production, department=finance
  [✓]      Principal — arn:aws:iam::123456789012:role/AnalyticsTeamRole
  [✓]      LF-tag-based grant — SELECT on database/table LF-tags: environment=production, department=finance
  [✓]      Column-level security — column grant: SELECT on columns [transaction_id, amount, currency] (PII columns EXCLUDED)
  [✓]      Resource links — cross-database resource link finance_transactions_link for table analytics_db.transactions
  [✓]      Data cells filter — row filter region IN ('us-east-1') on table transactions (optional, configured)
  [✓]      Tags — Environment=production, Governance=lake-formation
VERIFICATION_COMMANDS:
  aws lakeformation list-permissions --principal arn:aws:iam::123456789012:role/AnalyticsTeamRole
  aws lakeformation get-resource-lf-tags --resource '{"Database": {"Name": "analytics_db"}}'
  aws lakeformation list-lf-tags
  aws lakeformation describe-resource --resource-arn arn:aws:glue:us-east-1:123456789012:table/analytics_db/transactions
```

## Reasoning framework (why the admin-before-grants order matters)

1. **Data lake admin FIRST** — a data lake admin is an IAM principal
   (role or user) registered in Lake Formation. Only data lake admins
   can create LF-tags, register data locations, and grant permissions
   to other principals. Without an admin, no permission deployment
   can proceed.
2. **LF-tag keys and values** — LF-tags are key-value pairs attached
   to databases, tables, and columns. They are the access control
   abstraction layer: principals receive permissions on LF-tag
   expressions (e.g., `environment=production`), not on individual
   resources. Define tag keys BEFORE granting tag-based permissions.
3. **LF-tags on resources** — attach LF-tags to Glue databases and
   tables. Without LF-tags on resources, tag-based grants match
   nothing and principals receive zero access.
4. **Principal grants** — grant permissions (DESCRIBE, SELECT, INSERT)
   on LF-tag expressions to IAM principals (roles, users, SAML
   federated groups, IAM Identity Center groups). Without grants,
   principals cannot access data even if LF-tags are configured.
5. **Column-level security LAST** — column grants/denies and data
   cells filters are fine-grained layers applied AFTER the base
   table-level permission. They restrict which columns and rows a
   principal can access within an otherwise-permitted table.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **Data lake admin** | An IAM principal registered as a data lake admin. Only admins can create LF-tags and grant permissions. | `aws lakeformation list-data-lake-settings --query 'DataLakeSettings.DataLakeAdmins'` |
| **Glue Data Catalog** | Lake Formation manages permissions on Glue databases and tables. The catalog MUST be enabled for Lake Formation. | `aws glue get-databases --query 'DatabaseList[*].Name'` |
| **Glue database and tables** | The target database and tables MUST exist in the Glue Data Catalog. Without them, LF-tags and grants target nothing. | `aws glue get-database --name <db>` / `aws glue get-table --database-name <db> --name <table>` |
| **IAM principal for grants** | The role, user, or federated group receiving permissions. MUST exist in IAM (or IAM Identity Center). | `aws iam get-role --role-name <role>` |
| **S3 data location registered** | If the data lives in S3, the S3 location MUST be registered in Lake Formation as a data lake resource. | `aws lakeformation list-resources --resource-role arn:aws:iam::<acct>:role/LFServiceRole` |
| **IAM Identity Center instance** (if Identity Center integration) | For Identity Center-based grants, the Identity Center instance MUST be enabled and groups MUST exist. | `aws sso-admin list-instances` |
| **Amazon DataZone domain** (if DataZone integration) | For DataZone LF-tag integration, the DataZone domain and project MUST exist. | `aws datazone list-domains` |
| **Resource link target database** (if cross-database) | For resource links, the target database MUST exist and the source table MUST be accessible. | `aws glue get-database --name <target-db>` |
| **Hybrid access mode** (if applicable) | If using hybrid access mode, the table MUST be enabled for both Lake Formation and IAM/IAM Policies. | `aws lakeformation describe-resource --resource-arn <table-arn>` |

## Deployment procedure (apply in order)

### Step 1: Register data lake admin

The data lake admin is an IAM principal that can create LF-tags,
register data locations, and grant permissions. At least one admin
MUST be registered before any permission deployment.

```bash
aws lakeformation put-data-lake-settings \
  --data-lake-settings '{
    "DataLakeAdmins": [
      {"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/LFDataLakeAdmin"}
    ],
    "CreateDatabaseDefaultPermissions": [
      {"Principal": {"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/LFDataLakeAdmin"}, "Permissions": ["ALL"]}
    ],
    "CreateTableDefaultPermissions": [
      {"Principal": {"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/LFDataLakeAdmin"}, "Permissions": ["ALL"]}
    ],
    "TrustedResourceOwners": ["arn:aws:iam::123456789012:root"]
  }'
```

Rules:
- **The admin role needs `lakeformation:*` and `glue:*` IAM
  permissions.** Without IAM-level permissions, the admin cannot call
  Lake Formation APIs.
- **NEVER register a role with `AdministratorAccess` as the sole data
  lake admin.** Use a dedicated `LFDataLakeAdmin` role with scoped
  Lake Formation and Glue permissions.
- **Multiple admins are supported.** Register at least 2 for
  operational redundancy.

### Step 2: Create LF-tag keys and values

```bash
aws lakeformation create-lf-tag \
  --tag-key environment \
  --tag-values production staging dev

aws lakeformation create-lf-tag \
  --tag-key department \
  --tag-values finance engineering marketing

aws lakeformation create-lf-tag \
  --tag-key sensitivity \
  --tag-values public internal restricted pii
```

Rules:
- **Tag keys are immutable** — once created, a tag key cannot be
  renamed. Plan tag keys carefully.
- **Tag values can be added** — use `update-lf-tag` to add new values.
  Removing a value requires updating all resources and grants that
  reference it first.
- **NEVER create more than 5-7 tag keys.** Too many keys make the
  permission model unmaintainable. Use a small set of
  high-signal dimensions (environment, department, sensitivity).

### Step 3: Attach LF-tags to resources

```bash
# Attach LF-tags to a database
aws lakeformation add-lf-tags-to-resource \
  --resource '{"Database": {"Name": "analytics_db"}}' \
  --lf-tags '[{"TagKey": "environment", "TagValues": ["production"]}, {"TagKey": "department", "TagValues": ["finance"]}]'

# Attach LF-tags to a table
aws lakeformation add-lf-tags-to-resource \
  --resource '{"Table": {"DatabaseName": "analytics_db", "Name": "transactions"}}' \
  --lf-tags '[{"TagKey": "environment", "TagValues": ["production"]}, {"TagKey": "department", "TagValues": ["finance"]}, {"TagKey": "sensitivity", "TagValues": ["restricted"]}]'

# Attach LF-tags to specific columns
aws lakeformation add-lf-tags-to-resource \
  --resource '{"TableWithColumns": {"DatabaseName": "analytics_db", "Name": "transactions", "ColumnNames": ["ssn", "credit_card"]}}' \
  --lf-tags '[{"TagKey": "sensitivity", "TagValues": ["pii"]}]'
```

Rules:
- **Database-level tags are inherited by tables** — a table inherits
  its database's LF-tags unless overridden at the table level.
- **Column-level tags override table-level tags** — use column tags
  for PII or sensitive columns that need different access from the
  table.
- **NEVER skip LF-tags on resources.** Without LF-tags, tag-based
  grants match nothing and principals receive zero access.

### Step 4: Grant LF-tag-based permissions to principals

```bash
# Grant SELECT on all tables matching LF-tag expression
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/AnalyticsTeamRole"}' \
  --permissions SELECT DESCRIBE \
  --permissions-with-grant-option \
  --resource '{"LFTagPolicy": {"ResourceType": "TABLE", "Expression": [{"TagKey": "environment", "TagValues": ["production"]}, {"TagKey": "department", "TagValues": ["finance"]}]}}'

# Grant on database
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/AnalyticsTeamRole"}' \
  --permissions DESCRIBE ALTER \
  --resource '{"Database": {"Name": "analytics_db"}}'
```

Rules:
- **LF-tag-based grants are dynamic** — when new tables matching the
  LF-tag expression are added, the principal automatically receives
  access. No re-grant needed.
- **`DESCRIBE` is required for the principal to see the table in
  catalog queries** — grant SELECT + DESCRIBE together.
- **`permissions-with-grant-option`** — only grant if the principal
  should delegate access. NEVER use grant-option for end-user roles.

### Step 5: Column-level security (column grant and deny)

```bash
# Grant SELECT on specific columns only (PII columns EXCLUDED)
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/AnalyticsTeamRole"}' \
  --permissions SELECT \
  --resource '{"TableWithColumns": {"DatabaseName": "analytics_db", "Name": "transactions", "ColumnNames": ["transaction_id", "amount", "currency", "timestamp", "merchant"]}}'

# Explicit DENY on PII columns (stronger than column grant exclusion)
aws lakeformation batch-revoke-permissions \
  --entries '[{
    "Id": "deny-pii",
    "Principal": {"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/AnalyticsTeamRole"},
    "Permissions": ["SELECT"],
    "Resource": {"TableWithColumns": {"DatabaseName": "analytics_db", "Name": "transactions", "ColumnNames": ["ssn", "credit_card"]}}
  }]'
```

Rules:
- **Column grant is additive within the table.** If the principal has
  table-level SELECT and column-level SELECT on a subset, the
  effective access is the column-level subset (most restrictive).
- **Explicit deny via `batch-revoke-permissions`** removes a previously
  granted permission. Use for PII columns that should NEVER be
  accessible by a principal.
- **NEVER rely on column grant alone for PII protection.** Use data
  cells filter (Step 7) for row-level + column-level enforcement.

### Step 6: Resource links (cross-database access)

Resource links allow a table in one database to be referenced from
another database. This enables cross-database queries in Athena,
Redshift Spectrum, and EMR without granting direct access to the
source database.

```bash
# Create a resource link in the target database pointing to the source table
aws lakeformation create-resource-link \
  --resource-link-input '{
    "Name": "finance_transactions_link",
    "DatabaseName": "reporting_db",
    "TableIdentifier": "transactions"
  }'

# Grant DESCRIBE on the resource link to the principal
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/ReportingTeamRole"}' \
  --permissions DESCRIBE \
  --resource '{"Table": {"DatabaseName": "reporting_db", "Name": "finance_transactions_link", "CatalogId": "123456789012"}}'

# Grant SELECT on the underlying target table (via LF-tag or named resource)
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/ReportingTeamRole"}' \
  --permissions SELECT \
  --resource '{"Table": {"DatabaseName": "analytics_db", "Name": "transactions", "CatalogId": "123456789012"}}'
```

Rules:
- **Resource links are separate from the underlying table.** The
  principal needs DESCRIBE on the link AND SELECT on the target table.
  Granting only the link gives "table not found" errors.
- **Resource links do not copy LF-tags.** The link is a pointer; the
  target table's LF-tags control access.
- **Cross-account resource links** require RAM resource share in
  addition to the resource link. NEVER create cross-account links
  without a RAM share.

### Step 7: Data cells filter (row-level and column-level security)

Data cells filter enables row-level and column-level access control
on a single table. It is more expressive than column grants — it
supports row filter conditions (e.g., `region = 'us-east-1'`).

```bash
# Create the data cells filter
aws lakeformation create-data-cells-filter \
  --table-data '{
    "TableCatalogId": "123456789012",
    "DatabaseName": "analytics_db",
    "TableName": "transactions",
    "Name": "regional_access_filter",
    "RowFilter": {
      "FilterExpression": "region = '\''us-east-1'\''",
      "AllRowsWildcard": {}
    },
    "ColumnNames": ["transaction_id", "amount", "currency", "timestamp", "merchant", "region"],
    "ColumnWildcard": {"ExcludedColumnNames": ["ssn", "credit_card"]},
    "VersionId": "1"
  }'

# Grant access to the data cells filter
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/RegionalAnalystRole"}' \
  --permissions SELECT \
  --resource '{"DataCellsFilter": {"DatabaseName": "analytics_db", "TableName": "transactions", "Name": "regional_access_filter", "CatalogId": "123456789012"}}'
```

Rules:
- **Data cells filter is the most fine-grained permission layer.** It
  restricts both rows (via `FilterExpression`) and columns (via
  `ColumnNames` or `ColumnWildcard.ExcludedColumnNames`).
- **A table can have multiple filters.** Each principal receives
  access to one filter. Use different filters for different access
  patterns (regional, departmental, role-based).
- **NEVER use `AllRowsWildcard` without a `FilterExpression`.** That
  defeats the purpose of row-level security — it grants access to all
  rows with only column-level filtering.

### Step 8: IAM Identity Center integration (latest)

Identity Center integration walkthrough and rules moved verbatim to
[references/advanced-patterns.md](references/advanced-patterns.md).

### Step 9: LF-tags with Amazon DataZone (latest)

DataZone LF-tag integration walkthrough and rules moved verbatim to
[references/advanced-patterns.md](references/advanced-patterns.md).

### Step 10: Verification

Account-specific verification command block moved verbatim to
[references/cli-commands-and-iac.md](references/cli-commands-and-iac.md).

## Recent AWS features (2024-2026)

The 2024-2026 feature notes moved verbatim to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Workload matrix

| Workload | Permission model | Column security | Resource links | Identity Center | DataZone |
|---|---|---|---|---|---|
| **Production analytics (LF-tags)** | LF-tag-based | Column grant (PII excluded) | Optional | Yes | Optional |
| **PII-restricted access** | Named resource + data cells filter | Column deny + row filter | No | Optional | No |
| **Cross-database reporting** | LF-tag-based + resource links | Column grant | Yes | Optional | Optional |
| **Self-service marketplace** | LF-tag-based via DataZone subscription | Column grant | No | Yes | Yes |
| **Legacy IAM migration** | Hybrid access mode | IAM policy + LF overlay | Optional | Optional | No |
| **Multi-account data lake** | LF-tag-based + RAM share | Column grant | Cross-account | Optional | Optional |
| **Dev/test access** | Named resource (specific tables) | Column grant | No | Optional | No |

## NEVER (top 5 — full list of 12 in references)

- NEVER grant Lake Formation permissions without a registered data
  lake admin. Without an admin, LF-tag creation and permission grants
  fail with `AccessDeniedException`. The data lake admin is the #1
  prerequisite.
- NEVER use `AdministratorAccess` IAM role as the data lake admin.
  Use a dedicated `LFDataLakeAdmin` role with scoped Lake Formation
  and Glue permissions. A broad admin role is a privilege escalation
  vector.
- NEVER grant table-level SELECT to a principal that should only see
  non-PII columns. Use column-level grants or data cells filter to
  restrict access. Table-level SELECT grants access to ALL columns
  including PII.
- NEVER create LF-tag-based grants without attaching LF-tags to
  resources first. The grant matches nothing and the principal
  receives zero access — a silent failure that is hard to debug.
- NEVER mix IAM role principals and Identity Center principals for
  the same access pattern. Choose one model per access pattern to
  avoid permission conflicts and auditing confusion.


## Pre-flight safety checks (run before any deployment CLI)

- **Confirm a data lake admin is registered.**
- **Confirm the target Glue database and tables exist.**
- **Confirm the IAM principal (role, user, or Identity Center group)
  exists.**
- **Confirm S3 data locations are registered in Lake Formation.**
- **Confirm LF-tag keys are created before attaching to resources.**
- **Confirm LF-tags are attached to resources before granting
  tag-based permissions.**
- **Confirm the Identity Center instance is enabled (if SSO
  integration).**
- **Confirm the DataZone domain exists (if DataZone integration).**
- **Confirm the target database exists for resource link creation.**
- **For hybrid access mode, confirm the table is enabled for both
  Lake Formation and IAM.**

Full CLI sequences for all checks in
`references/lf-tags-and-column-security-guide.md`.

## Output format — MANDATORY literal labels

When invoked with a Lake Formation permissions deployment request,
your ENTIRE response MUST be the checklist block below. The labels
are **case-sensitive all-caps keywords**. Do NOT write a preamble.
Start with `PERMISSION_DEPLOYMENT:` and stop after the
`VERIFICATION_COMMANDS:` block.

```text
PERMISSION_DEPLOYMENT: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Data lake admin — <admin-principal-arn> (registered)
  [✓]      LF-tag keys — <tag-key-1> (values: <v1>, <v2>), <tag-key-2> (values: <v1>)
  [✓]      LF-tag on database — <database>: <tag-key>=<value>
  [✓]      LF-tag on table — <table>: <tag-key>=<value>
  [✓]      Principal — <principal-arn>
  [✓]      LF-tag-based grant — <permissions> on LF-tags: <expression>
  [✓]      Column-level security — <grant|deny> on columns [<column-list>]
  [✓]      Resource links — <link-name> for table <database>.<table>
  [OPTIONAL] Data cells filter — row filter <expression> on table <table>
  [OPTIONAL] IAM Identity Center — SSO group <group-arn> (configured | not configured)
  [OPTIONAL] Amazon DataZone — subscription <subscription-name> (configured | not configured)
  [✓]      Tags — <tags>
VERIFICATION_COMMANDS:
  aws lakeformation list-permissions --principal <principal-arn>
  aws lakeformation get-resource-lf-tags --resource '{"Database": {"Name": "<database>"}}'
  aws lakeformation list-lf-tags
  aws lakeformation describe-resource --resource-arn <table-arn>
```

**Status marker semantics:**
- `[✓]` — applied and verified.
- `[✗]` — NOT applied or misconfigured. Cite the gap.
- `[OPTIONAL]` — recommended but not required.
- `[INPUT NEEDED]` — prerequisite value missing; operator must provide.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite is
missing (data lake admin, target database/tables, IAM principal, S3
location registration), the verdict is `PREREQUISITES_MISSING`.

## References (load on demand)

- [references/cli-commands-and-iac.md](references/cli-commands-and-iac.md) — full copy-pasteable CLI sequence for all 10 deployment steps and Terraform/CloudFormation equivalents; now also the account-specific Step 10 verification commands moved from SKILL.md.
- [references/lf-tags-and-column-security-guide.md](references/lf-tags-and-column-security-guide.md) — LF-tag strategy and design, column-level security patterns, data cells filter conditions, resource links, hybrid access mode, Identity Center principal mapping, DataZone integration, full NEVER list, pre-flight safety CLI; now also the edge-case handling catalog moved from SKILL.md.
- [references/advanced-patterns.md](references/advanced-patterns.md) — IAM Identity Center and DataZone deployment deep dives (Steps 8-9), Recent AWS features detail, and the LF-tag/column-security/migration expert heuristics moved from SKILL.md.

## Domain

AWS CloudOps / Lake Formation Data Lake Governance Provisioning.


## AWS documentation

- **Lake Formation Developer Guide** — https://docs.aws.amazon.com/lake-formation/latest/dg/what-is-lake-formation.html
- **GrantPermissions API** — https://docs.aws.amazon.com/lake-formation/latest/APIReference/API_GrantPermissions.html
- **LF-tag based access control** — https://docs.aws.amazon.com/lake-formation/latest/dg/security-lf-tag-based-access-control.html
- **Column-level security** — https://docs.aws.amazon.com/lake-formation/latest/dg/column-level-security.html
- **Data cells filter** — https://docs.aws.amazon.com/lake-formation/latest/dg/data-cells-filter.html
- **Resource links** — https://docs.aws.amazon.com/lake-formation/latest/dg/resource-links.html
- **IAM Identity Center integration** — https://docs.aws.amazon.com/lake-formation/latest/dg/iam-idc.html
- **Amazon DataZone integration** — https://docs.aws.amazon.com/lake-formation/latest/dg/datazone-integration.html
- **Hybrid access mode** — https://docs.aws.amazon.com/lake-formation/latest/dg/hybrid-access-mode.html
- **Lake Formation CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/lakeformation/

## References

- `references/cli-commands-and-iac.md` — full copy-pasteable CLI command
  sequence for all 10 deployment steps, including data lake admin
  registration, LF-tag creation, LF-tag attachment to resources,
  LF-tag-based permission grants, column-level security grants and
  denies, resource link creation for cross-database access, data cells
  filter creation, IAM Identity Center integration, DataZone
  subscription, and Terraform / CloudFormation equivalents.

- `references/lf-tags-and-column-security-guide.md` — deep reference on
  LF-tag strategy and design, column-level security patterns, data
  cells filter row-level conditions, resource link cross-database
  access, hybrid access mode migration, IAM Identity Center principal
  mapping, DataZone LF-tag integration, full NEVER list, edge-case
  handling, and pre-flight safety CLI.
