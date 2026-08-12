---
name: s3-table-bucket-deployer
description: >-
  Provisions Amazon S3 Tables (table buckets) with production defaults:
  table bucket creation (create-table-bucket), namespace management
  (create-namespace), table creation in Apache Iceberg format
  (create-table with schema, partition spec), table maintenance
  configuration (compaction, snapshot management, unreferenced file
  cleanup), table bucket policy (separate from regular S3 object bucket
  policy), Apache Iceberg REST catalog endpoint for Athena integration,
  Lake Formation integration for fine-grained access control, table
  format version (Iceberg v2 for row-level deletes), partitioning
  strategy alignment with query patterns, S3 table bucket vs regular S3
  bucket distinction (purpose-built for tabular data), and Apache
  Iceberg features (time travel, schema evolution, ACID transactions).
  Emits a READY_TO_DEPLOY checklist with verification commands. Use when
  creating an S3 table bucket, managing namespaces, creating an Iceberg
  table in S3 Tables, configuring table maintenance, applying a table
  bucket policy, integrating Athena with S3 Tables, or setting up Lake
  Formation permissions on table bucket resources. Triggers: create s3
  table bucket, s3 tables namespace, iceberg table s3, s3 table
  maintenance compaction, s3 table bucket policy, iceberg rest catalog
  athena, lake formation s3 tables, s3 table partition spec.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with s3tables access
  (and Lake Formation / Athena workgroup permissions for integration
  steps). Works with Terraform aws_s3tables_table_bucket /
  aws_s3tables_namespace / aws_s3tables_table resources and
  CloudFormation AWS::S3Tables::TableBucket /
  AWS::S3Tables::Table templates.
keywords:
  - aws
  - s3 tables
  - table bucket
  - apache iceberg
  - cloudops
  - deploy
  - provisioning
  - namespace
  - compaction
  - snapshot management
  - table bucket policy
  - iceberg rest catalog
  - athena
  - lake formation
  - schema evolution
  - time travel
  - acid transactions
tags:
  - aws
  - s3-tables
  - table-bucket
  - apache-iceberg
  - cloudops
  - deploy
  - storage
  - provisioning
  - compaction
  - lake-formation
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Storage
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - s3-tables
    - table-bucket
    - apache-iceberg
    - cloudops
    - deploy
    - storage
    - provisioning
    - compaction
    - lake-formation
  dependencies:
    - aws-orchestrator
  keywords:
    - create s3 table bucket
    - s3 tables namespace
    - iceberg table s3
    - s3 table maintenance compaction
    - s3 table bucket policy
    - iceberg rest catalog athena
    - lake formation s3 tables
    - s3 table partition spec
  when_to_use: >-
    Invoke when the user wants to create an Amazon S3 table bucket,
    manage namespaces within a table bucket, create an Apache Iceberg
    table in S3 Tables, configure table maintenance (compaction, snapshot
    management, unreferenced file cleanup), apply a table bucket policy,
    integrate Athena with S3 Tables via the Iceberg REST catalog, or set
    up Lake Formation permissions on table bucket resources. Do NOT
    invoke for regular S3 bucket operations (standard object storage),
    S3 Glacier, or DynamoDB. For general-purpose object storage use the
    standard S3 bucket skills.
---

# S3 Table Bucket Deployer

An AWS CloudOps agent skill that provisions Amazon S3 Tables (table
buckets) with correct defaults. The skill walks the operator through
table bucket creation, namespace management, Iceberg table creation
with schema and partition spec, maintenance configuration (compaction,
snapshot management, unreferenced file cleanup), table bucket policy
(separate from regular S3 bucket policy), Iceberg REST catalog setup
for Athena, Lake Formation integration, table format versioning, and
partitioning strategy, captures all configuration decisions, explains
why each default matters, and emits a READY_TO_DEPLOY checklist with
copy-pasteable verification commands.

## Activation keywords

create S3 table bucket, S3 Tables namespace, Iceberg table S3, S3
table maintenance compaction, S3 table bucket policy, Iceberg REST
catalog Athena, Lake Formation S3 Tables, S3 table partition spec.

## STRICT output contract

When this skill is invoked with an S3-Tables-provisioning request
(create a table bucket, create a namespace, create an Iceberg table,
configure maintenance, apply a table bucket policy, integrate Athena,
or a partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section using
the literal all-caps labels `S3_TABLES:`, `VERDICT:`, `CHECKLIST:`,
and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Table bucket creation | Core bucket provisioning |
| Step 2 — Namespace management | Namespace before table (hard dependency) |
| Step 3 — Table creation (Apache Iceberg format) | Provisioning step |
| Step 4 — Table schema (column types, partition spec) | Schema design |
| Step 5 — Table maintenance (compaction, snapshot, cleanup) | Auto-maintenance config |
| Step 6 — Table bucket policy (separate from object bucket policy) | Access control |
| Step 7 — Iceberg REST API + Athena integration | Query engine integration |
| Step 8 — Lake Formation integration | Fine-grained access control |
| Step 9 — Table format version and partitioning strategy | Iceberg v2, partition design |
| Step 10 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/maintenance-and-iceberg.md | Maintenance + Iceberg detail |
| references/table-bucket-policy-and-integrations.md | Policy + Athena/LF detail |

## Mindset

**One-line takeaway:** An S3 table bucket is a purpose-built container
for Apache Iceberg tables — NOT a general-purpose S3 bucket. You cannot
store arbitrary objects in it. Namespaces must exist before tables.
Table bucket policy is a SEPARATE policy type from the regular S3 bucket
policy. Athena reads S3 Tables via the Iceberg REST catalog endpoint,
not via direct S3 paths. Maintenance (compaction, snapshot management,
unreferenced file cleanup) is enabled by default and configurable.

Three misconceptions dominate S3 Tables misdesign at provisioning time:

- **"A table bucket is just a regular S3 bucket with a different name."**
  It is NOT. A table bucket is a distinct resource type optimized for
  tabular data. You cannot use standard S3 APIs (PutObject, GetObject,
  ListObjects) on it. Table buckets use the `s3tables` API namespace,
  not the `s3` namespace. Regular S3 bucket policies do NOT apply —
  table buckets have their own policy type via
  `put-table-bucket-policy`.

- **"I can create a table directly in a table bucket without a
  namespace."** You CANNOT. The hierarchy is: table bucket → namespace
  → table. A namespace must exist before any table can be created in
  it. This is a hard API dependency — `create-table` fails if the
  namespace does not exist.

- **"Athena can query S3 Tables by pointing at the S3 bucket path."**
  It CANNOT. Athena accesses S3 Tables through the Apache Iceberg REST
  catalog endpoint, not by specifying an S3 path. The REST catalog
  provides the table metadata that Athena needs to read Iceberg data
  files. Lake Formation governs access to these tables for fine-grained
  permission control.

## Configuration dependency graph (novel heuristic)

S3 Tables configurations are NOT independent. The namespace must exist
before the table. Maintenance configuration is per-table. Table bucket
policy is separate from any regular S3 bucket policy. Athena needs the
REST catalog, not an S3 path. Use this graph to sequence provisioning.

| Configuration | Hard dependencies | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Table bucket | S3 Tables access enabled | cannot convert regular bucket; region-unique name | container for namespaces/tables |
| Namespace | table bucket exists | immutable name; max 100 per bucket | table creation |
| Table (Iceberg) | namespace exists; format=ICEBERG | v1/v2 chosen at creation; schema evolvable | data ingestion, queries |
| Table schema | table exists | Iceberg types; partition spec refs schema columns | query planning |
| Maintenance config | table exists | all 3 types ENABLED by default; per-table | performance optimization |
| Table bucket policy | table bucket exists | uses `put-table-bucket-policy` (NOT `s3:put-bucket-policy`) | cross-account access |
| Athena integration | table exists; REST catalog configured | workgroup must reference REST catalog; LF grants needed | SQL query access |
| Lake Formation | table exists; LF enabled | governs table/column access; without grants Athena fails | fine-grained access |

**The namespace-before-table row is the one a baseline model misses.**
Creating the table bucket is necessary but NOT sufficient. The namespace
must be created as an explicit step. The procedure below forces this
ordering.

**Critical cross-dependencies:** table bucket policy uses
`put-table-bucket-policy` (NOT `s3api put-bucket-policy`). Maintenance
is per-table, not per-bucket. Iceberg v2 (chosen at creation) enables
row-level deletes. Athena requires the REST catalog, not S3 paths.

## Expert heuristic: table bucket vs regular S3 bucket

A baseline model conflates table buckets with regular S3 buckets. S3
Tables is a purpose-built container for tabular data with a completely
separate API surface.

```text
Regular S3 Bucket          | S3 Table Bucket
s3:* APIs                  | s3tables:* APIs
Arbitrary objects          | Apache Iceberg tables ONLY
s3:PutBucketPolicy         | s3tables:PutTableBucketPolicy (SEPARATE)
Athena via S3 path         | Athena via Iceberg REST catalog endpoint
Manual compaction jobs     | Built-in auto-maintenance
```

**Key implication:** do NOT use standard S3 CLI commands on a table
bucket. Use `aws s3tables` exclusively with `s3tables:*` IAM
permissions.

## Expert heuristic: maintenance automation is on by default

S3 Tables provides three automatic maintenance types for every Iceberg
table, all ENABLED by default: **compaction** (merges small files into
larger ones, ~512 MB target), **snapshot management** (expires old
snapshots, controls metadata growth), and **unreferenced file cleanup**
(removes orphaned data files, reclaims storage). All are per-table
configurable. Unlike self-managed Iceberg on S3, you do NOT need to
build or operate separate compaction jobs. The decision is whether to
keep defaults or tune settings per workload. Disabling is possible but
almost always wrong for production.

## Expert heuristic: Athena reads via REST catalog, not S3 paths

A baseline model points Athena at the S3 bucket path. Athena actually
accesses S3 Tables through the Apache Iceberg REST catalog endpoint:
S3 Table Bucket provisions the REST catalog, the Athena workgroup
references it, Lake Formation grants permissions to the query role,
and queries use `namespace.table` notation. Without the REST catalog,
Athena returns "table not found." The S3 path is irrelevant.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | How to verify |
|---|---|
| S3 Tables available in account/region | `aws s3tables list-table-buckets --region <region>` |
| Table bucket name unique | Check naming rules (3-63 chars, lowercase, hyphens) |
| Namespace name planned | Must exist before table creation |
| Table schema defined (columns + Iceberg types) | Define columns at creation |
| Partition strategy decided | Assess query patterns for partition columns |
| Iceberg format version decided | v2 (recommended) vs v1 (append-only) |
| IAM permissions for `s3tables:*` | Verify `s3tables:CreateTableBucket`, etc. |
| Athena workgroup exists (if querying) | REST catalog configuration needed |
| Lake Formation enabled (if using LF) | LF governs table/column-level access |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Table bucket creation

An S3 table bucket is the top-level container for Iceberg tables. It
is created via the `s3tables` API, not the standard S3 API.

```bash
# Create a table bucket
aws s3tables create-table-bucket \
  --name analytics-tables \
  --region us-east-1

# The table bucket ARN format:
# arn:aws:s3tables:us-east-1:123456789012:bucket/analytics-tables
```

**Naming:** 3-63 chars, lowercase letters/numbers/hyphens, must start
and end with a letter or number, unique within region.

**Limits:** 100 table buckets per account, 100 namespaces per bucket,
10,000 tables per namespace (all soft limits).

**Common mistake:** using `aws s3api create-bucket`. Table buckets
require `aws s3tables create-table-bucket`.

## Step 2 — Namespace management

Namespaces are logical groupings within a table bucket. A namespace
must exist before any table can be created in it.

```bash
TABLE_BUCKET_ARN="arn:aws:s3tables:us-east-1:123456789012:bucket/analytics-tables"

# Create a namespace
aws s3tables create-namespace \
  --table-bucket-arn "$TABLE_BUCKET_ARN" \
  --namespace '{"namespace": ["sales_analytics"]}' \
  --region us-east-1

# List namespaces in the table bucket
aws s3tables list-namespaces \
  --table-bucket-arn "$TABLE_BUCKET_ARN" \
  --region us-east-1
```

**Naming:** 1-255 chars, alphanumeric/underscores/hyphens. Can be
hierarchical with dot notation (e.g., `sales.us_east`).

**Common mistake:** skipping namespace creation. `create-table` fails
with a namespace-not-found error.

## Step 3 — Table creation (Apache Iceberg format)

Tables are created within namespaces. S3 Tables currently supports
Apache Iceberg as the table format. The table metadata (schema,
partition spec) is provided at creation time.

```bash
# Create an Iceberg table with schema and partition spec
aws s3tables create-table \
  --table-bucket-arn "$TABLE_BUCKET_ARN" \
  --namespace sales_analytics \
  --name orders \
  --format ICEBERG \
  --metadata '
  {
    "iceberg": {
      "schema": {
        "type": "struct",
        "fields": [
          {"id": 1, "name": "order_id", "type": "long", "required": true},
          {"id": 2, "name": "customer_id", "type": "long", "required": true},
          {"id": 3, "name": "order_date", "type": "timestamp", "required": true},
          {"id": 4, "name": "amount", "type": "double", "required": false},
          {"id": 5, "name": "status", "type": "string", "required": false}
        ]
      },
      "partition-spec": [
        {"name": "order_date_day", "transform": "day", "source-id": 3}
      ],
      "format-version": 2
    }
  }
  ' \
  --region us-east-1
```

**Key decisions at creation:**
- **Format version:** v2 recommended (row-level deletes, upserts,
  MERGE INTO). v1 = append-only.
- **Schema:** Iceberg column types. Evolvable (add columns later).
- **Partition spec:** columns + transforms. Affects performance.

**Verify the table was created:**

```bash
aws s3tables get-table \
  --table-bucket-arn "$TABLE_BUCKET_ARN" \
  --namespace sales_analytics \
  --name orders \
  --region us-east-1
```

## Step 4 — Table schema (column types, partition spec)

The Iceberg schema defines columns with types. The partition spec
determines how data is physically organized.

### Iceberg column types

| Type | Description |
|---|---|
| `boolean`, `int`, `long`, `float`, `double` | Primitives |
| `decimal(p,s)` | Fixed precision (financial) |
| `string` | UTF-8 text |
| `timestamp`, `timestamptz` | Microsecond timestamps (with/without tz) |
| `date`, `time` | Date and time-of-day |
| `bytes` | Binary data |
| `struct`, `list`, `map` | Nested/complex types |

### Partition spec transforms

| Transform | Example |
|---|---|
| `identity` | Partition by `status` directly |
| `year`, `month`, `day`, `hour` | Time-based partitioning from timestamp/date |
| `bucket[N]` | Hash into N buckets (high-cardinality columns) |
| `truncate[W]` | Truncate to width W |

### Partition strategy

```text
Time-series (WHERE date > ...)     → day(timestamp) or month(timestamp)
Category filter (WHERE region=...) → identity(low-card column)
High-cardinality lookup            → bucket[16-32](column)
Composite geo-temporal             → day(date) + truncate(region)
AVOID: identity on >10K distinct values (small file problem)
```

**Rule of thumb:** target at least 100 MB per partition. Too many
partitions = small files = slow. Too few = full scans = wasted I/O.

## Step 5 — Table maintenance (compaction, snapshot management, cleanup)

S3 Tables provides three automatic maintenance types, all ENABLED by
default. Each is configurable per-table.

### View current maintenance configuration

```bash
aws s3tables get-table-maintenance-configuration \
  --table-bucket-arn "$TABLE_BUCKET_ARN" \
  --namespace sales_analytics \
  --name orders \
  --region us-east-1
```

### Configure compaction

Compaction merges small data files into larger ones, reducing metadata
overhead and improving query performance.

```bash
aws s3tables update-table-maintenance-configuration \
  --table-bucket-arn "$TABLE_BUCKET_ARN" \
  --namespace sales_analytics --name orders \
  --type compaction \
  --value '{"status":"ENABLED","settings":{"targetFileSize":"536870912","minInputFiles":5,"maxInputFiles":100}}' \
  --region us-east-1
```

### Configure snapshot management

Expires old Iceberg snapshots to control metadata growth.

```bash
aws s3tables update-table-maintenance-configuration \
  --table-bucket-arn "$TABLE_BUCKET_ARN" \
  --namespace sales_analytics --name orders \
  --type snapshot-management \
  --value '{"status":"ENABLED","settings":{"maxSnapshotAge":"604800","minSnapshots":5}}' \
  --region us-east-1
```

### Configure unreferenced file cleanup

Removes data files no longer referenced by any snapshot, reclaiming
storage.

```bash
aws s3tables update-table-maintenance-configuration \
  --table-bucket-arn "$TABLE_BUCKET_ARN" \
  --namespace sales_analytics --name orders \
  --type unreferenced-file-removal \
  --value '{"status":"ENABLED","settings":{"maxFileAge":"2592000"}}' \
  --region us-east-1
```

**Critical:** disabling maintenance is almost always the wrong choice
for production. S3 Tables automates this — keep it enabled.

## Step 6 — Table bucket policy (separate from object bucket policy)

Table bucket policy is a DISTINCT policy type from regular S3 bucket
policy. Use `put-table-bucket-policy`, NOT `s3api put-bucket-policy`.

```bash
# Put a table bucket policy
aws s3tables put-table-bucket-policy \
  --table-bucket-arn "$TABLE_BUCKET_ARN" \
  --resource-policy '
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::999999999999:root"
        },
        "Action": [
          "s3tables:GetTableBucket",
          "s3tables:ListNamespaces",
          "s3tables:ListTables",
          "s3tables:GetTable",
          "s3tables:GetNamespace"
        ],
        "Resource": "arn:aws:s3tables:us-east-1:123456789012:bucket/analytics-tables/*"
      }
    ]
  }
  ' \
  --region us-east-1
```

**Verify the policy:**

```bash
aws s3tables get-table-bucket-policy \
  --table-bucket-arn "$TABLE_BUCKET_ARN" \
  --region us-east-1
```

**Key distinction:** regular S3 uses `s3:PutBucketPolicy` /
`aws s3api put-bucket-policy` with `s3:*` actions. Table buckets use
`s3tables:PutTableBucketPolicy` / `aws s3tables put-table-bucket-policy`
with `s3tables:*` actions. The policy targets table bucket resources
(namespaces, tables), not individual objects.

**Common mistake:** using `aws s3api put-bucket-policy` on a table
bucket — fails or applies to the wrong resource type.

## Step 7 — Iceberg REST API + Athena integration

Athena accesses S3 Tables via the Apache Iceberg REST catalog
endpoint, NOT by specifying an S3 path. The REST catalog provides the
Iceberg table metadata that Athena needs to plan and execute queries.

### How the REST catalog works

```text
S3 Table Bucket → provisions Iceberg REST catalog
  → Athena workgroup references REST catalog
  → Query: SELECT * FROM ns.table
  → Athena calls REST catalog for metadata → reads data files
```

### Configuring Athena

```bash
# Verify Athena can see the table via the REST catalog
aws athena start-query-execution \
  --query-string "SHOW TABLES IN sales_analytics" \
  --work-group primary \
  --query-execution-context Database=sales_analytics \
  --result-configuration OutputLocation=s3://query-results-bucket/athena/ \
  --region us-east-1
```

### Querying Iceberg features via Athena

```sql
-- Time travel: query a previous snapshot
SELECT * FROM sales_analytics.orders
FOR SYSTEM_TIME AS OF TIMESTAMP '2026-08-01 00:00:00';

-- Schema evolution (metadata-only, no rewrite)
ALTER TABLE sales_analytics.orders ADD COLUMNS (discount double);

-- ACID UPDATE (requires Iceberg v2)
UPDATE sales_analytics.orders SET status = 'shipped' WHERE order_id = 12345;
```

Without the REST catalog, Athena returns "table not found." The S3
path is NOT used for Athena access to S3 Tables.

## Step 8 — Lake Formation integration

Lake Formation provides fine-grained access control (table-level and
column-level) for S3 Tables resources. Without Lake Formation grants,
Athena queries fail with access denied.

```bash
# Grant table-level access via Lake Formation
aws lakeformation grant-permissions \
  --principal DataLakePrincipalIdentifier=arn:aws:iam::123456789012:role/AthenaUserRole \
  --permissions SELECT DESCRIBE \
  --resource '{"Table": {"DatabaseName": "sales_analytics", "Name": "orders"}}' \
  --region us-east-1

# Grant column-level access (fine-grained)
aws lakeformation grant-permissions \
  --principal DataLakePrincipalIdentifier=arn:aws:iam::123456789012:role/AthenaUserRole \
  --permissions SELECT \
  --resource '{
    "TableWithColumns": {
      "DatabaseName": "sales_analytics",
      "Name": "orders",
      "ColumnWildcard": {}
    }
  }' \
  --region us-east-1
```

**Lake Formation requirements:** LF must be enabled, the S3 Tables
catalog registered as a data source, and the Athena query role must
have LF grants for queried tables/columns. Without grants, Athena
returns "Insufficient Lake Formation permissions."

## Step 9 — Table format version and partitioning strategy

### Iceberg format version

| Feature | v1 | v2 |
|---|---|---|
| Append / overwrite | Yes | Yes |
| Row-level deletes (UPDATE, DELETE, MERGE INTO) | No | Yes |

**Recommendation:** use v2 for all new tables (superset of v1). Choose
v1 only if downstream tools lack v2 support or the table is strictly
append-only.

### Partitioning strategy

```text
Good: day(timestamp), month(timestamp), bucket[16](id), day(date)+truncate(region)
Bad:  identity on >10K values, no partition on large tables, partition on never-filtered column
```

Target at least 100 MB per partition. Too small = small file problem.
Too few = full scans.

## Step 10 — Recent features

**Recent AWS features (2024-2026):**

- **S3 Tables general availability (2024-2025):** Amazon S3 Tables
  launched as purpose-built storage for tabular data using Apache
  Iceberg, with built-in maintenance and REST catalog integration.

- **Iceberg REST catalog for Athena (2024-2025):** Athena integration
  via the REST catalog endpoint, enabling SQL queries with time travel,
  schema evolution, and ACID support.

- **Lake Formation fine-grained access for S3 Tables (2024-2025):**
  Lake Formation integration for table-level and column-level
  permissions on S3 Tables resources, enabling centralized access
  governance.

- **Iceberg v2 row-level operations (2024-2025):** S3 Tables supports
  Iceberg v2 format with UPDATE, DELETE, and MERGE INTO operations
  for row-level mutations.

- **Cross-account table bucket policy (2024-2025):** Table bucket
  policies support cross-account access for sharing tables with other
  AWS accounts.

- **Terraform provider support (2024-2025):** The Terraform AWS
  provider added `aws_s3tables_table_bucket`,
  `aws_s3tables_namespace`, and `aws_s3tables_table` resources for
  infrastructure-as-code provisioning of S3 Tables.

## NEVER do these things

1. **NEVER use standard S3 APIs on a table bucket.** Table buckets use
   `aws s3tables` (not `aws s3`/`s3api`). IAM actions are `s3tables:*`,
   not `s3:*`.

2. **NEVER create a table without first creating the namespace.**
   Hierarchy: table bucket -> namespace -> table. `create-table` fails
   without a namespace.

3. **NEVER apply a regular S3 bucket policy to a table bucket.** Use
   `put-table-bucket-policy` with `s3tables:*` actions, not
   `s3api put-bucket-policy` with `s3:*` actions.

4. **NEVER point Athena at an S3 path for S3 Tables.** Athena uses the
   Iceberg REST catalog endpoint. S3 paths return "table not found."

5. **NEVER disable table maintenance without understanding the
   consequences.** Compaction, snapshot management, and file cleanup
   are ENABLED by default for good reason.

6. **NEVER use Iceberg v1 if you need row-level operations.** UPDATE,
   DELETE, MERGE INTO require v2.

7. **NEVER partition on a high-cardinality column without bucketing.**
   Use `bucket[N]` transform for high-cardinality columns.

8. **NEVER skip Lake Formation grants if LF is enabled.** Athena
   queries fail without LF grants on the table/columns.

9. **NEVER assume table buckets can store arbitrary objects.** They
   are purpose-built for Iceberg tables only.

10. **NEVER forget the region when listing table buckets.** They are
    region-scoped.

## Output format

```text
S3_TABLES: <table-bucket-name> / <namespace> / <table-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Table bucket: <bucket-name> (<bucket-arn>)
  [✓|✗] Namespace: <namespace>
  [✓|✗] Table: <table-name> (format: ICEBERG v<v1|v2>)
  [✓|✗] Schema: <column count> columns (<type list summary>)
  [✓|✗] Partition spec: <partition columns + transforms>
  [✓|✗] Maintenance — compaction: ENABLED (target <size>, min <n> files) | DISABLED
  [✓|✗] Maintenance — snapshot management: ENABLED (max <days>d, min <n>) | DISABLED
  [✓|✗] Maintenance — unreferenced file cleanup: ENABLED (max <days>d) | DISABLED
  [✓|✗] Table bucket policy: <applied | none>
  [✓|✗] Athena integration: REST catalog configured | Not configured
  [✓|✗] Lake Formation: grants applied (table-level | column-level) | Not configured
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws s3tables get-table --table-bucket-arn <arn> --namespace <ns> --name <table> --region <region>
  aws s3tables get-table-maintenance-configuration --table-bucket-arn <arn> --namespace <ns> --name <table> --region <region>
  aws s3tables get-table-bucket-policy --table-bucket-arn <arn> --region <region>
```

### Worked example — table bucket with Iceberg table and Athena

```text
S3_TABLES: analytics-tables / sales_analytics / orders
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Table bucket: analytics-tables (arn:aws:s3tables:us-east-1:123456789012:bucket/analytics-tables)
  [✓] Namespace: sales_analytics
  [✓] Table: orders (format: ICEBERG v2)
  [✓] Schema: 5 columns (long, long, timestamp, double, string)
  [✓] Partition spec: day(order_date)
  [✓] Maintenance — compaction: ENABLED (target 512MB, min 5 files)
  [✓] Maintenance — snapshot management: ENABLED (max 7d, min 5 snapshots)
  [✓] Maintenance — unreferenced file cleanup: ENABLED (max 30d)
  [✓] Table bucket policy: applied (cross-account read for 999999999999)
  [✓] Athena integration: REST catalog configured
  [✓] Lake Formation: grants applied (table-level SELECT for AthenaUserRole)
  [✓] Tags: Environment=production, Team=analytics
VERIFICATION_COMMANDS:
  aws s3tables get-table --table-bucket-arn arn:aws:s3tables:us-east-1:123456789012:bucket/analytics-tables --namespace sales_analytics --name orders --region us-east-1
  aws s3tables get-table-maintenance-configuration --table-bucket-arn arn:aws:s3tables:us-east-1:123456789012:bucket/analytics-tables --namespace sales_analytics --name orders --region us-east-1
  aws s3tables get-table-bucket-policy --table-bucket-arn arn:aws:s3tables:us-east-1:123456789012:bucket/analytics-tables --region us-east-1
```

## Error handling

### create-table fails with namespace not found
- The namespace does not exist. Create it first with
  `create-namespace`, then retry.

### put-table-bucket-policy fails
- Policy uses `s3:*` actions instead of `s3tables:*`. Rewrite with
  `s3tables:GetTable`, `s3tables:ListTables`, etc.

### Athena returns "table not found"
- Athena is not configured with the Iceberg REST catalog. Verify the
  workgroup references the REST catalog endpoint. Also verify Lake
  Formation grants exist.

### Athena returns "Insufficient Lake Formation permissions"
- Use `grant-permissions` to grant SELECT on the table to the query
  role.

### Table maintenance not running
- Check `get-table-maintenance-configuration`. May be DISABLED, or
  the table may not have enough data to trigger compaction (below
  minInputFiles threshold).

### Iceberg v1 table cannot do UPDATE/DELETE
- v1 does not support row-level operations. Create a new table with
  format-version 2 and migrate data.

## Domain

AWS CloudOps / Amazon S3 Tables Provisioning & Apache Iceberg Table
Management.

## AWS documentation

- **S3 Tables User Guide** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-tables.html
- **Creating table buckets** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/creating-table-buckets.html
- **Managing namespaces** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/managing-namespaces.html
- **Creating tables** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/creating-tables.html
- **Table maintenance** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/table-maintenance.html
- **Table bucket policies** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/table-bucket-policies.html
- **Iceberg REST catalog** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-tables-iceberg-rest-catalog.html
- **Athena integration** — https://docs.aws.amazon.com/athena/latest/ug/s3-tables.html
- **Lake Formation integration** — https://docs.aws.amazon.com/lake-formation/latest/dg/s3-tables.html
- **Apache Iceberg format** — https://iceberg.apache.org/spec/
