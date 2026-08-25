# Advanced patterns - CUR Automation Automator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Step 0: Expert knowledge — non-obvious CUR behaviors

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
