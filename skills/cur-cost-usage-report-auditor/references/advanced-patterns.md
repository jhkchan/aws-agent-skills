# Advanced patterns - CUR Cost and Usage Report Auditor

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Step 0: Expert knowledge — non-obvious CUR behaviors that change classification

These behaviors are easy to misjudge without operational CUR experience.
Each changes a verdict if ignored:

- **CUR delivery is asynchronous and bounded.** Hourly files arrive
  within ~8 hours of the hour ending; daily files within ~24 hours of
  the day ending. The staleness thresholds (48h hourly / 72h daily) are
  6x and 3x the normal delivery window — well past any expected latency.
  A manifest 49 hours old is not "slow delivery"; it is a stopped pipeline.

- **The manifest file is the freshness signal, not the API.**
  `describe-report-definitions` returns configuration only — no status.
  The authoritative freshness signal is the `LastModified` timestamp of
  the latest `<report-name>-Manifest.json` in the S3 prefix. The console's
  "last refreshed" indicator caches for up to 1 hour and can mislead.

- **`cur-1.0` is the minimum viable schema version.** Legacy versions
  predate Savings Plans amortization columns, cost-category support, and
  the `lineItem/lineItemType` expansion (`Refund`, `Credit`, `EdpDiscount`).
  A legacy-version CUR may appear to "work" but silently drops cost
  adjustments that distort unit-economics dashboards.

- **Athena integration requires BOTH Parquet format AND the CFN crawler.**
  Setting `Format: Parquet` alone does NOT create the Athena table. CUR
  auto-generates an `athena_integration/crawler-cfn.yml` CloudFormation
  template in the report prefix. Without running it (or an equivalent
  `aws glue create-crawler`), Athena queries fail with "table not found."

- **The S3 bucket policy is CUR-specific.** The bucket must grant
  `s3:PutObject` and `s3:GetBucketAcl` to `billingreports.amazonaws.com`.
  Without this policy, CUR delivery silently fails — the API accepts
  the configuration, the console shows "active," but no files appear.
  Always verify actual S3 object existence, not just the API config.

- **No backfill on creation.** When you create a new CUR, it starts from
  the current billing period forward. Historical data does NOT backfill.
  A CUR created today has zero history — dashboards will show empty
  trends until data accumulates. This is not a staleness finding; it is
  an expected startup condition.

- **`RefreshClosedReports: false` freezes closed periods.** AWS posts
  late corrections (refunds, credits, Savings Plans true-ups) to
  previously-closed billing periods. If `RefreshClosedReports` is false,
  these corrections never propagate to the CUR — the line items are
  frozen at first delivery. This causes perpetual reconciliation drift
  between CUR and the Billing console.

- **Resource IDs are opt-in via AdditionalSchemaElements.** Without
  `"Resources"` in `AdditionalSchemaElements`, the CUR lacks the
  `lineItem/ResourceId` column entirely. You cannot attribute cost to
  individual EC2 instances, S3 buckets, or Lambda functions. Cost
  allocation tags still work, but resource-level visibility is absent.

- **Athena partition pruning is mandatory for cost control.** CUR data
  in Athena is partitioned by `{year}/{month}`. A query without
  `WHERE year = '2026' AND month = '01'` scans the ENTIRE dataset —
  potentially terabytes for a large account. The Glue crawler must run
  when new partitions arrive (monthly) or Athena won't see the new data.

- **Up to 50 report definitions per payer.** Multiple CURs allow
  different consumers (e.g., one Parquet+ATHENA for Athena queries,
  one CSV+GZIP for legacy tools). The account-level verdict is the
  worst across all definitions — one broken CUR can poison the pipeline.

- **`BillingViewArn` scopes the CUR to a billing view.** Available
  with AWS Organizations cost hierarchy, this lets a single CUR cover
  only a subset of linked accounts. If the BillingViewArn points to a
  deleted view, the CUR stops delivering silently.

- **S3 prefix encodes the billing period, not the delivery date.**
  CUR data is organized as
  `<S3Prefix>/<ReportName>/<YYYYMMDD-YYYYMMDD>/<assemblyId>/<files>`,
  where the date range is the *billing period* (e.g., `20260701-20260731`),
  NOT the day the file was delivered. You cannot use
  `list-objects-v2 --prefix .../2026-07-04/` to find "today's" hourly
  delivery — all July files share the same `20260701-20260731` prefix.
  To find the latest delivery, always sort by `LastModified`, never
  by key prefix. Auditors who filter by date-prefix get false NO_MANIFEST
  results.

- **Athena scan cost differential: Parquet vs CSV is ~10x.** The CUR
  `Format` field is not just about query-ability — it drives Athena
  billing. Parquet is columnar: a `SELECT sum(cost) WHERE service =
  'EC2'` scans only 2 columns, costing ~1/10th of the equivalent
  CSV/GZIP scan (which reads every row). For a mid-size account with
  ~200 GB/month of CUR data, a single unoptimized CSV full-table query
  can cost $5+; the same Parquet query costs under $0.50. This makes
  `Format: Parquet` a cost-optimization decision, not just a feature
  checkbox. When remediating CSV→Parquet, note that historical data
  already delivered as CSV remains CSV — only future deliveries switch
  to Parquet, so Athena queries spanning the cutover must UNION both
  formats or filter by date.

- **Glue partition schema drift after `put-report-definition`.** When
  you update a CUR definition (e.g., adding `Resources` to
  `AdditionalSchemaElements`), the Glue *table* schema updates on the
  next crawler run, but **existing partitions retain their original
  schema**. Athena queries on old partitions return `NULL` for the new
  `lineItem/ResourceId` column — they do not error, they silently
  produce empty values. This is MSCK-repair-resistant: `MSCK REPAIR
  TABLE` adds missing partitions but does NOT update their schemas.
  The fix is `ALTER TABLE ... SET LOCATION` per-partition or a full
  crawler re-crawl with `CrawlerConfiguration: { Configuration: {
    Version: 1.0, CrawlerOutput: { Partitions: { AddOrUpdateBehavior:
    "UpdateAllPartitionsAndTable" } } } }`. Without this, operators
  see a "working" Athena table with mysterious NULLs in new columns
  for all pre-migration data.

## Deep reference: CUR delivery internals

### Manifest file structure

Each CUR delivery produces a manifest JSON at
`s3://<bucket>/<prefix>/<report-name>/<billing-period>/<report-name>-Manifest.json`.
The manifest contains:
- `reportId` — unique UUID for this delivery.
- `billingPeriod` — `{start: "2026-07-01T00:00:00Z", end: "2026-08-01T00:00:00Z"}`.
- `columns` — ordered list of column names for the billing period.
- `reportKeys` — S3 keys for the actual data files (Parquet or CSV).

The column list can change between billing periods (AWS adds new
columns). Downstream transforms must read column names from the manifest,
not hardcode them.

### Athena integration flow

1. CUR writes Parquet files partitioned by `{year}/{month}` under the
   report prefix.
2. CUR writes `athena_integration/crawler-cfn.yml` — a CloudFormation
   template that creates a Glue Data Catalog database (`athenacur`),
   table, and crawler.
3. Running the CFN stack creates the table with the correct schema
   mapping and a crawler that updates partitions when new data arrives.
4. The crawler must be re-run monthly (or triggered by a CloudWatch
   Events rule) to add the new month's partition. Without this, Athena
   queries on the new month return zero rows.
5. The Athena workgroup must be in the SAME REGION as the S3 bucket
   to avoid cross-region data transfer charges.

### Late-arrival and bill-close processing

At the start of each billing period (1st of the month), AWS re-delivers
the ENTIRE prior month's data with all late corrections applied
(refunds, credits, Savings Plans true-ups). This is why
`RefreshClosedReports: true` matters — it ensures the CUR reflects these
corrections. During bill-close (1st-2nd of each month), the delivery
pattern changes: the full-month re-delivery takes priority over hourly
files, causing a temporary lag in the latest hour's data.

### Payer vs linked account restriction

CUR is configured at the payer (management) account level. Linked
(member) accounts cannot create, modify, or even see CUR definitions —
`describe-report-definitions` on a linked account always returns empty.
This is by design: the billing data belongs to the payer. For
organizations using AWS Organizations cost hierarchy, the
`BillingViewArn` field scopes a CUR to a specific billing view (a
subset of linked accounts).

## Recent AWS features (2024-2026)

- **CUR 2.0 with FOCUS spec support (2024-2025):** AWS introduced CUR 2.0 with alignment to the FinOps Open Cost and Usage Specification (FOCUS). Auditors should verify that CUR 2.0 reports are configured for cross-cloud FinOps tooling compatibility — the schema differs from CUR 1.0.
- **Hourly refresh improvements:** CUR delivery now supports more reliable hourly refresh. Auditors should verify that the report version and refresh cadence meet the organization's FinOps requirements.
- **Athena integration with CUR 2.0:** Athena integration now works with CUR 2.0 format. Auditors should verify that Athena table DDL matches the CUR version in use.
