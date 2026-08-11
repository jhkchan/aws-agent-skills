---
name: quicksight-dashboard-deployer
description: >-
  Provisions Amazon QuickSight dashboards with production defaults:
  account creation (Standard/Enterprise), data source (Athena, RDS,
  Redshift, S3, Aurora), dataset (SQL, join, calculated field),
  analysis (visual types, sheet layout), dashboard creation and sharing,
  template-based deployment, row-level security (RLS via dataset
  permissions), SPICE vs Direct Query, VPC connection for private data
  stores, IAM service role, email-based user provisioning, namespace
  and groups, refresh schedules, parameterized dashboards. Emits a
  READY_TO_DEPLOY checklist with verification commands. Use when
  creating a QuickSight dashboard, connecting QuickSight to a data
  source, setting up SPICE ingestion, configuring row-level security,
  deploying multi-tenant dashboards, or provisioning QuickSight users.
  Triggers: create quicksight dashboard, quicksight data source,
  quicksight SPICE, quicksight template, quicksight row-level security,
  quicksight VPC connection, quicksight enterprise.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with quicksight access
  (and sts:AssumeRole if cross-account data sources). Works with
  Terraform aws_quicksight_* resources and CloudFormation
  AWS::QuickSight::* templates.
keywords:
  - aws
  - quicksight
  - dashboard
  - analytics
  - bi
  - cloudops
  - deploy
  - provisioning
  - spice
  - data source
  - dataset
  - analysis
  - template
  - row-level security
  - rls
  - vpc connection
  - enterprise
tags:
  - aws
  - quicksight
  - dashboard
  - analytics
  - cloudops
  - deploy
  - provisioning
  - spice
  - data-source
  - dataset
  - analysis
  - template
  - row-level-security
  - vpc-connection
  - enterprise
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Analytics
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - quicksight
    - dashboard
    - analytics
    - cloudops
    - deploy
    - provisioning
    - spice
    - data-source
    - dataset
    - analysis
    - template
    - row-level-security
    - vpc-connection
    - enterprise
  dependencies:
    - aws-orchestrator
  keywords:
    - create quicksight dashboard
    - quicksight data source
    - quicksight SPICE
    - quicksight template
    - quicksight row-level security
    - quicksight VPC connection
    - quicksight user provisioning
    - quicksight enterprise
  when_to_use: >-
    Invoke when the user wants to create a QuickSight dashboard, connect
    QuickSight to a data source (Athena, RDS, Redshift, S3, Aurora),
    configure SPICE ingestion vs Direct Query, set up row-level security,
    deploy template-based multi-tenant dashboards, provision QuickSight
    users and groups, or configure VPC connections for private data
    stores. Do NOT invoke for Amazon Athena workgroup management (use
    Athena skills), Redshift cluster provisioning (use Redshift skills),
    or general BI tool comparisons.
---

# QuickSight Dashboard Deployer

An AWS CloudOps agent skill that provisions Amazon QuickSight dashboards
with correct defaults. The skill walks the operator through account
creation and edition selection, data source connection, dataset
definition with SPICE or Direct Query, analysis and visual composition,
dashboard creation and sharing, template-based deployment for multi-
tenant scenarios, row-level security, VPC connections for private data
stores, IAM service roles, user and group provisioning, and dataset
refresh schedules — then captures all decisions and emits a
READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

create QuickSight dashboard, QuickSight data source, QuickSight SPICE,
QuickSight template, QuickSight row-level security, QuickSight VPC
connection, QuickSight user provisioning, QuickSight Enterprise.

## STRICT output contract

When this skill is invoked with a QuickSight-dashboard-provisioning
request (create a dashboard, connect a data source, set up SPICE,
configure RLS, deploy a template, provision users, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `QUICKSIGHT_DASHBOARD:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[x]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Account creation and edition | Account setup |
| Step 2 — Data source connection | Data store connectivity |
| Step 3 — Dataset (SQL, join, calculated field) | Data modeling |
| Step 4 — SPICE vs Direct Query | Ingestion mode decision |
| Step 5 — Analysis and dashboard creation | Visual composition + publishing |
| Step 6 — Template-based deployment | Multi-tenant dashboards |
| Step 7 — Row-level security (RLS) | Data access control |
| Step 8 — VPC connection and IAM role | Private connectivity + permissions |
| Step 9 — User provisioning, namespaces, groups | User management |
| Step 10 — Refresh schedule and parameters | Data freshness + dynamic filtering |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/spice-and-ingestion.md | SPICE detail |
| references/templates-and-rls.md | Template + RLS detail |

## Mindset

**One-line takeaway:** A QuickSight dashboard is a published, read-only
view of an analysis. The analysis is built on a dataset. The dataset is
backed by a data source. SPICE ingestion decouples query latency from
source-store load. Templates enable multi-tenant dashboard deployment.
RLS controls which rows each reader sees. The VPC connection bridges
QuickSight to private data stores.

Three misconceptions dominate QuickSight dashboard misdesign at
provisioning time:

- **"Direct Query gives real-time data, so always use it."** It does
  give fresh data, but at the cost of query latency and source-store
  load. SPICE caches data in-memory and serves sub-second queries
  without hitting the source. For dashboards with many concurrent
  viewers or complex joins, Direct Query overwhelms the source
  database. The default for most dashboards should be SPICE with a
  scheduled refresh.

- **"Sharing a dashboard grants data access."** It does not. Sharing a
  dashboard lets a reader view the published version. Row-level
  security is a SEPARATE configuration that controls which rows each
  reader sees. Without RLS, every reader sees all data in the dataset.

- **"Templates are just for reuse."** Templates are the primary
  mechanism for multi-tenant dashboard deployment. A single template
  encodes the analysis definition; each tenant gets a dashboard created
  from that template pointing at its own dataset. This is far more
  scalable than manually rebuilding dashboards per tenant.

## Configuration dependency graph (novel heuristic)

QuickSight dashboard configurations are NOT independent. The data source
must exist before the dataset. The dataset must exist before the
analysis. The analysis must exist before the dashboard. SPICE ingestion
must be configured before the refresh schedule. The VPC connection must
be authorized before private data sources can be used. Use this graph to
sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| QuickSight account | AWS account exists; edition chosen | account name is globally unique; region is fixed at creation | the QuickSight workspace |
| Data source | QuickSight account exists; source datastore reachable | credentials must be valid at creation; VPC connection needed for private sources | dataset creation |
| Dataset (SPICE) | Data source exists; SQL or table selected | SPICE capacity is per-account (Enterprise: 500GB+); ingestion runs at creation and on schedule | analysis + dashboard |
| Dataset (Direct Query) | Data source exists; source DB handles concurrent queries | no SPICE capacity consumed; latency depends on source performance | analysis + dashboard |
| Analysis | Dataset exists; visual types chosen | analysis is editable; dashboard is a published snapshot | dashboard creation |
| Dashboard | Analysis exists; published at version 1+ | dashboard is read-only for readers; update = publish new version from analysis | sharing + reader access |
| Template | Analysis or dashboard exists (as source) | template version is immutable after creation; updates create new versions | multi-tenant deployment |
| Dashboard from template | Template exists; target dataset exists in target account | target dataset schema must match the source dataset schema used to create the template | per-tenant dashboard |
| Row-level security (RLS) | Dataset exists; permissions defined per user/group | RLS applies to the DATASET, not the dashboard; all dashboards using the dataset inherit RLS | row-level data filtering |
| VPC connection | QuickSight account in Enterprise edition; security groups + subnets specified | must be AVAILABLE before data source can use it; requires IAM role with ENI permissions | private data source connection |
| IAM service role | Trust policy for QuickSight principal; permissions for data source access | role ARN specified in data source creation for Aurora/RDS cross-account access | cross-account data source |
| Refresh schedule | Dataset uses SPICE; schedule defined (hourly/daily/weekly) | Direct Query datasets do NOT have refresh schedules (they query live) | data freshness for SPICE datasets |
| User provisioning | QuickSight account exists; user email specified | user role: READER/AUTHOR/ADMIN; first user in account is the admin | dashboard sharing |
| Namespace / groups | QuickSight account exists; namespace created | groups are per-namespace; users assigned to groups for RLS | group-based RLS and access |

**The SPICE-vs-DirectQuery row is the one a baseline model misses.**
Choosing Direct Query for a high-traffic dashboard creates source-store
load and latency issues. Choosing SPICE for near-real-time data needs
stale data. The procedure below forces an explicit ingestion-mode
decision per dataset.

**Cross-dependency gotchas:**
- The VPC connection requires Enterprise edition. Standard edition
  cannot connect to private data stores.
- RLS is defined on the DATASET, not the dashboard. All dashboards
  using that dataset inherit the same RLS. For per-dashboard RLS, use
  separate datasets.
- Template deployment across accounts requires the target account to
  have its own QuickSight account and matching dataset schema.
- SPICE capacity is shared across ALL datasets in the account. Adding
  a large dataset may exhaust capacity for existing datasets.
- Dashboard sharing requires the reader's email to be registered as a
  QuickSight user. Unregistered emails cannot receive shares.

## Expert heuristic: SPICE vs Direct Query

A baseline model says "use Direct Query for real-time." The correct
heuristic evaluates cost, latency, concurrency, and freshness together.

```text
Dataset query mode decision:
  ├── Dashboard audience > 20 concurrent viewers → SPICE (avoid source overload)
  ├── Source DB is Aurora/RDS (limited connections) → SPICE (offload queries)
  ├── Data freshness requirement < 15 minutes → Direct Query (SPICE refresh min is 15 min)
  ├── Data volume > SPICE capacity (500GB Enterprise) → Direct Query (SPICE can't fit)
  ├── Complex joins / calculated fields across large tables → SPICE (pre-computed)
  ├── Redshift / Athena source (designed for analytical load) → Direct Query OK
  └── Cost-sensitive, low-traffic internal dashboard → Direct Query (no SPICE cost)
```

**Key implication:** the #1 cause of QuickSight dashboard performance
issues is Direct Query on an OLTP database (RDS/Aurora) with many
concurrent viewers. Switching to SPICE with a 15-minute refresh
eliminates source-store load and serves sub-second queries.

## Expert heuristic: RLS via dataset permissions and session identity

Row-level security is enforced at the dataset level. Two mechanisms:

```text
RLS mechanisms:
  1. Dataset permissions (Grant):
     - Define which rows a user/group can see based on a column value
     - QuickSight matches the user's identity against the RLS rules
     - Applied BEFORE data reaches the visual

  2. Session policy (generate-embedding-url-for-registered-user):
     - Used with embedded dashboards
     - Session identity passed via QuickSight reader session
     - RLS rules filter rows based on the session identity
```

**Multi-tenant pattern:** create one dataset per tenant with RLS rules
that filter by tenant ID. All tenants share the same template-based
dashboard definition but see only their own data.

## Expert heuristic: template-driven multi-tenant deployment

```text
Template deployment flow:
  1. Build the analysis + dashboard in a source account
  2. Create a template from the source analysis/dashboard
  3. For each tenant:
     a. Create a dataset in the tenant's namespace pointing at tenant data
     b. Create a dashboard FROM the template, referencing the tenant dataset
     c. Apply RLS rules on the tenant dataset
     d. Share the dashboard with tenant users
  4. Template updates: create new template version, then update all
     tenant dashboards from the new version
```

**Key implication:** a single template update propagates to all tenant
dashboards. This is the only scalable way to manage 10+ tenant
dashboards. Manual per-tenant rebuilds are error-prone.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| QuickSight account exists | All resources live under the account | `aws quicksight describe-account-settings --aws-account-id <id>` |
| Edition identified (Standard/Enterprise) | VPC connections, RLS require Enterprise | Check `Edition` in describe-account-settings |
| Source data store reachable | Data source creation needs connectivity | Test connectivity from QuickSight VPC or public endpoint |
| SPICE capacity sufficient | Large datasets may exceed capacity | `aws quicksight describe-account-settings` |
| IAM role for data source (if cross-account) | QuickSight role needs source read access | Verify IAM role trust + permissions |
| VPC connection (for private sources) | Private RDS/Redshift requires VPC connection | `aws quicksight describe-vpc-connection` — AVAILABLE |
| User email list (for sharing) | Sharing requires registered users | Verify emails are registered QuickSight users |
| Template ARN (if template-based) | Dashboard-from-template needs the template | `aws quicksight describe-template` |

## Step 1 — Account creation and edition

QuickSight requires a per-account subscription. The edition determines
available features.

| Edition | SPICE capacity | VPC connection | RLS | Q (NL query) | Paginated reports |
|---|---|---|---|---|---|
| Standard | 10GB (default) | No | No | No | No |
| Enterprise | 500GB+ (scalable) | Yes | Yes | Yes | Yes |

```bash
aws quicksight create-account-subscription \
  --account-name "my-org-quicksight" \
  --edition ENTERPRISE \
  --notification-email admin@example.com \
  --authentication-method IAM_AND_QUICKSIGHT \
  --aws-account-id 123456789012 \
  --region us-east-1
```

Wait for account status `ACCOUNT_CREATED` before proceeding. The
region chosen at account creation is fixed and cannot be changed.

## Step 2 — Data source connection

QuickSight connects to data sources via connectors. Each source type
has specific connection parameters.

| Source | Connection type | Auth method | VPC connection needed |
|---|---|---|---|
| Amazon Athena | Direct (AWS-native) | IAM role | No |
| Amazon S3 | Direct (AWS-native) | IAM role | No |
| Amazon RDS (MySQL/PostgreSQL) | JDBC | Username/password or Secrets Manager | Yes (if private) |
| Amazon Aurora | JDBC | Username/password or Secrets Manager | Yes (if private) |
| Amazon Redshift | JDBC | Username/password or Secrets Manager | Yes (if private) |

**Create Athena data source:**

```bash
aws quicksight create-data-source \
  --aws-account-id 123456789012 \
  --data-source-id ds-athena-prod \
  --name "Athena Production" \
  --type ATHENA \
  --data-source-parameters '{"AthenaParameters":{"WorkGroup":"primary"}}' \
  --region us-east-1
```

**Create RDS PostgreSQL data source (via VPC connection):**

```bash
aws quicksight create-data-source \
  --aws-account-id 123456789012 \
  --data-source-id ds-rds-prod \
  --name "RDS PostgreSQL Production" \
  --type POSTGRESQL \
  --data-source-parameters '{"PostgreSqlParameters":{"Host":"prod-db.cluster-abc123.us-east-1.rds.amazonaws.com","Port":5432,"Database":"analytics"}}' \
  --credentials '{"CredentialPair":{"Username":"quicksight_reader","Password":"<password>"}}' \
  --vpc-connection-arn "arn:aws:quicksight:us-east-1:123456789012:vpcConnection/vpc-conn-123" \
  --region us-east-1
```

## Step 3 — Dataset (SQL, join, calculated field)

A dataset defines the data available for analysis. It can use a custom
SQL query, a table join, or calculated fields. Calculated fields are
defined at the logical table map level. Joins are defined by specifying
a `JoinInstruction` linking two physical tables on a join key.

**Create a dataset with custom SQL (SPICE mode):**

```bash
aws quicksight create-data-set \
  --aws-account-id 123456789012 \
  --data-set-id ds-sales-metrics \
  --name "Sales Metrics" \
  --import-mode SPICE \
  --physical-table-map '{"sales-table":{"CustomSql":{"DataSourceArn":"arn:aws:quicksight:us-east-1:123456789012:datasource/ds-athena-prod","Name":"sales_query","SqlQuery":"SELECT order_id, customer_id, region, revenue, order_date FROM sales WHERE order_date >= date_trunc('\''month'\'', current_date)","Columns":[{"Name":"order_id","Type":"STRING"},{"Name":"customer_id","Type":"STRING"},{"Name":"region","Type":"STRING"},{"Name":"revenue","Type":"DECIMAL"},{"Name":"order_date","Type":"DATETIME"}]}}}' \
  --region us-east-1
```

## Step 4 — SPICE vs Direct Query

| Aspect | SPICE | Direct Query |
|---|---|---|
| Latency | Sub-second (in-memory) | Source DB dependent (seconds) |
| Source load | None (data cached) | Every interaction queries source |
| Freshness | Stale until refresh (min 15 min) | Real-time |
| Capacity | Per-account limit (Enterprise 500GB+) | No limit (source DB is limit) |
| Cost | SPICE capacity per session | Source DB compute cost |

**Trigger SPICE ingestion:**

```bash
aws quicksight create-ingestion \
  --aws-account-id 123456789012 \
  --data-set-id ds-sales-metrics \
  --ingestion-id "ingestion-$(date +%s)" \
  --region us-east-1
```

## Step 5 — Analysis and dashboard creation

An analysis is the editable workspace; a dashboard is a published,
read-only snapshot of an analysis. Readers cannot edit dashboards.

**Create analysis:**

```bash
aws quicksight create-analysis \
  --aws-account-id 123456789012 \
  --analysis-id "sales-analysis" \
  --name "Sales Performance Analysis" \
  --source-entity '{"DataSetIdentifier":{"DataSetArn":"arn:aws:quicksight:us-east-1:123456789012:dataset/ds-sales-metrics","Identifier":"sales-metrics"}}' \
  --region us-east-1
```

Supported visual types: bar chart, line chart, pie chart, pivot table,
KPI, gauge chart, scatter plot, heatmap, map (geospatial), combo chart,
funnel chart, sankey diagram, word cloud, tree map, and insight
(ML-powered anomaly detection). Sheet layout controls how visuals are
arranged on the canvas via a defined grid layout.

**Create dashboard from analysis:**

```bash
aws quicksight create-dashboard \
  --aws-account-id 123456789012 \
  --dashboard-id "sales-dashboard" \
  --name "Sales Performance Dashboard" \
  --source-entity '{"SourceAnalysis":{"Arn":"arn:aws:quicksight:us-east-1:123456789012:analysis/sales-analysis","DataSetReferences":[{"DataSetPlaceholder":"sales-metrics","DataSetArn":"arn:aws:quicksight:us-east-1:123456789012:dataset/ds-sales-metrics"}]}}' \
  --dashboard-publish-options '{"AdHocFilteringOption":{"AvailabilityStatus":"ENABLED"},"ExportToCSVOption":{"AvailabilityStatus":"ENABLED"}}' \
  --version-description "Initial version" \
  --region us-east-1
```

**Share dashboard with a user:**

```bash
aws quicksight create-dashboard-permission \
  --aws-account-id 123456789012 \
  --dashboard-id "sales-dashboard" \
  --grant-permissions '{"Principal":"arn:aws:quicksight:us-east-1:123456789012:user/default/reader@example.com","Actions":["quicksight:DescribeDashboard","quicksight:ListDashboardVersions","quicksight:QueryDashboard"]}' \
  --region us-east-1
```

## Step 6 — Template-based deployment

Templates capture the analysis/dashboard definition for reuse across
accounts or tenants.

**Create template from analysis:**

```bash
aws quicksight create-template \
  --aws-account-id 123456789012 \
  --template-id "sales-template" \
  --name "Sales Dashboard Template" \
  --source-entity '{"SourceAnalysis":{"Arn":"arn:aws:quicksight:us-east-1:123456789012:analysis/sales-analysis","DataSetReferences":[{"DataSetPlaceholder":"sales-data","DataSetArn":"arn:aws:quicksight:us-east-1:123456789012:dataset/ds-sales-metrics"}]}}' \
  --version-description "v1.0" \
  --region us-east-1
```

**Create dashboard from template (per tenant):**

```bash
aws quicksight create-dashboard \
  --aws-account-id 123456789012 \
  --dashboard-id "tenant-a-sales" \
  --name "Tenant A Sales Dashboard" \
  --source-entity '{"SourceTemplate":{"Arn":"arn:aws:quicksight:us-east-1:123456789012:template/sales-template","DataSetReferences":[{"DataSetPlaceholder":"sales-data","DataSetArn":"arn:aws:quicksight:us-east-1:123456789012:dataset/ds-tenant-a-sales"}]}}' \
  --version-description "Tenant A v1" \
  --region us-east-1
```

**Propagate template update to tenant dashboards:**

```bash
aws quicksight update-template \
  --aws-account-id 123456789012 \
  --template-id "sales-template" \
  --source-entity '{"SourceAnalysis":{"Arn":"arn:aws:quicksight:us-east-1:123456789012:analysis/sales-analysis","DataSetReferences":[{"DataSetPlaceholder":"sales-data","DataSetArn":"arn:aws:quicksight:us-east-1:123456789012:dataset/ds-sales-metrics"}]}}' \
  --region us-east-1

aws quicksight update-dashboard \
  --aws-account-id 123456789012 \
  --dashboard-id "tenant-a-sales" \
  --source-entity '{"SourceTemplate":{"Arn":"arn:aws:quicksight:us-east-1:123456789012:template/sales-template","DataSetReferences":[{"DataSetPlaceholder":"sales-data","DataSetArn":"arn:aws:quicksight:us-east-1:123456789012:dataset/ds-tenant-a-sales"}]}}' \
  --version-description "Updated from template v2" \
  --region us-east-1
```

## Step 7 — Row-level security (RLS)

RLS filters rows per user or group. It is defined on the DATASET, not
the dashboard. All dashboards using the dataset inherit the same RLS.

**Create RLS rules dataset (maps users to allowed column values):**

```bash
aws quicksight create-data-set \
  --aws-account-id 123456789012 \
  --data-set-id "ds-sales-rls" \
  --name "Sales RLS Rules" \
  --import-mode SPICE \
  --physical-table-map '{"rls-table":{"RelationalTable":{"DataSourceArn":"arn:aws:quicksight:us-east-1:123456789012:datasource/ds-athena-prod","Schema":"rls","Name":"sales_rls_rules","InputColumns":[{"Name":"UserName","Type":"STRING"},{"Name":"Region","Type":"STRING"}]}}}' \
  --region us-east-1
```

**Enable RLS on the dataset using the RLS rules dataset:**

```bash
aws quicksight update-data-set \
  --aws-account-id 123456789012 \
  --data-set-id "ds-sales-metrics" \
  --row-level-permission-data-set '{"Arn":"arn:aws:quicksight:us-east-1:123456789012:dataset/ds-sales-rls","PermissionPolicy":"GRANT_ACCESS","FormatVersion":"VERSION_1","Namespace":"default","Status":"ENABLED"}' \
  --region us-east-1
```

## Step 8 — VPC connection and IAM role

Enterprise edition only. Connects QuickSight to private RDS/Redshift/
Aurora via specified security groups and subnets.

**Create VPC connection:**

```bash
aws quicksight create-vpc-connection \
  --aws-account-id 123456789012 \
  --vpc-connection-id "vpc-conn-prod" \
  --name "Production VPC Connection" \
  --subnet-ids "subnet-aaa111" "subnet-bbb222" \
  --security-group-ids "sg-quicksight-access" \
  --dns-resolvers "10.0.0.2" \
  --role-arn "arn:aws:iam::123456789012:role/QuickSightVpcRole" \
  --region us-east-1
```

The IAM role must trust `quicksight.amazonaws.com` and have
`ec2:CreateNetworkInterface`, `ec2:DeleteNetworkInterface`, and
`ec2:DescribeNetworkInterfaces` permissions for the specified subnets
and security groups. Wait for status `AVAILABLE` before using in a
data source.

**QuickSight service role trust policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "quicksight.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

## Step 9 — User provisioning, namespaces, groups

**Register a user:**

```bash
aws quicksight register-user \
  --aws-account-id 123456789012 \
  --namespace default \
  --identity-type QUICKSIGHT \
  --email "reader@example.com" \
  --user-role READER \
  --region us-east-1
```

User roles: READER (view dashboards), AUTHOR (create analyses/
dashboards), ADMIN (manage account).

**Create a namespace (for multi-tenant isolation):**

```bash
aws quicksight create-namespace \
  --aws-account-id 123456789012 \
  --namespace "tenant-a" \
  --identity-store QUICKSIGHT \
  --region us-east-1
```

**Create a group (for group-based RLS):**

```bash
aws quicksight create-group \
  --aws-account-id 123456789012 \
  --namespace default \
  --group-name "east-region-readers" \
  --description "Readers with access to East region data" \
  --region us-east-1
```

## Step 10 — Refresh schedule and parameters

SPICE datasets support scheduled refreshes. Direct Query datasets do
NOT have refresh schedules.

**Create refresh schedule:**

```bash
aws quicksight put-data-set-refresh-properties \
  --aws-account-id 123456789012 \
  --data-set-id "ds-sales-metrics" \
  --refresh-properties '{"RefreshConfiguration":{"IncrementalRefresh":{"Frequency":{"Interval":"HOURLY","TimeOfTheDay":"00:00"}}}}' \
  --region us-east-1
```

Supported intervals: MINUTE_15, MINUTE_30, HOURLY, DAILY, WEEKLY,
MONTHLY.

**Parameters** enable dynamic filtering in dashboards. A reader
selects a value (e.g., region, date range) and all visuals on the
sheet update. Parameters are defined in the analysis and linked to
filter controls on the sheet (drop-down, slider, date picker).
**Pagination** refers to paginated reports (Enterprise edition) that
produce multi-page PDF/Excel output with repeating headers and footers
— distinct from interactive dashboards.

## NEVER do these things

1. **NEVER use Direct Query on an OLTP database (RDS/Aurora) for a
   high-traffic dashboard.** Each interaction sends a query to the
   source. With 20+ concurrent viewers, the source database is
   overwhelmed. Use SPICE with a scheduled refresh instead.

2. **NEVER assume sharing a dashboard grants data access.** Sharing
   lets a reader view the dashboard. Row-level security is a SEPARATE
   configuration that controls which rows each reader sees. Without
   RLS, every reader sees all data.

3. **NEVER define RLS on the dashboard.** RLS is defined on the
   DATASET. All dashboards using that dataset inherit the same RLS.
   For per-dashboard RLS, create separate datasets.

4. **NEVER attempt VPC connections with Standard edition.** VPC
   connections require Enterprise edition. Standard edition cannot
   connect to private data stores. Upgrade to Enterprise first.

5. **NEVER create a template without version-description.** Each
   template version should have a clear description. Without version
   tracking, propagating updates to tenant dashboards becomes
   unmanageable.

6. **NEVER forget to set up a refresh schedule for SPICE datasets.**
   Without a schedule, SPICE data is only as fresh as the last manual
   ingestion. Set up at least a daily refresh.

7. **NEVER assume the RLS rules dataset matches the source schema.**
   The RLS rules dataset maps users/groups to allowed column values.
   The column referenced in RLS rules must exist in the source dataset.

8. **NEVER mix tenants in a single dataset without RLS.** If multiple
   tenants share a dataset, RLS MUST filter each tenant's data. For
   strict isolation, use separate datasets per tenant.

9. **NEVER skip the SPICE capacity check for large datasets.** SPICE
   capacity is per-account and shared across all datasets. A large
   dataset may exhaust capacity for existing datasets.

10. **NEVER use unregistered emails for dashboard sharing.** Dashboard
    readers must be registered QuickSight users. Register users first
    via `register-user`.

11. **NEVER assume template deployment works across accounts without
    matching schemas.** The target account must have a dataset with a
    schema matching the source dataset used to create the template.

12. **NEVER forget that the QuickSight account region is fixed.** The
    region chosen at account creation cannot be changed. All
    QuickSight resources live in that region. Choose carefully.

## Output format

```text
QUICKSIGHT_DASHBOARD: <dashboard-id> (version <n>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] QuickSight account: <account-name> (edition: Standard|Enterprise, region: <region>)
  [✓|✗] Data source: <data-source-id> (type: <Athena|RDS|Redshift|S3|Aurora>)
  [✓|✗] VPC connection: <vpc-conn-id> (status: AVAILABLE) | Not required (public source)
  [✓|✗] Dataset: <data-set-id> (mode: SPICE|DIRECT_QUERY)
  [✓|✗] SPICE refresh schedule: <interval> | N/A (Direct Query)
  [✓|✗] Analysis: <analysis-id> (sheets: <count>)
  [✓|✗] Dashboard: <dashboard-id> (version: <n>, status: CREATED)
  [✓|✗] Row-level security: ENABLED (dataset <rls-dataset-id>) | Disabled
  [✓|✗] Template: <template-id> (version: <n>) | Not used
  [✓|✗] Dashboard sharing: <user-count> users, roles: <roles>
  [✓|✗] IAM service role: <role-arn> | Default QuickSight role
  [✓|✗] Parameters: <list> | None
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws quicksight describe-dashboard --aws-account-id <id> --dashboard-id <dashboard-id> --region <region>
  aws quicksight describe-data-set --aws-account-id <id> --data-set-id <data-set-id> --region <region>
  aws quicksight list-ingestions --aws-account-id <id> --data-set-id <data-set-id> --region <region>
```

### Worked example — Enterprise dashboard with SPICE and RLS

```text
QUICKSIGHT_DASHBOARD: sales-dashboard (version 1)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] QuickSight account: my-org-quicksight (edition: Enterprise, region: us-east-1)
  [✓] Data source: ds-athena-prod (type: Athena)
  [✓] VPC connection: Not required (Athena is AWS-native)
  [✓] Dataset: ds-sales-metrics (mode: SPICE)
  [✓] SPICE refresh schedule: HOURLY
  [✓] Analysis: sales-analysis (sheets: 2)
  [✓] Dashboard: sales-dashboard (version: 1, status: CREATED)
  [✓] Row-level security: ENABLED (dataset ds-sales-rls)
  [✓] Template: Not used
  [✓] Dashboard sharing: 3 users, roles: READER
  [✓] IAM service role: Default QuickSight role
  [✓] Parameters: Region, DateRange
  [✓] Tags: Environment=production, Domain=sales
VERIFICATION_COMMANDS:
  aws quicksight describe-dashboard --aws-account-id 123456789012 --dashboard-id sales-dashboard --region us-east-1
  aws quicksight describe-data-set --aws-account-id 123456789012 --data-set-id ds-sales-metrics --region us-east-1
  aws quicksight list-ingestions --aws-account-id 123456789012 --data-set-id ds-sales-metrics --region us-east-1
```

## Error handling

### Data source creation fails with connectivity error
- For private data stores, verify the VPC connection is AVAILABLE and
  the security group allows inbound from QuickSight. For public
  sources, verify the endpoint is reachable.

### SPICE ingestion fails
- Check SPICE capacity: `describe-account-settings`. Verify the SQL
  query is valid and the source is accessible. Check ingestion status
  with `list-ingestions`.

### Dashboard creation fails with schema mismatch
- If creating from a template, the target dataset schema must match
  the source schema. Verify column names and types match.

### RLS not filtering correctly
- Verify the RLS rules dataset maps the correct user ARN/email to the
  correct column values. Check that RLS is ENABLED on the dataset.

### VPC connection stuck in CREATING
- The IAM role must have permissions to create network interfaces.
  Check the role's permissions for `ec2:CreateNetworkInterface`.

### User cannot view shared dashboard
- Verify the user is registered: `describe-user`. Verify the
  dashboard permission grants the reader's principal ARN.

## Domain

AWS CloudOps / Amazon QuickSight Dashboard Provisioning & Analytics.

## AWS documentation

- **QuickSight User Guide** — https://docs.aws.amazon.com/quicksight/latest/user/welcome.html
- **Create account** — https://docs.aws.amazon.com/quicksight/latest/user/signing-up-for-quicksight.html
- **SPICE** — https://docs.aws.amazon.com/quicksight/latest/user/spice-concepts.html
- **Data sources** — https://docs.aws.amazon.com/quicksight/latest/user/sources.html
- **Templates** — https://docs.aws.amazon.com/quicksight/latest/user/working-with-templates.html
- **Row-level security** — https://docs.aws.amazon.com/quicksight/latest/user/row-level-security.html
- **VPC connections** — https://docs.aws.amazon.com/quicksight/latest/user/vpc-connections.html
- **Embedding** — https://docs.aws.amazon.com/quicksight/latest/user/embedding.html
- **QuickSight API** — https://docs.aws.amazon.com/quicksight/latest/APIReference/Welcome.html
