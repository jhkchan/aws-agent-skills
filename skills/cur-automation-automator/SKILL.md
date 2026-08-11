---
name: cur-automation-automator
description: >-
  Designs end-to-end AWS Cost and Usage Report (CUR) automation: CUR creation
  (hourly granularity, resource-level, ReportVersioning, Athena integration),
  Athena setup (database, table, partition projection), CUR query automation
  (top spenders, unused resources, Savings Plan opportunities, tag compliance),
  QuickSight integration (datasets, SPICE dashboards), Cost Category automation,
  cost allocation tag activation, and latest CUR 2.0 split cost allocation,
  AWS BCM Data Exports, Amazon Q cost analysis. Emits a verdict
  (AUTOMATED with full IaC template | MANUAL_STEP_REQUIRED with specific gap).
  Use when setting up CUR, migrating from Cost Explorer to Athena-backed
  analytics, automating FinOps queries, building QuickSight cost dashboards,
  activating tags at scale, or adopting CUR 2.0 split cost allocation.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline plan classification. Live-account
  operations use aws cur describe-report-definitions, put-report-definition,
  delete-report-definition, modify-report-definition, aws athena
  start-query-execution, get-query-execution, create-named-query, aws glue
  get-database, create-database, aws quicksight create-data-source,
  create-dataset, create-dashboard, aws ce list-cost-category-definitions,
  create-cost-category-definition, aws ce update-cost-allocation-tags-status,
  list-cost-allocation-tags, aws bcm-data-exports create-export, list-exports
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - CUR
  - Cost and Usage Report
  - FinOps
  - Athena
  - partition projection
  - QuickSight
  - SPICE
  - cost allocation tags
  - Cost Category
  - Savings Plans
  - Reserved Instances
  - top spenders
  - unused resources
  - tag compliance
  - CUR 2.0
  - split cost allocation
  - EKS cost attribution
  - BCM Data Exports
  - Amazon Q cost analysis
  - cost dashboard
tags:
  - cur
  - finops
  - athena
  - quicksight
  - cost-optimization
  - automate
  - cost-allocation
  - bcm-data-exports
  - cur2
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: FinOps
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "AUTOMATED | MANUAL_STEP_REQUIRED"
  when_to_use: >-
    Setting up CUR for the first time (creating the report, Athena database,
    partitioned table); migrating from Cost Explorer API to Athena-backed CUR
    analytics for higher resolution and longer history; automating recurring
    FinOps queries (top spenders, unused resources, Savings Plan / Reserved
    Instance opportunities, tag compliance); building QuickSight cost
    dashboards backed by CUR; activating cost allocation tags at scale via
    CE API; defining Cost Categories for chargeback / showback; adopting
    CUR 2.0 split cost allocation for EKS / ECS / Lambda container cost
    attribution; migrating from legacy CUR to BCM Data Exports; or wiring
    Amazon Q (Business Pro) for natural-language cost analysis.
  activation_triggers:
    - "set up CUR"
    - "create Cost and Usage Report"
    - "CUR Athena integration"
    - "Athena CUR partition projection"
    - "top spenders query"
    - "unused resources FinOps"
    - "Savings Plan opportunities"
    - "Reserved Instance recommendations"
    - "tag compliance audit"
    - "QuickSight cost dashboard"
    - "SPICE dataset CUR"
    - "Cost Category automation"
    - "cost allocation tag activation"
    - "CUR 2.0 split cost allocation"
    - "EKS cost attribution"
    - "BCM Data Exports"
    - "Amazon Q cost analysis"
  invocation_schema: >-
    Input: either (a) a scenario describing the target CUR setup (greenfield
    vs. migration, scope: single account vs. organization/payer, granularity:
    hourly vs. daily, target: Athena-only vs. Athena+QuickSight vs. BCM Data
    Exports), OR (b) an existing CUR + Athena configuration and an operation
    (audit, migrate-cur2, add-quicksight, automate-queries, activate-tags,
    define-cost-categories). Output: deterministic OPERATION / VERDICT /
    REQUIREMENTS / IAC_TEMPLATE / MANUAL_GAPS / NOTES block where VERDICT is
    AUTOMATED (full CloudFormation / Terraform template generated) or
    MANUAL_STEP_REQUIRED (specific gap blocks automation, with exact CLI
    snippet to close it).
---

# CUR Automation Automator

## What this skill does

Designs and emits a working CUR automation stack as code — CUR
definition, Athena database with partition projection, named queries for
top-spenders / unused-resources / Savings-Plan-opportunities / tag-compliance,
optional QuickSight datasets and dashboards, Cost Categories for
chargeback, cost-allocation-tag activation, and (when requested) CUR 2.0
split cost allocation, BCM Data Exports, or Amazon Q cost-analysis wiring.
Runs deterministic requirement checks before emitting the template — if
all checks pass, the verdict is `AUTOMATED` with a populated
CloudFormation / Terraform template. If a requirement is missing (no
payer account, no bucket policy for Athena, no QuickSight Enterprise
session, no BCM Data Exports permission), the verdict is
`MANUAL_STEP_REQUIRED` with the specific gap and the exact CLI / IaC
snippet that closes it.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds + requirement checklist + capability matrix | Before any build |
| **§ Mindset** | Why CUR+Athena beats Cost Explorer, the 24-hour lag, partition projection | Understanding the design model |
| **§ Pre-flight** | Requirement gate — payer, bucket, Glue catalog, IAM, QuickSight session | Before emitting any template |
| **§ Process** | Per-stage design: CUR definition, Athena table, queries, QuickSight, tags, Cost Categories | When designing each layer |
| **§ STRICT output contract** | Required labels + FORBIDDEN patterns + self-check | Before emitting any block |
| **§ Expert heuristic** | The 5 non-obvious failure modes that miss naive CUR setups | Defense-in-depth |
| **§ Anti-Patterns** | NEVER list — common mistakes that silently break CUR automation | Review before emitting |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `AUTOMATED` | All requirements satisfied (payer or consolidated-billing account, CUR bucket with correct policy, Glue Data Catalog in CUR region, IAM role for Athena/QuickSight, QuickSight Enterprise session if dashboards requested, cost-allocation-tag activation if tags requested, BCM Data Exports permissions if BCM path). Template generated. | Emit complete CUR automation template, ready to apply |
| `MANUAL_STEP_REQUIRED` | One or more requirements missing (linked (member) account only — no CUR visibility; bucket policy missing Athena service principal; QuickSight session not initialized; tag activation requires payer root or Billing role; BCM Data Exports not enabled in the account). | Emit the specific gap and the exact CLI / IaC snippet to close it. Hold the partial template as a draft. |

**Requirement checklist (all must be satisfied for AUTOMATED):**

1. **Account type** — payer (management) or consolidated-billing
   account. A linked account cannot create a CUR that spans the
   organization. Verify via `aws organizations describe-organization`
   or `aws ce list-accounts` (payer-only API).
2. **CUR S3 bucket** — exists, has BlockPublicAccess enabled,
   versioning on, bucket policy granting `billingreports.amazonaws.com`
   WRITE and `athena.amazonaws.com` READ, both with `aws:SourceAccount`
   condition. SSE-KMS for compliance; SSE-S3 acceptable for non-regulated.
3. **ReportVersioning** — `CREATE_NEW` (default, full daily snapshot)
   or `OVERWRITE` (incremental, smaller bucket, harder to time-travel).
4. **Granularity** — `HOURLY` (max 24-hour delay before data lands) or
   `DAILY` (max 24-hour delay, smaller files). For real-time cost
   anomaly detection, use Cost Anomaly Detection, not CUR.
5. **Compression** — `Parquet` (columnar, Athena-optimal, ~10x faster
   scans vs GZIP). Avoid GZIP unless a legacy consumer requires it.
6. **Athena Glue Data Catalog** — exists in the SAME region as the CUR
   bucket. Cross-region catalogs require explicit catalog ARN.
7. **Partition projection** — Athena table MUST use partition projection
   (`projection.day.type=date`,
   `projection.day.range=2024/01/01,NOW`) to avoid manual `MSCK REPAIR
   TABLE` (which is O(n_parts) slow and throttles past 20k partitions).
8. **Athena workgroup** — non-`primary` workgroup with
   BytesScannedCutoffPerQuery set (CUR queries can scan 100s of GB if
   untuned; the cutoff prevents bill shock).
9. **IAM execution role** — Athena workgroup role with
   `athena:StartQueryExecution`, `glue:GetTable`, `s3:GetObject` on the
   CUR bucket, `s3:PutObject` on the Athena results bucket.
10. **QuickSight Enterprise session** — `aws quicksight describe-account`
    returns `AccountEdition: ENTERPRISE` (or `ENTERPRISE_AND_Q`).
    Standard edition cannot schedule SPICE refresh on Athena.
11. **Cost-allocation tag activation** (if tags layer requested) — only
    the payer account root or a Billing role can call
    `UpdateCostAllocationTagsStatusUpstream`. Linked accounts can read
    tag keys but cannot activate them.
12. **Cost Category** (if chargeback layer requested) — payer account
    only.
13. **CUR 2.0 / Split Cost Allocation** (if requested) — must be enabled
    on the payer via Billing console or CE API. Takes 24-48 hours for
    first data.
14. **BCM Data Exports** (if requested) — must be enabled on the payer;
    the service-linked role `AWSServiceRoleForBCMDataExports` is
    auto-created on first use.

**Capability matrix (which AWS service handles each layer):**

| Layer | Service(s) | Common pitfalls |
|---|---|---|
| CUR definition | CUR (`cur`) | Hourly granularity → 24h lag; Parquet required for fast Athena |
| Storage | S3 | Wrong region (must match Glue catalog); missing service-principal policy |
| Catalog | Glue Data Catalog | Cross-region catalog breaks Athena partition projection |
| Query engine | Athena | `primary` workgroup = no DSL, unbounded cost; partition projection missing |
| Query automation | Athena Named Queries, EventBridge scheduler, Lambda | No DSL on workgroup = expensive scans |
| Visualization | QuickSight | Standard edition = no scheduled SPICE refresh; Enterprise needed |
| Chargeback | Cost Categories | Linked account cannot create; payer-only |
| Tag activation | CE API | Linked account cannot activate tags; payer-only |
| CUR 2.0 | Split Cost Allocation Data (SCAD) | Must be enabled separately; 24-48h lag for first data |
| Modern exports | BCM Data Exports | Service-linked role auto-created on first use |
| NL analysis | Amazon Q Business (cost connector) | Requires Q Business Pro subscription; payer-scoped |

## Mindset

**One-line takeaway:** CUR + Athena + partition projection is the only
way to do FinOps at AWS scale — Cost Explorer is a UI, not a data
pipeline. Driven by three CUR realities:

- **Cost Explorer is rate-limited and resolution-capped.** CE API caps
  at 1 req/s and returns aggregated data with a 24-hour SLA. CUR gives
  you the raw line items (resource-level for hourly CUR), 12+ months of
  history, and no rate limit because you're querying your own Athena.
  Any FinOps pipeline that touches more than 5 services or more than 50
  accounts must move off CE and onto CUR.

- **Partition projection is non-negotiable.** CUR writes one partition
  per day (or per hour for hourly CUR). A year of hourly CUR = ~8,700
  partitions. `MSCK REPAIR TABLE` scans every partition metadata
  object — past 20k it throttles and never finishes. Partition
  projection (`projection.day.type=date`,
  `projection.day.range=2024/01/01,NOW`) tells Athena to compute
  partition locations from the date string itself — no Glue metastore
  writes, no MSCK, no throttle.

- **CUR 2.0 split cost allocation changes container cost attribution.**
  In CUR 1.0, an EKS pod that runs for 5 minutes on a shared node shows
  as the full node cost. CUR 2.0 + Split Cost Allocation Data (SCAD)
  divides the node cost across pods by CPU/memory usage with idle
  allocation. Without SCAD, EKS cost attribution is wrong by an order
  of magnitude. SCAD must be enabled separately on the payer.

## Pre-flight: requirement gate

Run before emitting any template. Missing requirements produce
MANUAL_STEP_REQUIRED with the exact gap.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws organizations describe-organization` — confirm the caller is
   the payer / management account. If not, CUR scope is limited.
2. `aws cur describe-report-definitions` — confirm whether a CUR with
   the target name already exists (create vs. update).
3. `aws s3api get-bucket-location --bucket <cur-bucket>` and
   `get-bucket-versioning` — verify the CUR bucket exists, has
   versioning on, and is in the target region.
4. `aws s3api get-bucket-policy --bucket <cur-bucket>` — verify the
   policy grants `billingreports.amazonaws.com` WRITE and
   `athena.amazonaws.com` READ, with `aws:SourceAccount` conditions.
5. `aws glue get-database --name <athena_db>` — verify the Glue database
   exists (or will be created alongside the template).
6. `aws athena list-work-groups` — verify a non-`primary` workgroup
   exists with `EnforceWorkgroupConfiguration: true` and a per-query
   byte cutoff.
7. `aws quicksight describe-account --aws-account-id <acct>` (if
   QuickSight requested) — verify `AccountEdition: ENTERPRISE`.
8. `aws ce list-cost-allocation-tags --status Active` (if tags layer
   requested) — verify the target tag keys are already activated.
9. `aws ce list-cost-category-definitions` (if chargeback requested) —
   verify existing Cost Categories to avoid name conflicts.
10. `aws bcm-data-exports list-exports` (if BCM Data Exports requested)
    — verify the service is enabled.

**Malformed input:** if the input scenario is missing required fields
(account type, target region, granularity, scope), emit
`VERDICT: MANUAL_STEP_REQUIRED` with `GAP: Scenario missing required
field <field>. Provide <field> to proceed.`

| Requirement | Effect on automation |
|---|---|
| Caller is a linked (member) account | MANUAL_STEP_REQUIRED — CUR visibility is payer-only; emit the cross-account IAM role snippet. |
| CUR bucket policy missing Athena service principal | MANUAL_STEP_REQUIRED — emit `aws s3api put-bucket-policy` snippet granting `athena.amazonaws.com` with `aws:SourceAccount`. |
| Glue database does not exist | AUTOMATED (the database is part of the emitted template). |
| Only `primary` Athena workgroup exists | AUTOMATED (the template creates a non-primary workgroup with DSL). |
| QuickSight account is Standard edition | MANUAL_STEP_REQUIRED — scheduled SPICE refresh requires Enterprise; emit `update-account-subscription` snippet. |
| Cost-allocation tag not activated | MANUAL_STEP_REQUIRED — payer-only API; emit `update-cost-allocation-tags-status` snippet. |
| CUR 2.0 SCAD not enabled | MANUAL_STEP_REQUIRED — payer-only enablement in Billing console; emit the console URL. |
| BCM Data Exports not enabled | AUTOMATED (first `create-export` call auto-creates the service-linked role). |
| CUR < 24 hours old | MANUAL_STEP_REQUIRED — no data to query yet; emit the wait-and-retry note. |

## Process — CUR automation design (apply in order)

### Step 0: Expert knowledge — non-obvious CUR behaviors

- **The 24-hour delivery lag is a hard SLA, not a target.** CUR is
  delivered 3 times per day for hourly granularity and 1 time per day
  for daily. The most recent hour's data is NEVER in CUR — use Cost
  Anomaly Detection or real-time CloudWatch metrics for that.

- **`OVERWRITE` ReportVersioning breaks time-travel queries.** With
  OVERWRITE, AWS rewrites the previous day's partition as the day's
  invoices close. Use `CREATE_NEW` (default) unless you specifically
  want the final-state snapshot.

- **`Resource` granularity requires hourly CUR.** Daily CUR aggregates
  by service + linked account + usage type — no resource IDs. To get
  resource-level cost (EC2 instance ID, S3 bucket name), you MUST set
  `AdditionalSchemaElements: ["Resources"]` AND `TimeUnit: HOURLY`.

- **CUR 2.0 is a different report, not a setting on CUR 1.0.** CUR 2.0
  ships via BCM Data Exports (`bcm-data-exports`), not via the legacy
  `cur` API. The column schema is different.

- **`MSCK REPAIR TABLE` is an anti-pattern on CUR.** It scans every
  partition object. Past ~20k partitions it throttles and never
  finishes. Partition projection is the only sustainable model.

- **The `lineItem/UsageAccountId` is the account that USED the
  resource; `bill/PayerAccountId` is the account that PAID.**
  Chargeback queries group by `lineItem/UsageAccountId`; refund
  queries group by `bill/PayerAccountId`.

- **Savings Plans and Reserved Instance discounts appear in two
  columns.** `lineItem/LineItemType = SavingsPlanCoveredUsage` and
  `SavingsPlanRecurringFee`. To compute effective rate, you must join
  the two — naive queries double-count or miss the fee.

- **Cost Category values are evaluated in order.** Always emit a
  catch-all `Uncategorized` rule at the end; otherwise line items that
  match no rule vanish from chargeback reports.

- **Cost allocation tags must be activated BEFORE they appear in
  CUR.** Activating a new tag today makes it appear in CUR starting
  TOMORROW — historical CUR data does NOT backfill. Payer-account-only.

- **QuickSight SPICE refresh is bounded by edition.** Standard: no
  scheduled refresh on Athena datasets. Enterprise: up to 32 scheduled
  refreshes per dataset, hourly granularity.

- **CUR Athena queries can scan the entire report if unfiltered.** A
  year of hourly CUR with resource IDs can be 5+ TB. Without a
  partition predicate, a single query costs $25+ at $5/TB. The Athena
  workgroup BytesScannedCutoffPerQuery MUST be set.

- **CUR 2.0 split cost allocation only covers EKS, ECS (Fargate +
  EC2), and Lambda today.** Other compute (EC2 dedicated, EMR) is not
  split. Do not promise "per-pod cost" for non-EKS workloads.

- **Amazon Q cost analysis is a NATURAL LANGUAGE layer, not a data
  layer.** It queries CUR via Athena under the hood, but adds its own
  prompt-completion cost. Use Q for ad-hoc exploration; use Athena
  named queries for repeatable pipelines.

### Step 1: CUR definition design

| Setting | Recommended | Why |
|---|---|---|
| `ReportName` | `<org>-cur-hourly` | Identifies the report in the console |
| `TimeUnit` | `HOURLY` | Required for resource-level granularity |
| `Format` | `Parquet` | Columnar, ~10x faster Athena scans |
| `Compression` | `Parquet` (built-in) | Native, no extra compression setting |
| `AdditionalSchemaElements` | `["Resources"]` (add `SplitCostAllocationData` for CUR 2.0) | Resource IDs + SCA |
| `S3Bucket` | existing bucket in CUR region | SSE-KMS recommended |
| `S3Prefix` | `cur/<report-name>/` | Path-based isolation for multi-report buckets |
| `S3Region` | bucket region | Must match Glue catalog region |
| `ReportVersioning` | `CREATE_NEW` | Daily snapshots, enables time travel |
| `RefreshClosedReports` | `true` | Refunds/credits apply to closed partitions |
| `ReportPublishingPreferences` | `Hourly: true` | Required for hourly CUR |

### Step 2: CUR bucket policy design

The bucket MUST grant two service principals:
1. `billingreports.amazonaws.com` — WRITE (CUR delivery).
2. `athena.amazonaws.com` — READ (Athena query execution).

Both MUST use `aws:SourceAccount` (and for athena, optionally
`aws:SourceArn`) conditions to prevent confused-deputy attacks. See
`references/quicksight-and-cmefeatures.md` for the full policy JSON.

### Step 3: Athena database and table (partition projection)

The Athena table DDL MUST use partition projection. Without it, MSCK
REPAIR TABLE never finishes past ~20k partitions. See
`references/athena-partition-projection-and-queries.md` for the full
DDL with TBLPROPERTIES block.

**Workgroup (non-primary, with DSL):** always create a non-primary
workgroup with `EnforceWorkgroupConfiguration: true` and
`BytesScannedCutoffPerQuery: 1099511627776` (1 TB cutoff). The `primary`
workgroup has no cutoff; a single unfiltered query can scan 5+ TB.

### Step 4: Query automation — named queries

| Query | Purpose | Key predicate |
|---|---|---|
| `top_spenders_by_service` | Monthly cost by service, ranked | `WHERE day >= date_trunc('month', current_date)` GROUP BY `product_servicename` |
| `top_spenders_by_account` | Monthly cost by linked account | GROUP BY `lineitem_usageaccountid` |
| `unused_ec2_resources` | EC2 instances with zero network bytes | LEFT JOIN cw_metrics WHERE bytes_in = 0 |
| `savings_plan_opportunities` | On-Demand spend eligible for SP coverage | `lineitem_lineitemtype = 'Usage' AND pricing_term = 'OnDemand'` |
| `ri_utilization` | Reserved Instance coverage and utilization | `lineitem_lineitemtype LIKE 'RIFee%' OR 'DiscountedUsage'` |
| `tag_compliance_gaps` | Resources missing required tags | `WHERE resource_tags_<key> IS NULL` |
| `eks_pod_cost_attribution` | EKS pod cost (requires CUR 2.0 SCA) | `WHERE split_cost_allocation_data_resource IS NOT NULL` |

Full SQL for each query lives in
`references/athena-partition-projection-and-queries.md`.

### Step 5: QuickSight, Cost Categories, tags, and CUR 2.0 layers

| Layer | Default | Why |
|---|---|---|
| QuickSight edition | Enterprise | Required for scheduled SPICE refresh on Athena |
| Dataset refresh | Hourly during business hours | Avoids Athena concurrency limits |
| SPICE capacity | 500 GB baseline | One year of hourly CUR ≈ 100-200 GB after Parquet |
| Row-Level Security | By linked account | RLS on `lineitem_usageaccountid` for chargeback |
| Cost Category rules | `EQUAL`/`PROPORTIONAL`/`FIXED`/`ATTRIBUTES` | Chargeback model selection |
| Cost Category catch-all | `Uncategorized` final rule | Prevents line items vanishing from chargeback |
| Tag activation | Payer-only, non-backfilling | CE API `UpdateCostAllocationTagsStatusUpstream` |
| CUR 2.0 SCAD | Enable via system tag keys | `aws:eks:clusterName`, `aws:ecs:clusterName`, `aws:lambda:functionName` |
| BCM Data Exports | `bcm-data-exports` API for new reports | Replaces legacy `cur` API; supports custom queries |

Tag activation snippet (payer only):

```bash
aws ce update-cost-allocation-tags-status-upstream \
  --tag-keys "env" "team" "cost-center" \
  --status "Active" --profile payer-profile
```

CUR 2.0 SCAD requires CloudWatch Container Insights on EKS clusters
before enabling. BCM Data Exports full create-export payload lives in
`references/quicksight-and-cmefeatures.md`.

### Step 10: Emit template (AUTOMATED) or gap (MANUAL_STEP_REQUIRED)

If all pre-flight requirements pass, emit the complete CUR automation
template (CloudFormation / Terraform, per the operator's preference):
- `AWS::CUR::ReportDefinition` (or BCM Data Export).
- `AWS::S3::Bucket` for CUR destination (if not provided).
- `AWS::S3::BucketPolicy` granting CUR + Athena service principals.
- `AWS::Glue::Database` and `AWS::Glue::Table` with partition projection
  TBLPROPERTIES.
- `AWS::Athena::WorkGroup` (non-primary, with DSL).
- `AWS::Athena::NamedQuery` for each query in the standard set.
- `AWS::Scheduler::Schedule` + `AWS::Lambda::Function` for recurring
  query automation.
- `AWS::QuickSight::DataSource`, `DataSet`, `Dashboard` (if requested).
- `AWS::CE::CostCategoryDefinition` (if chargeback requested).
- `AWS::IAM::Role` for the Athena/QuickSight execution role.

If any requirement is missing, emit `MANUAL_STEP_REQUIRED` with the
specific gap and the exact CLI / IaC snippet to close it.

## Patterns — IaC templates

Full CloudFormation and Terraform templates (CUR definition + Glue DB +
Glue Table with partition projection + non-primary workgroup with DSL +
named queries) live in `references/athena-partition-projection-and-queries.md`.

The non-negotiable TBLPROPERTIES block for partition projection:

```text
projection.enabled = true
projection.day.type = date
projection.day.range = "2024/01/01,NOW"  # literal NOW, Athena engine v3
projection.day.format = "yyyy/MM/dd"
projection.day.interval = 1
projection.day.interval.unit = DAYS
storage.location.template = s3://<bucket>/<prefix>/year=${year}/month=${month}/day=${day}
```

The non-negotiable workgroup configuration:

```text
EnforceWorkgroupConfiguration = true
BytesScannedCutoffPerQuery = 1099511627776  # 1 TB cutoff
EngineVersion = Athena engine version 3  # required for NOW range end
```

## Diagnostic flows

### CUR not delivering to S3

`aws s3 ls s3://<bucket>/<prefix>/year=YYYY/month=MM/` — empty for >
24 hours is almost always a bucket policy problem. Verify
`billingreports.amazonaws.com` is present with `aws:SourceAccount`
condition, and that the bucket region matches `S3Region` in the report
definition.

### Athena query fails with "HIVE_CURSOR_ERROR"

The CUR table schema is out of date — AWS adds columns when new
services launch. Pull the latest DDL from the AWS docs or
`aws cur get-report-definition`. Use `OPENCSVSerde` for legacy CSV CUR;
`ParquetHiveSerDe` for Parquet.

### Athena query returns "Partition not found"

Partition projection not enabled, or partition date outside range.
Check `TBLPROPERTIES ('projection.enabled' = 'true')` and
`projection.day.range = '2024/01/01,NOW'`. The literal `NOW` is
evaluated at query time — requires Athena engine v3.

### QuickSight SPICE refresh fails with "Athena query timeout"

The auto-generated SQL scans too much data without a partition
predicate. Add a filter on the partition column in the QuickSight
dataset, or use a custom SQL dataset with a WHERE clause.

### Tag activation has no effect on CUR data

The tag was activated AFTER the data was delivered. CUR does NOT
backfill — historical data remains tag-less. Activation applies only
to data delivered after activation.

## Output format (per operation)

```text
OPERATION: <create | update | audit | migrate-cur2 | add-quicksight | activate-tags | define-cost-categories | enable-bcm-exports>
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
TARGET: <cur-automation-stack-name>
REQUIREMENTS:
  - [PASS] <requirement description>
  - [FAIL] <requirement description> — <gap>
IAC_TEMPLATE: <inline CloudFormation / Terraform template, or "(held in draft)">
MANUAL_GAPS:
  - GAP: <gap description>
    REMEDIATION: <exact CLI or IaC snippet to close the gap>
    REASON: <why this cannot be automated>
NOTES: <delivery lag, partition projection caveats, payer-only caveats>
```

### Perfect example output — AUTOMATED

```text
OPERATION: create
VERDICT: AUTOMATED
TARGET: prod-cur-automation
REQUIREMENTS:
  - [PASS] Caller is payer account 111111111111
  - [PASS] CUR bucket prod-cur-bucket exists in us-east-1 with versioning
  - [PASS] CUR bucket policy grants billingreports.amazonaws.com + athena.amazonaws.com
  - [PASS] Glue database prod_cur will be created
  - [PASS] Athena workgroup finops-cur will be created with 1TB DSL
  - [PASS] Athena results bucket prod-athena-results exists with KMS SSE
IAC_TEMPLATE:
  # CloudFormation with: AWS::CUR::ReportDefinition (HOURLY, Parquet,
  # AdditionalSchemaElements=[Resources], ReportVersioning=CREATE_NEW),
  # AWS::Glue::Database, AWS::Glue::Table (partition projection TBLPROPERTIES),
  # AWS::Athena::WorkGroup (finops-cur, BytesScannedCutoffPerQuery=1TB,
  # EngineVersion=3), AWS::Athena::NamedQuery for top_spenders_by_service.
  # Full template in references/athena-partition-projection-and-queries.md.
MANUAL_GAPS: (none)
NOTES:
  - First CUR delivery arrives within 24 hours.
  - All Athena queries MUST include a partition predicate on day/month/year.
```

### Perfect example output — MANUAL_STEP_REQUIRED

```text
OPERATION: create
VERDICT: MANUAL_STEP_REQUIRED
TARGET: linked-account-cur-stack
REQUIREMENTS:
  - [FAIL] Caller is linked account 222222222222, not payer 111111111111
  - [PASS] S3 bucket exists
IAC_TEMPLATE: (held in draft — apply after closing the gap below)
MANUAL_GAPS:
  - GAP: CUR is being created from a linked account.
    REMEDIATION:
      aws cur put-report-definition --report-definition file://cur.json --profile payer
    REASON: CUR API is payer-only; cross-account requires payer IAM role + Glue policy.
NOTES:
  - Run this skill from the payer account for organization-wide FinOps.
```

## STRICT output contract

The rules below are hard constraints. Violating any one produces a CUR
automation stack that fails silently on first run (no data, no
permissions, throttle at scale) or a gap report that leaves the operator
stuck. Self-check EVERY emitted block against these rules before
returning.

### Required output structure

Every response MUST be a single block using these literal labels, in
this order. Do NOT substitute markdown headings or camelCase variants.

```text
OPERATION: <create | update | audit | migrate-cur2 | add-quicksight | activate-tags | define-cost-categories | enable-bcm-exports>
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
TARGET: <cur-automation-stack-name>
REQUIREMENTS:
  - [PASS] <requirement description>
  - [FAIL] <requirement description> — <gap>
IAC_TEMPLATE: <inline CloudFormation / Terraform, or "(held in draft)">
MANUAL_GAPS:
  - GAP: <gap description>
    REMEDIATION: <exact CLI or IaC snippet to close the gap>
    REASON: <why this cannot be automated>
NOTES: <delivery lag, partition projection caveats, payer-only caveats>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: AUTOMATED` when any requirement is `[FAIL]`.**
   A single `[FAIL]` MUST produce `VERDICT: MANUAL_STEP_REQUIRED`.

2. **NEVER emit a `[FAIL]` requirement without a corresponding
   `MANUAL_GAPS` entry.** Every `[FAIL]` line MUST have a matching
   GAP/REMEDIATION/REASON block with the exact CLI or IaC snippet.

3. **NEVER emit an Athena CUR table without partition projection.** A
   table created with `PARTITIONED BY (year, month, day)` but no
   `TBLPROPERTIES ('projection.enabled' = 'true')` forces
   `MSCK REPAIR TABLE`, which throttles past ~20k partitions.

4. **NEVER emit a CUR bucket policy with `Principal: "*"`.** CUR data
   is sensitive cost data — restrict to `billingreports.amazonaws.com`
   and `athena.amazonaws.com` service principals with `aws:SourceAccount`
   conditions.

5. **NEVER emit an Athena workgroup without
   `BytesScannedCutoffPerQuery`.** The `primary` workgroup has no
   cutoff; a single unfiltered query can scan 5+ TB at $5/TB = $25+.
   Every emitted workgroup MUST have a cutoff (recommended 1 TB).

6. **NEVER emit a CUR with daily granularity when resource-level cost
   is requested.** Daily CUR aggregates by service + linked account —
   no resource IDs. Resource-level requires hourly CUR with
   `AdditionalSchemaElements: ["Resources"]`.

7. **NEVER emit cost-allocation-tag activation from a linked account.**
   The CE API `UpdateCostAllocationTagsStatusUpstream` is payer-only.

8. **NEVER emit `IAC_TEMPLATE: (held in draft)` without listing which
   specific `[FAIL]` items blocked it.** The MANUAL_GAPS block MUST
   enumerate every gap.

**Self-check before emit:**
- [ ] Any `[FAIL]` in REQUIREMENTS → VERDICT is MANUAL_STEP_REQUIRED?
- [ ] Every `[FAIL]` has a matching GAP/REMEDIATION/REASON block?
- [ ] Athena table has partition projection TBLPROPERTIES?
- [ ] CUR bucket policy uses service principals with aws:SourceAccount?
- [ ] Athena workgroup has BytesScannedCutoffPerQuery set?
- [ ] Hourly CUR has AdditionalSchemaElements: [Resources]?
- [ ] Tag activation runs only on payer account?

## Expert heuristic — top 5 non-obvious failure modes

The five failure modes below are the ones a naive CUR setup misses.
Each is silently wrong (no error, no log) until 30+ days in.

1. **MSCK REPAIR TABLE silently throttles past ~20k partitions.** No
   error — Athena returns success with zero new partitions added. The
   table appears empty for queries on recent dates. The only prevention
   is partition projection (`projection.day.type=date`). Any CUR table
   without `projection.enabled=true` is a ticking time bomb at the
   3-year mark.

2. **CUR bucket policy without `aws:SourceAccount` condition is a
   confused-deputy risk.** `billingreports.amazonaws.com` is a service
   principal — without `aws:SourceAccount`, a different account could
   direct delivery to your bucket. The fix is `Condition: StringEquals:
   aws:SourceAccount: <account>` on both statements.

3. **QuickSight Standard edition silently fails scheduled SPICE
   refresh.** No error in the QuickSight console — the schedule simply
   does not exist. The dataset stays stale, dashboards show last-week
   data. Fix: upgrade to Enterprise.

4. **Tag activation does NOT backfill historical CUR data.** Activating
   `cost-center` today makes it appear in CUR data starting tomorrow.
   September's CUR data remains tag-less. Tag-based chargeback only
   becomes complete 12 months after activation.

5. **CUR 2.0 SCAD requires EKS Container Insights enabled.** Without
   CloudWatch Container Insights on the EKS cluster, the SCA data has
   nothing to split by — the entire node cost appears against the
   default namespace. Enable Container Insights BEFORE enabling SCAD.

## Anti-Patterns — NEVER do these things

- **NEVER emit a CUR with `ReportVersioning: OVERWRITE` for FinOps.**
  OVERWRITE rewrites the previous day's partition as invoices close —
  historical queries return different results on each run. Use `CREATE_NEW`.

- **NEVER emit an Athena CUR table without partition projection.** Past
  ~20k partitions, `MSCK REPAIR TABLE` throttles and never finishes —
  the table appears empty with no error.

- **NEVER emit a CUR bucket policy with `Principal: "*"`.** CUR data is
  sensitive — restrict to `billingreports.amazonaws.com` and
  `athena.amazonaws.com` with `aws:SourceAccount` conditions.

- **NEVER emit the `primary` Athena workgroup for CUR queries.** The
  primary workgroup has no DSL — a single unfiltered query can scan 5+
  TB at $5/TB. Always create a non-primary workgroup with a cutoff.

- **NEVER emit cost-allocation tag activation from a linked account.**
  The CE API is payer-only. Always verify the caller is the payer.

- **NEVER emit a daily CUR when resource-level cost is requested.** Daily
  CUR aggregates by service + linked account — no resource IDs. Requires
  hourly CUR with `AdditionalSchemaElements: ["Resources"]`.

- **NEVER emit a QuickSight dataset on Athena without an Enterprise
  session.** Standard edition has no scheduled SPICE refresh — dashboards
  silently show stale data.

- **NEVER emit a Cost Category without a catch-all `Uncategorized` rule.**
  Without it, line items that match no rule vanish from chargeback reports.

- **NEVER emit CUR 2.0 SCAD without Container Insights on EKS.** SCAD
  splits node cost by pod-level CPU/memory — without Container Insights,
  the SCA data has nothing to split by.

- **NEVER emit a BCM Data Exports setup assuming the service-linked role
  exists.** An SCP denying `iam:CreateServiceLinkedRole` blocks the SLR
  auto-creation silently.

- **NEVER emit an Athena query without a partition predicate.**
  `SELECT * FROM cur_hourly` scans the entire table (5+ TB at $5/TB).
  Always include `WHERE day BETWEEN ... AND ...`.

- **NEVER auto-execute `put-report-definition` without the CONFIRM gate.**
  The CUR API is idempotent, but bucket policy changes have blast radius.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`put-report-definition`, `delete-report-definition`,
  `update-cost-allocation-tags-status`, `create-cost-category-definition`,
  `bcm-data-exports create-export`), emit: `CONFIRM: About to <operation>
  on CUR automation stack <name> in account <account> region <region>.
  This affects <consequence>. Proceed? (yes/no)`. Do NOT execute until
  the operator confirms.

- **Verify the caller is the payer account.** `aws sts
  get-caller-identity` — if the account ID is not the payer, all CUR,
  Cost Category, and tag-activation operations fail with `AccessDenied`.

- **Snapshot the existing CUR definition before update.**
  `aws cur describe-report-definitions --output json > /tmp/cur-backup-$(date +%s).json`.

- **Verify the CUR bucket has no in-flight delivery** (02:00-06:00 UTC
  window) before changing the bucket policy.

- **Before emitting tag activation**, verify the tag keys exist on at
  least one resource. **Before emitting a Cost Category**, verify no
  Cost Category with the target name exists. **Before emitting CUR 2.0
  SCAD**, verify EKS clusters have Container Insights enabled.

- Prefer additive changes over destructive changes.

## Recent AWS features (2024-2026)

- **CUR 2.0 via BCM Data Exports (2024-2025):** the modern path for new
  CUR setups. Uses `bcm-data-exports` API (not legacy `cur`). Adds split
  cost allocation columns natively. Replaces the legacy CUR API for new
  reports; existing CUR 1.0 reports continue to work.

- **Split Cost Allocation Data (SCAD) for EKS/ECS/Lambda (2024-2025):**
  divides node cost across pods/containers by CPU/memory usage with idle
  allocation. Must be enabled separately on the payer. Requires CloudWatch
  Container Insights on EKS clusters.

- **Amazon Q Business cost analysis (2025-2026):** natural-language layer
  on top of CUR. Q Business Pro ($20/user/month) connects to CUR via
  Athena under the hood. Use for ad-hoc exploration; use Athena named
  queries for repeatable pipelines.

- **Athena engine version 3 (2024):** required for partition projection
  with `NOW` as the range end. Engine v2 does not evaluate `NOW` correctly.

- **Cost Anomaly Detection with CUR correlation (2025):** CAD now
  correlates anomalies with the underlying CUR line items, making it
  easier to identify the resource that caused the spike. Use CAD for
  real-time alerting (CUR has 24-hour lag).

- **QuickSight Q (2024-2025):** natural-language Q in QuickSight, layered
  on top of CUR-backed datasets. Useful for non-technical stakeholders.

## Domain

AWS CloudOps / FinOps — Cost & Usage Report (CUR) Automation, Athena
Analytics, QuickSight Visualization, Cost Category Chargeback, CUR 2.0
Split Cost Allocation.

## AWS documentation

- **AWS Cost and Usage Report User Guide** — https://docs.aws.amazon.com/cur/latest/userguide/what-is-cur.html
- **CUR Athena table integration** — https://docs.aws.amazon.com/cur/latest/userguide/athena.html
- **CUR 2.0 / BCM Data Exports** — https://docs.aws.amazon.com/cur/latest/userguide/bcm-data-exports.html
- **Split Cost Allocation Data** — https://docs.aws.amazon.com/cur/latest/userguide/split-cost-allocation-data.html
- **Athena partition projection** — https://docs.aws.amazon.com/athena/latest/ug/partition-projection.html
- **Athena workgroups** — https://docs.aws.amazon.com/athena/latest/ug/workgroups.html
- **AWS Cost Categories** — https://docs.aws.amazon.com/cost-management/latest/userguide/manage-cost-categories.html
- **Cost allocation tags** — https://docs.aws.amazon.com/cost-management/latest/userguide/alloc-tags.html
- **QuickSight Athena datasets** — https://docs.aws.amazon.com/quicksight/latest/user/create-a-data-set-athena.html
- **AWS CLI cur reference** — https://docs.aws.amazon.com/cli/latest/reference/cur/
- **AWS CLI bcm-data-exports reference** — https://docs.aws.amazon.com/cli/latest/reference/bcm-data-exports/
