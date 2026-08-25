# Advanced Patterns (load on demand) — AWS Budget Deployer

Edge-case catalogs, expert-knowledge deep dives, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Cross-dependency gotchas (moved from SKILL.md)

**Cross-dependency gotchas:**

- A budget action targeting a linked account requires the action role
  in THAT linked account, not the payer. A common error is provisioning
  the role in the payer and expecting it to apply an IAM policy to an
  IAM principal in a linked account.
- SNS topics with SSE-KMS will silently drop notifications from Budgets
  unless the KMS key policy grants `kms:GenerateDataKey*` and
  `kms:Decrypt` to `budgets.amazonaws.com` and
  `ce.amazonaws.com`. AWS-managed KMS keys (`alias/aws/sns`) work
  out-of-the-box.
- Budget notifications on `FORECAST` alerts fire earlier than `ACTUAL`
  but forecast is a trailing model — it is less accurate in the first
  ~14 days of a budget period.
- Usage budgets (RI/SP utilization/coverage) do NOT support budget
  actions — only SNS/email/Slack notifications. Do not attempt to wire
  an IAM policy/EC2 stop action on a usage budget; the API rejects it.

## Expert heuristic: anomaly detection sensitivity tuning (moved from SKILL.md)

Cost Anomaly Detection uses a machine-learning model on your historical
Cost Explorer usage data. The model needs **at least ~30 days** of
history before its predictions are reliable. Three configuration choices
dominate false-positive rates:

- **`Feedback` API (`put-feedback`)**: the model does NOT auto-learn
  from SNS-dismissed alerts. You must explicitly call
  `aws ce put-feedback --anomaly-id <id> --is-anomaly NO` to suppress a
  false positive. Operators frequently mark alerts as "not an anomaly"
  in the console but do not realize the model only updates via
  `put-feedback`. Plan for this in the runbook.
- **Subscription `Threshold`**: the dollar amount above which an
  anomaly is published to SNS. Default is `$0`. **Always set a
  threshold** (typical: `$100` or `$1000` depending on total account
  spend). A `$0` threshold produces daily noise from minor variances.
- **Monitor `MonitorSpecification`**: a service-scoped monitor
  (`Dimension=SERVICE`) gives cleaner signals than the default
  account-wide monitor. For multi-service accounts, provision per-
  service dimensional monitors rather than relying on the
  account-wide one.

## Expert heuristic: API, cost, and timing quirks (moved from SKILL.md)

These operational details are not in the Budgets documentation front
page but cause real production incidents:

- **Budgets has a free tier of 2 budgets per account.** The first 2
  budgets (cost or usage) are free; each additional budget costs
  ~$0.10/day (~$3/month). This is rarely surfaced during provisioning
  and shows up as an unexpected line item. For organizations with 50+
  linked accounts each getting 3 budgets, the budget cost itself can
  exceed $1,500/month. Consolidate to payer-level budgets with
  `CostFilters` for linked-account scoping rather than provisioning
  per-linked-account budgets.

- **The Budgets API has a throttling limit of ~1 update per second
  per account.** `update-budget`, `create-notification`, and
  `create-budget-action` share this limit. Terraform/CloudFormation
  runs that update dozens of budgets in parallel will hit
  `ThrottlingException`. Sequence budget updates with a 1.5-second
  delay between calls. The limit is account-wide, not per-budget.

- **The forecast model loses accuracy in the first 10-14 days of a
  budget period.** AWS Budgets forecast uses a trailing weighted
  average of the last 14-21 days of actual spend. In the first half
  of a monthly budget period, the forecast is extrapolated from
  sparse data and can be off by 30-50%. FORECAST alerts that fire in
  days 1-14 are unreliable; treat them as informational. After day
  15, forecast accuracy improves to within ~10-15% of actual.

- **RI/SP coverage and utilization budgets evaluate every 6-8 hours,
  not in real time.** Usage budgets (`RI_UTILIZATION`, `RI_COVERAGE`,
  `SP_UTILIZATION`, `SP_COVERAGE`) pull from Cost Explorer's usage
  data pipeline, which has a 6-8 hour processing delay. A budget
  alert for RI utilization dropping below 80% may fire 6-8 hours
  after the actual utilization change. For time-sensitive RI/SP
  monitoring, supplement with CloudWatch + Cost Explorer API polling
  at higher frequency.

- **Cost allocation tag activation has a 12-24 hour propagation
  delay.** Activating a tag key in Billing -> Cost Allocation Tags
  does not make the tag immediately available in
  `CostFilters.TagKeyValue`. Budgets created with a tag filter
  before the tag is fully propagated will return zero spend until
  the tag data flows through. Always verify tag activation via
  `aws ce get-cost-and-usage --group-by Type=TAG,Key=<key>` before
  creating a tag-scoped budget.

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Savings Plan Budget alerts (2024-2025 GA):** AWS Budgets now
  supports `SP_UTILIZATION` and `SP_COVERAGE` budget types natively.
  Previously these were only available via Cost Explorer queries. The
  Budgets API surfaces them as first-class usage budgets with SNS/email
  notifications (no actions — see Step 4 constraint).
- **Cost Anomaly Detection Feedback API GA (2024-2025):**
  `aws ce put-feedback` lets operators annotate false positives and
  true positives directly via CLI. The ML model learns ONLY from
  explicit feedback — console "dismiss" does not train it. Plan a
  runbook step to call `put-feedback` for each reviewed anomaly.
- **Anomaly Monitor `MonitorSpecification` JSON (2024-2025):**
  dimensional monitors now accept a `MonitorSpecification` JSON filter
  for `ANOMALY_TOTAL_IMPACT_ABSOLUTE` and
  `ANOMALY_TOTAL_IMPACT_PERCENTAGE`. Provisioning tip: set both —
  dollar for absolute impact, percent for relative impact.
- **Budget Actions regional expansion (2024-2025):** `RUN_SSM_DOCUMENTS`
  now supports `STOP_RDS_INSTANCE` (in addition to
  `STOP_EC2_INSTANCES`). Use for non-production databases.
- **Cost Explorer tag-based filters in Budgets (2024):**
  `CostFilters.TagKeyValue` now accepts up to 50 tag key-value pairs
  per budget (up from 10). Provisioning tip: complex tag filters still
  require tags to be activated in Billing → Cost Allocation Tags.
