---
name: cur-cost-usage-report-auditor
description: >-
  Audits AWS Cost and Usage Report (CUR) configurations for coverage gaps,
  data staleness, report-version drift, missing Athena integration, disabled
  S3 bucket versioning, and time-horizon limits. Emits a deterministic
  verdict (NO_CUR | STALE | CONFIG_GAP | OK) per report definition or payer
  account. Use when reviewing CUR health, checking whether Athena cost
  queries are wired, validating hourly refresh cadence, or auditing FinOps
  data pipeline posture before a cost-optimization initiative.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline config classification. Live-account
  audits use aws cur describe-report-definitions, aws s3api get-bucket-versioning,
  aws glue get-table, and aws s3api head-object (AWS CLI v2, SSO or key-based
  credentials).
keywords:
  - CUR
  - Cost and Usage Report
  - billing
  - FinOps
  - cost visibility
  - Athena integration
  - Parquet
  - cur-1.0
  - hourly refresh
  - S3 versioning
  - Glue Data Catalog
  - cost allocation
  - report staleness
  - payer account
  - Resource IDs
  - manifest file
  - RefreshClosedReports
tags: [cur, finops, cost-optimization, billing, athena, s3, audit]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: FinOps
  verdict_shape: "NO_CUR | STALE | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing a CUR configuration for FinOps pipeline health, checking whether
    Athena integration is wired, validating hourly refresh cadence, auditing
    S3 bucket versioning for CUR data, or diagnosing why Athena cost queries
    return empty or stale results.
  activation_triggers:
    - "audit this Cost and Usage Report"
    - "is my CUR configured correctly"
    - "check CUR Athena integration"
    - "why is my CUR stale"
    - "CUR report version check"
    - "is hourly refresh enabled"
    - "CUR S3 bucket versioning"
    - "FinOps data pipeline audit"
    - "CUR not delivering to S3"
    - "Athena cost query empty"
  invocation_schema: >-
    Input: either (a) a CUR report definition JSON (from aws cur
    describe-report-definitions) optionally paired with S3 bucket metadata
    (versioning status, latest manifest timestamp) and Glue table status,
    OR (b) a payer account id for live-account audit. Output: deterministic
    REPORT/VERDICT/REASON/FINDINGS/REMEDIATION block per report definition,
    where VERDICT ∈ {NO_CUR, STALE, CONFIG_GAP, OK, ERROR}.
---

# CUR Cost and Usage Report Auditor

## Mindset

**One-line takeaway:** CUR is the only source of line-item-granular cost
data in AWS. The verdict cascades: no CUR → nothing else matters; stale
CUR → wrong decisions; config gap → blind spots; OK → pipeline is healthy.

CUR underpins every FinOps pipeline. Three properties determine its health:
- **Existence** — without CUR there is zero line-item cost visibility.
  Cost Explorer is aggregated (service/daily), and Budgets is threshold-
  based. Neither gives per-resource hourly spend needed for attribution.
- **Freshness** — CUR files are delivered asynchronously (within ~8h for
  hourly, ~24h for daily). A stale CUR feeds dashboards outdated data,
  causing missed anomalies and wrong forecasts.
- **Completeness** — a fresh CUR can still have blind spots: wrong report
  version (missing Savings Plans columns), no Athena integration (can't
  query), no S3 versioning (no recovery), missing resource IDs (can't
  attribute cost to individual resources).

## Quick reference — verdict thresholds

| Condition | Verdict | Rule |
|---|---|---|
| Zero report definitions on the payer account | **NO_CUR** | Step 1 |
| Hourly CUR, latest manifest > 48h old | **STALE** | Step 2a |
| Daily CUR, latest manifest > 72h old | **STALE** | Step 2b |
| ReportVersion is not `cur-1.0` | **CONFIG_GAP** | Step 3a |
| Format is not `Parquet` (blocks Athena) | **CONFIG_GAP** | Step 3b |
| AdditionalArtifacts does not include `ATHENA` | **CONFIG_GAP** | Step 3c |
| S3 bucket versioning is `Suspended` or not enabled | **CONFIG_GAP** | Step 3d |
| AdditionalSchemaElements does not include `Resources` | **CONFIG_GAP** | Step 3e |
| RefreshClosedReports is `false` | **CONFIG_GAP** | Step 3f |
| All dimensions pass | **OK** | Step 4 |

See the ordered steps below for edge cases. Deep CUR delivery internals
(manifest format, partition pruning, late-arrival reprocessing) are in
the [Deep reference](#deep-reference-cur-delivery-internals) section.

## Input schema — concrete examples

**Mode A — offline config audit (report-definition JSON):**

```json
{
  "ReportName": "cur-hourly-athena",
  "TimeUnit": "HOURLY",
  "Format": "Parquet",
  "Compression": "Parquet",
  "AdditionalSchemaElements": ["Resources"],
  "S3Bucket": "my-cur-bucket",
  "S3Prefix": "cur",
  "S3Region": "us-east-1",
  "AdditionalArtifacts": ["ATHENA"],
  "RefreshClosedReports": true,
  "ReportVersion": "cur-1.0",
  "BillingViewArn": null
}
```

Paired metadata (optional but recommended for full audit):
```json
{
  "bucket_versioning_status": "Enabled",
  "latest_manifest_timestamp": "2026-08-02T04:15:00Z",
  "glue_table_exists": true,
  "cur_created_at": "2026-06-01T10:00:00Z"
}
```

**Mode B — live-account audit (payer account id only):**
```json
{ "payer_account_id": "123456789012" }
```

Valid `Format` values: `Parquet` | `textORcsv` (the literal API enum —
CSV with optional GZIP). Valid `TimeUnit` values: `HOURLY` | `DAILY`.
Valid `ReportVersion`: `cur-1.0` only (legacy omitted from API output).

## Pre-flight: account context gate

Before evaluating CUR configuration, classify the account context.
Several conditions short-circuit the audit — misclassifying them produces
false NO_CUR verdicts.

**Live-account pre-flight checks (skip for offline config audit):**
1. Confirm the target account is the **payer (management) account**, not
   a linked (member) account. CUR is a billing-account-level service —
   `aws cur describe-report-definitions` on a linked account returns an
   empty list even if the payer has CUR configured. This is NOT a NO_CUR
   finding; it is an account-context error.
2. Run API calls in `us-east-1`. The CUR service endpoint is
   `cur.us-east-1.amazonaws.com`. Calls in other regions may silently
   return empty results or `AccessDeniedException` depending on the
   IAM policy region scoping.
3. Snapshot the latest manifest timestamp BEFORE classification:
   `aws s3api list-objects-v2 --bucket <bucket> --prefix <prefix>/
   <report-name>/ --query 'Contents[?ends_with(Key,`-Manifest.json`)]
   .[LastModified]' --output text | sort | tail -1`
   This gives the authoritative freshness signal — more reliable than
   the console's "last refreshed" indicator, which caches for up to 1h.

| Attribute | Effect on audit |
|---|---|
| Account type: linked (member) | CUR cannot be created here — only the **payer** account can configure CUR. Empty report list is EXPECTED. Output `VERDICT: ERROR` with note "CUR is a payer-account service; run this audit on the management account." |
| Account type: payer (management) | Proceed with full audit. |
| Multiple report definitions | Audit each independently. A payer can have up to 50 CUR definitions. Aggregate the worst verdict across all definitions for the account-level rollup. |
| Region of API call | Must be `us-east-1`. Other regions may return stale or empty results. |

### Error handling — API and input failures

**IAM permission errors:** If `describe-report-definitions` returns
`AccessDeniedException`, the caller lacks `cur:DescribeReportDefinitions`.
Emit `VERDICT: ERROR` — this is an IAM failure, not a NO_CUR finding.
Required minimum policy for the auditor role: `cur:DescribeReportDefinitions`,
`s3:ListBucket`, `s3:GetObject`, `glue:GetTable`. Verify with
`aws iam simulate-principal-policy` before reporting NO_CUR.

**API throttling:** The CUR API has a low TPS limit (~1 TPS per payer
account). For multi-account sweeps, serialize calls with 1s delay. If
`ThrottlingException` occurs, retry with exponential backoff (2s, 4s, 8s).

**Malformed input:** If the report-definition JSON is invalid (missing
required fields, non-parseable), emit `VERDICT: ERROR` with the specific
field name. Do NOT attempt classification on malformed input — a missing
`TimeUnit` or `Format` field makes staleness and CONFIG_GAP checks
unreliable.

**Missing manifest with bucket access:** If `list-objects-v2` returns
empty but the bucket exists and has objects, verify the prefix path
matches `S3Prefix + "/" + ReportName + "/"`. A trailing-slash mismatch
is the most common cause of "no manifest found" false positives.

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious CUR behaviors that change classification

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

### Step 1: NO_CUR — existence check (highest priority — zero cost visibility)

If the payer account has zero report definitions
(`describe-report-definitions` returns `ReportDefinitions: []`), the
verdict is **NO_CUR**. This is the worst posture — there is no line-item
cost data at all. FinOps pipelines, cost-allocation analytics, and
per-resource attribution all depend on CUR existence.

A linked account returning empty is NOT NO_CUR — it is an account-context
error (see Pre-flight gate).

### Step 2: STALE — freshness check (data pipeline has stopped)

Extract the latest manifest timestamp from S3 (see Pre-flight step 3).
If no manifest exists in the prefix at all, treat as STALE (the CUR was
configured but has never delivered — a broken delivery pipeline).

- **Step 2a — Hourly cadence:** If `TimeUnit: HOURLY` and the latest
  manifest is **more than 48 hours** old → **STALE**. Hourly files
  deliver within ~8h; 48h is 6x the delivery window. At this threshold,
  delivery has definitively stopped, not merely lagged.

- **Step 2b — Daily cadence:** If `TimeUnit: DAILY` and the latest
  manifest is **more than 72 hours** old → **STALE**. Daily files
  deliver within ~24h; 72h is 3x the delivery window.

- **Edge case — newly created CUR (< 48h old):** A CUR created within
  the last 48 hours has not yet delivered its first file. This is NOT
  stale — it is the expected startup window. Check the CUR creation
  timestamp (or the report definition's first-seen date) before applying
  the staleness threshold. Emit a note: "CUR created <48h ago; first
  delivery pending — check again after 8h."

- **Edge case — end of billing period:** CUR re-delivers the entire
  billing period's data at the start of each new period (bill-close
  processing). During this window (~6-12h around the 1st of each month),
  the latest manifest timestamp may be 24-36h old for hourly CURs. This
  is expected; do not flag as STALE if the current date is within 2 days
  of a billing-period boundary.

### Step 3: CONFIG_GAP — completeness check (configuration defects)

If the CUR exists and is fresh, evaluate each configuration dimension.
Any dimension that fails → **CONFIG_GAP**. Apply in order — the first
failing dimension produces the verdict, but enumerate ALL failing
dimensions in FINDINGS:

- **Step 3a — Report version:** If `ReportVersion` is not `cur-1.0`
  (or not present, which defaults to legacy), the CUR uses the old
  schema. Missing columns: Savings Plans amortization, cost categories,
  expanded `lineItemType` values. This causes reconciliation drift and
  breaks downstream transforms that expect `cur-1.0` columns.

- **Step 3b — Format:** If `Format` is not `Parquet`, Athena integration
  is impossible. CSV/GZIP formats cannot be queried by Athena via the
  standard CUR Glue table. A CUR without Athena integration requires
  manual S3 downloads and local parsing — impractical for any real
  FinOps workflow.

- **Step 3c — AdditionalArtifacts:** If `AdditionalArtifacts` does not
  include `ATHENA`, CUR will not generate the `athena_integration/`
  prefix with the CloudFormation crawler template. Even with
  `Format: Parquet`, the Athena table will not be auto-created.
  Check for `REDSHIFT` and `QUICKSIGHT` artifacts as informational
  findings (they add value but are not required for core Athena flow).

- **Step 3d — S3 bucket versioning:** If the CUR destination bucket has
  `Status: Suspended` or no versioning configuration, CUR data files
  have no point-in-time recovery. A botched downstream transform (e.g.,
  a Glue job that overwrites the CUR prefix) permanently destroys the
  original data. S3 versioning is the only recovery mechanism for CUR
  data — CUR itself does not version its outputs.

- **Step 3e — AdditionalSchemaElements (Resources):** If
  `AdditionalSchemaElements` does not include `Resources`, the CUR lacks
  the `lineItem/ResourceId` column. Cost cannot be attributed to
  individual resources — only to service/account/tag level. This blinds
  per-resource right-sizing and waste-detection efforts.

- **Step 3f — RefreshClosedReports:** If `RefreshClosedReports` is
  `false`, previously-closed billing periods are frozen at first
  delivery. Late corrections (refunds, credits, Savings Plans true-ups,
  edp discounts) never propagate. The CUR will perpetually disagree with
  the Billing console for any month that receives post-close adjustments.

### Step 4: OK — all dimensions pass

If the CUR exists, is fresh, and passes all CONFIG_GAP checks (Steps
3a-3f), the verdict is **OK**. The FinOps data pipeline is healthy.

For an account-level rollup with multiple CUR definitions, the account
verdict is the **worst** across all definitions:
`NO_CUR > STALE > CONFIG_GAP > OK`.

## Output format (per report definition)

```text
REPORT: <report-name>
VERDICT: NO_CUR | STALE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the specific finding and step number>
FINDINGS:
  - [CRITICAL] <finding description (Step Na)>
  - [HIGH] <finding description (Step Nb)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

**Per-finding severity mapping:**
- NO_CUR → **CRITICAL** — zero line-item cost visibility
- STALE → **HIGH** — data pipeline stopped; dashboards unreliable
- CONFIG_GAP Step 3a (legacy version) → **HIGH** — missing cost columns
- CONFIG_GAP Step 3b/3c (no Athena) → **HIGH** — no query capability
- CONFIG_GAP Step 3d (no versioning) → **MEDIUM** — no data recovery
- CONFIG_GAP Step 3e (no Resources) → **MEDIUM** — no resource attribution
- CONFIG_GAP Step 3f (no refresh closed) → **MEDIUM** — reconciliation drift
- OK → **LOW**

### Worked example — stale CUR with Athena gap

```text
REPORT: my-cur-hourly
VERDICT: STALE
REASON: Latest manifest is 9 days old for an hourly-cadence CUR (Step 2a)
— delivery pipeline has stopped. Athena integration is also misconfigured.
FINDINGS:
  - [HIGH] Hourly CUR manifest last delivered 9 days ago; staleness
    threshold is 48h (Step 2a)
  - [HIGH] Format is CSV/GZIP — Athena integration is not possible (Step 3b)
  - [MEDIUM] AdditionalArtifacts missing ATHENA (Step 3c)
  - [MEDIUM] S3 bucket versioning is Suspended (Step 3d)
REMEDIATION:
  1. HIGH — Verify the S3 bucket policy grants billingreports.amazonaws.com
     PutObject + GetBucketAcl. Check for deleted BillingViewArn.
     Re-run: aws cur describe-report-definitions to confirm config is intact.
  2. HIGH — Update Format to Parquet: aws cur put-report-definition
     --report-definition file://cur-def.json (Format: Parquet)
  3. MEDIUM — Add 'ATHENA' to AdditionalArtifacts in the report definition.
  4. MEDIUM — Enable S3 versioning:
     aws s3api put-bucket-versioning --bucket <bucket>
     --versioning-configuration Status=Enabled
```

## Anti-Patterns — NEVER

- NEVER classify a linked (member) account with zero CUR definitions as
  NO_CUR. CUR is a payer-account service; linked accounts inherit the
  payer's configuration. Flag as ERROR with a redirect to the management
  account.

- NEVER treat a CUR created within the last 48 hours with no manifest
  as STALE. The first delivery window is ~8h for hourly and ~24h for
  daily. Apply the staleness threshold only after the startup window.

- NEVER flag a CUR as CONFIG_GAP for missing `REDSHIFT` or `QUICKSIGHT`
  artifacts. Only `ATHENA` is required for standard FinOps query
  workflows. REDSHIFT/QUICKSIGHT are add-on integrations.

- NEVER recommend deleting and recreating a CUR to fix a config gap.
  Deleting destroys the historical prefix structure and the Glue table
  partition map. Use `aws cur put-report-definition` with the updated
  definition (it overwrites the existing one while preserving S3 history).

- NEVER assume `Format: Parquet` alone means Athena is working. The
  CloudFormation crawler template (`athena_integration/crawler-cfn.yml`)
  must have been executed. Verify with `aws glue get-table` — a missing
  table means Athena queries will fail regardless of the format.

- NEVER treat a missing manifest during the first 2 days of a billing
  period as STALE. AWS re-delivers the entire prior billing period
  during bill-close processing (1st-2nd of each month), causing a
  temporary delivery lag. Check the calendar before flagging.

- NEVER report OK without verifying actual S3 object existence. A CUR
  can show "active" in the API and console while silently failing to
  deliver (deleted bucket policy, wrong region, deleted BillingViewArn).
  The manifest file in S3 is the ground truth — the API is a config
  mirror, not a delivery confirmation.

- NEVER ignore a `BillingViewArn` that points to a deleted or modified
  billing view. This silently stops CUR delivery with no error or alert.
  Check the view exists: `aws billingvisions list-billing-views`.

- NEVER recommend Athena queries without partition filters. CUR data
  is partitioned by `{year}/{month}`. A full-table scan on a large
  account can cost hundreds of dollars in a single query. Always include
  `WHERE year = '...' AND month = '...'` in remediation examples.

- NEVER assume a single CUR definition covers all needs. A payer with
  one CSV-format CUR and no Athena integration has CONFIG_GAP even if
  data is fresh. The completeness dimension is independent of freshness.

- NEVER classify `AccessDeniedException` from `describe-report-definitions`
  as NO_CUR. An IAM permission failure (`cur:DescribeReportDefinitions`
  missing) produces the same empty result as a payer with zero CURs.
  Always verify the caller's IAM policy before reporting NO_CUR — a false
  NO_CUR sends the operator on a pointless CUR-creation workflow.

- NEVER swallow `ThrottlingException` from the CUR API. The CUR endpoint
  has a ~1 TPS limit per payer. For multi-account sweeps, serialize calls
  with 1s delay. Retrying with exponential backoff (2s, 4s, 8s) is safe;
  ignoring the throttle produces empty results that look like NO_CUR.

- NEVER ignore cross-region bucket-policy mismatches. The CUR delivery
  bucket policy grants `s3:PutObject` to
  `billingreports.amazonaws.com` with a `StringEquals` condition on
  `aws:SourceBucketAccount` and a `s3:x-amz-acl` condition. If the
  bucket is in a different region from the CUR's `S3Region`, or if a
  `Condition` key restricts to `aws:SourceIp` ranges that exclude
  AWS billing infrastructure, CUR delivery fails silently — the API
  shows "active" but no objects arrive. Always compare the bucket
  region against `S3Bucket`/`S3Region` in the report definition, and
  verify no `Condition` block excludes billing service principals.

- NEVER overlook S3 lifecycle rules that target the CUR prefix. A
  lifecycle policy with `Expiration` or `NoncurrentVersionExpiration`
  on the CUR prefix silently deletes old CUR objects — including
  manifests and assembly files. This causes historical data gaps that
  look like "CUR was just created" when objects older than the rule's
  `Days` value are gone. Before classifying a CUR as healthy, run
  `aws s3api get-bucket-lifecycle-configuration --bucket <bucket>`
  and verify no rule matches the CUR `S3Prefix`. A common mistake:
  a blanket rule expiring objects after 30 days on the entire bucket
  wipes monthly CUR files before bill-close reprocessing can use them.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (put-report-definition, delete-report-definition, put-bucket-versioning,
  put-bucket-policy), the auditor MUST emit:
  `CONFIRM: About to <action> on report <name> / bucket <bucket>. This
  affects <consequence>. Proceed? (yes/no)`
- **Back up the current report definition before modifying:**
  `aws cur describe-report-definitions --output json >
  /tmp/cur-backup-$(date +%s).json`
  CUR definitions are overwritten atomically — no rollback without backup.
- **Back up the S3 bucket policy before modifying:**
  `aws s3api get-bucket-policy --bucket <bucket> --output json >
  /tmp/<bucket>-policy-backup-$(date +%s).json`
- **Verify the S3 bucket exists and is writable by CUR:**
  `aws s3api head-bucket --bucket <bucket>` — fail closed if it errors.
- Before enabling S3 versioning on an existing bucket, warn the operator
  that versioning increases storage costs (all object versions retained).
  Recommend adding an S3 lifecycle policy to expire non-current versions
  after 90 days.
- Prefer `put-report-definition` (overwrites in place, preserves S3
  history) over delete+recreate (destroys prefix structure).

## Remediation guidance

### For NO_CUR — no CUR configured

1. Create a CUR with the recommended configuration:
   ```bash
   aws cur put-report-definition --report-definition '{
     "ReportName": "cur-hourly-athena",
     "TimeUnit": "HOURLY",
     "Format": "Parquet",
     "Compression": "Parquet",
     "AdditionalSchemaElements": ["Resources"],
     "S3Bucket": "<your-cur-bucket>",
     "S3Prefix": "cur/",
     "S3Region": "us-east-1",
     "AdditionalArtifacts": ["ATHENA"],
     "RefreshClosedReports": true,
     "ReportVersion": "cur-1.0"
   }' --profile <p>
   ```
2. Ensure the S3 bucket has the CUR delivery policy (grant
   `billingreports.amazonaws.com` PutObject + GetBucketAcl).
3. Enable S3 versioning on the bucket.
4. After ~8 hours, verify delivery:
   `aws s3api list-objects-v2 --bucket <bucket> --prefix cur/cur-hourly-athena/`
5. Run the Athena CloudFormation template that CUR auto-generates at
   `s3://<bucket>/cur/cur-hourly-athena/athena_integration/crawler-cfn.yml`.

### For STALE — data pipeline has stopped

1. Verify the S3 bucket still exists and has the CUR delivery policy.
2. Check if `BillingViewArn` points to a deleted view.
3. Check if the bucket policy was modified (e.g., by a third-party tool).
4. If the bucket is intact, verify the CUR definition:
   `aws cur describe-report-definitions --output json`.
5. If config is intact but no files arrive, open an AWS Support case
   (Billing category) — CUR delivery may have an upstream issue.
6. After the pipeline resumes, verify with:
   `aws s3api list-objects-v2 --bucket <bucket> --prefix <prefix>/
   <report-name>/ --query 'reverse(sort_by(Contents,&LastModified))[0]'`

### For CONFIG_GAP — Step 3a (legacy version)

1. Update the report definition with `ReportVersion: cur-1.0`:
   ```bash
   aws cur put-report-definition --report-definition file://updated-cur.json
   ```
   Include `ReportVersion: cur-1.0` in the definition JSON.

### For CONFIG_GAP — Steps 3b/3c (no Athena)

1. Change `Format` to `Parquet` and add `ATHENA` to `AdditionalArtifacts`.
2. Re-run `describe-report-definitions` to confirm the change took effect.
3. Navigate to the `athena_integration/` prefix and run the
   `crawler-cfn.yml` CloudFormation template to create the Glue table.
4. Verify the Athena table:
   `aws glue get-table --database athenacur --name <report-name>`

### For CONFIG_GAP — Step 3d (no S3 versioning)

1. Enable versioning:
   ```bash
   aws s3api put-bucket-versioning --bucket <bucket> \
     --versioning-configuration Status=Enabled --profile <p>
   ```
2. Add a lifecycle policy to expire non-current versions after 90 days
   to control storage costs.

### For CONFIG_GAP — Step 3e (no Resources)

1. Add `"Resources"` to `AdditionalSchemaElements` in the report
   definition and update via `put-report-definition`.
2. Note: existing historical data will NOT retroactively include
   ResourceId — only data from the update forward will have it.

### For CONFIG_GAP — Step 3f (RefreshClosedReports false)

1. Set `RefreshClosedReports: true` in the report definition.
2. The next billing-period close will trigger a full re-delivery of the
   prior period with corrections applied.

### For OK

1. No remediation required for the current posture.
2. Recommend verifying the Glue crawler runs monthly to add new
   partitions: `aws glue start-crawler --name <crawler-name>`.
3. Recommend adding an S3 lifecycle policy to transition old CUR data
   to Glacier after 12 months if long-term retention is required.
4. Recommend monitoring CUR delivery with a CloudWatch alarm on S3
   `PutObject` events for the CUR prefix (detect staleness early).

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

## Domain

AWS CloudOps / FinOps — Cost Visibility and Data Pipeline Health.
