---
name: cloudwatch-dashboards-operator
description: Operates Amazon CloudWatch dashboards end-to-end — dashboard creation and update via JSON model (PutDashboard/GetDashboard API), custom widgets backed by Lambda functions, cross-account dashboards via CloudWatch Observability Access Manager (OAM) shared observability, metric math expressions for derived calculations, anomaly detection bands, alarm integration in dashboard widgets, dashboard sharing via resource-based policy, dashboard variables and parameters, auto-refresh intervals, cross-section (account and region switching), dashboard templates for common AWS services (RDS, EC2, Lambda, ECS), dashboard API automation for version-controlled IaC, and CloudWatch Metrics Insights for SQL-like metric queries. Runs deterministic pre-checks (dashboard JSON validity, Lambda widget permissions, OAM sink/source configuration, metric namespace existence) behind a CONFIRM gate and emits OPERATION_COMPLETED or REVIEW_REQUIRED per operation. Use when creating service dashboards, adding metric math or anomaly...
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws cloudwatch put-dashboard, get-dashboard, delete-dashboards, list-dashboards, put-metric-alarm, describe-alarms-for-metric, aws oam create-sink, create-link, aws lambda add-permission (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPERATION_COMPLETED | REVIEW_REQUIRED
  when_to_use: Creating or updating a CloudWatch dashboard via JSON model, adding metric math expressions or anomaly detection bands, integrating alarms into dashboard widgets, building cross-account dashboards via OAM, creating Lambda-backed custom widgets, sharing dashboards via resource-based policy, templating dashboards for common services (RDS, EC2, Lambda, ECS), running Metrics Insights queries in dashboards, or automating dashboard lifecycle via PutDashboard API for version-controlled IaC.
  activation_triggers: create CloudWatch dashboard, update dashboard JSON, PutDashboard API, metric math expression, anomaly detection band, add alarm to dashboard, cross-account dashboard, OAM shared observability, dashboard sharing, dashboard variables, custom widget Lambda, dashboard template, RDS monitoring dashboard, EC2 monitoring dashboard, Lambda monitoring dashboard, ECS monitoring dashboard, Metrics Insights query, version-controlled dashboard, dashboard IaC
  invocation_schema: 'Input: either (a) a dashboard specification (service type, metric names, layout preference) plus the intended operation (create- dashboard, update-dashboard, add-metric-math, add-anomaly-detection, share-dashboard, enable-cross-account, add-custom-widget, delete- dashboard), OR (b) a dashboard name + operation for live-account execution. Output: deterministic OPERATION / VERDICT / PRE_CHECKS / STEPS / POST_VERIFY / NOTES block per dashboard operation, where VERDICT is OPERATION_COMPLETED or REVIEW_REQUIRED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CloudWatch dashboard, PutDashboard, GetDashboard, dashboard JSON, custom widget, Lambda widget, metric math, anomaly detection, alarm integration, cross-account dashboard, OAM, observability access manager, shared observability, dashboard sharing, dashboard variables, dashboard template, Metrics Insights, RDS dashboard, EC2 dashboard, Lambda dashboard, ECS dashboard, auto-refresh, dashboard IaC
  tags: aws, cloudwatch, dashboard, monitoring, observability, metrics, oam, management, operate
---

# CloudWatch Dashboards Operator

## What this skill does

Executes CloudWatch dashboard operations correctly and safely. Runs
deterministic pre-checks before any state-changing API call (dashboard
JSON validity, widget metric namespace existence, Lambda custom-widget
permissions, OAM sink/source configuration, resource-based policy for
sharing), executes the operation behind a CONFIRM gate, and verifies
the result by confirming the dashboard renders and all widgets return
data. Every create-dashboard operation produces a complete JSON model
suitable for PutDashboard API or IaC pipelines; every update-dashboard
operation emits a diff between the current and proposed JSON so the
operator can review changes before applying.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds + pre-check priority | Before any operation |
| **§ Mindset** | Metric math for derived calculations, OAM for cross-account, PutDashboard for IaC | Understanding the safety model |
| **§ Pre-flight** | Dashboard metadata gate — existing dashboards, OAM sinks, metric namespaces | Before executing any CLI |
| **§ Process** | Per-operation planning: create, update, metric-math, anomaly, share, cross-account, custom-widget, delete | When choosing which operation to run |
| **§ Output format** | Structured OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY template | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that break dashboards or hide data | Review before risky operations |
| **§ Pre-flight safety** | Capture pre-state, dashboard JSON diff, OAM link verification | Defense-in-depth |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `OPERATION_COMPLETED` | Dashboard operation finished and post-verification passed (PutDashboard returned 200, get-dashboard confirms JSON model applied, all widgets render with data) | Emit verification results, monitoring plan |
| `REVIEW_REQUIRED` | Operation plan is ready but requires human review before execution (cross-account OAM link affects monitoring scope, dashboard sharing exposes data externally, custom Lambda widget executes arbitrary code, anomaly detection band needs tuning) | Emit plan with specific review items, wait for operator approval |

**Priority order for pre-checks (apply in this sequence):**

1. **Dashboard JSON validity** — the dashboard body must be valid JSON
   with the required `widgets` array. Each widget must have `type`,
   `x`, `y`, `width`, `height`, and `properties`.
2. **Metric namespace existence** — verify the namespace
   (e.g., `AWS/RDS`, `AWS/Lambda`, `AWS/ECS`) has published data;
   empty namespaces produce empty dashboards.
3. **Metric dimensions** — verify dimension values (e.g., DBInstanceIdentifier)
   match live resources; stale dimension values produce broken widgets.
4. **OAM configuration** — for cross-account dashboards, verify the OAM
   sink exists in the monitoring account and the source account has a
   link attached.
5. **Lambda custom-widget permissions** — for Lambda-backed widgets,
   verify the Lambda function exists and has a resource-based policy
   allowing `cloudwatch.amazonaws.com` to invoke it.
6. **Anomaly detection model** — for anomaly detection bands, verify
   the model has sufficient training data (minimum 15 minutes of
   metrics; optimal with 2+ weeks).
7. **Sharing policy** — for dashboard sharing, verify the resource-based
   policy does not over-expose to `*` principal.

**Cost/time baselines (2026):**

- Dashboard creation (PutDashboard): <1 second API call. No per-dashboard
  charge (CloudWatch dashboards are free up to 3; $3/dashboard/month
  beyond 3).
- Custom widget Lambda: per-invocation cost (Lambda free tier covers
  most dashboard refresh patterns). Dashboard refreshes every 1-5 min.
- Cross-account via OAM: no additional charge; metrics flow through the
  existing OAM link (source account publishes, monitoring account
  queries).
- Anomaly detection: $0.015 per 1,000 anomalies detected. Training data
  ingestion is free.
- Metrics Insights queries: $0.005 per 1,000 queries (counted when used
  in a dashboard widget that refreshes).
- Dashboard API calls (GetDashboard, PutDashboard, ListDashboards):
  counted against CloudWatch API limits (50 transactions/second by
  default).

## Mindset

**One-line takeaway:** Metric math enables derived calculations beyond
raw CloudWatch metrics; cross-account dashboards use OAM shared
observability (not cross-account IAM roles); PutDashboard API enables
version-controlled dashboard IaC. Driven by three CloudWatch realities:

- **Metric math is the foundation of derived calculations.** Raw metrics
  (e.g., `Invocations`, `Errors`) tell you counts. Metric math lets you
  compute error rate (`Errors / Invocations`), throttle ratio
  (`Throttles / Invocations`), or p99 latency from percentile metrics.
  Without metric math, operators must export to a notebook or spreadsheet
  to compute derived values — a workflow that breaks real-time visibility.

- **Cross-account dashboards use OAM, not cross-account IAM role
  assumption.** CloudWatch Observability Access Manager (OAM) creates a
  sink in the monitoring account and links from source accounts. The
  monitoring account's dashboard queries span all linked source accounts
  via the `@Account` dimension. This is fundamentally simpler than the
  legacy approach of cross-account IAM roles per source account, and it
  scales to hundreds of accounts via AWS Organizations.

- **PutDashboard API enables version-controlled IaC for dashboards.**
  The dashboard body is a JSON string passed to `put-dashboard
  --dashboard-body <json>`. Store the JSON in Git, diff it in PRs, and
  deploy via CI/CD (CloudFormation, Terraform, or direct CLI). This is
  the only way to maintain dashboard consistency across environments
  (dev/staging/prod) and recover from accidental console edits.

## Pre-flight: dashboard metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `list-dashboards` paginates at 1,000/page (rarely an
issue). `list-metrics` paginates at 500/page — drain `--next-token` to
find all dimension combinations.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws cloudwatch list-dashboards` — check if the target dashboard name
   already exists (PutDashboard overwrites without confirmation).
2. `aws cloudwatch get-dashboard --dashboard-name <name>` — for
   update-dashboard, capture the current JSON body for diffing.
3. `aws cloudwatch list-metrics --namespace <ns>` — verify the
   namespace has published data and identify available dimensions.
4. `aws oam list-sinks` — for cross-account dashboards, verify an OAM
   sink exists in the monitoring (current) account.
5. `aws oam list-links` — verify source accounts are linked to the
   sink. Capture `LinkStatus: LINKED`.
6. `aws lambda get-function-configuration --function-name <fn>` — for
   custom widgets, verify the Lambda function exists and `State: Active`.
7. `aws lambda get-policy --function-name <fn>` — verify the resource-
   based policy allows `cloudwatch.amazonaws.com` to
   `lambda:InvokeFunction`.
8. `aws cloudwatch describe-alarms-for-metric --namespace <ns>
  --metric-name <metric>` — for alarm widgets, verify the alarm exists.

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Dashboard specification is
not valid JSON or is missing required fields — cannot plan.` and
`REMEDIATION: Provide a valid dashboard name, service type, and metric
configuration. Use aws cloudwatch get-dashboard --dashboard-name <name>
--output json as a template.`

| Dashboard attribute | Effect on operation |
|---|---|
| Dashboard name already exists | PutDashboard OVERWRITES the entire dashboard body. Capture the current body for diff/rollback before update. |
| Namespace has no published data | Dashboard widgets render empty. Verify metric publishing before or after creation. |
| Cross-account `@Account` dimension used | Requires OAM sink + source link in LINKED state. Without OAM, the dimension returns no data. |
| Anomaly detection model age < 15 min | Band may not render. Minimum 15 minutes of data needed; optimal with 2+ weeks. |
| Lambda custom widget without resource policy | Widget renders an error. Lambda must allow `cloudwatch.amazonaws.com` to invoke. |
| Dashboard body > 256 KB | PutDashboard rejects. CloudWatch limit is 256 KB per dashboard body (approximately 100-200 widgets depending on complexity). |
| Alarm referenced in widget does not exist | Widget renders "No alarms found." Verify alarm name matches an existing alarm. |
| Metrics Insights query syntax error | Widget renders an error. Verify SQL-like syntax: `SELECT avg(CPUUtilization) FROM AWS/RDS GROUP BY DBInstanceIdentifier`. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious CloudWatch dashboard behaviors

Step 0 expert knowledge — non-obvious dashboard behaviors (PutDashboard overwrite semantics, metric math, OAM, anomaly-band training data, custom-widget Lambda, sharing policy, variables, auto-refresh cost, Metrics Insights, @Account/@Region, service templates, 256 KB limit, escaped GetDashboard body, log widgets) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when planning any operation — each behavior changes the plan if ignored.

### Step 1: Pre-check gate — REVIEW_REQUIRED if any check needs human attention

Run ALL pre-checks for the chosen operation.

**For ALL operations:**
1. Dashboard name is valid (alphanumeric, hyphens, underscores; 1-255
   chars; no leading/trailing spaces).
2. Dashboard body is valid JSON with the `widgets` array.

**For create-dashboard (`put-dashboard`):**
3. Dashboard name does NOT already exist (or the operator confirms an
   overwrite).
4. Each metric namespace in the widgets has published data
   (`list-metrics --namespace <ns>`).
5. Each dimension value matches a live resource.
6. If anomaly detection is used: minimum 15 minutes of training data
   available.

**For update-dashboard (`put-dashboard` on existing):**
3. Current dashboard body captured via GetDashboard.
4. Diff between current and proposed body is presented for review.
5. No widgets are silently dropped (widget count should be >= current
   unless intentionally removing widgets).

**For add-metric-math:**
3. Referenced metrics (`id: m1`, `id: m2`) exist in the widget's
   `metrics` array.
4. Math expression is syntactically valid (CloudWatch metric math syntax).
5. The expression result is dimensionally meaningful (e.g.,
   `Errors / Invocations` is a rate; `Errors + Invocations` is probably
   not useful).

**For enable-cross-account:**
3. OAM sink exists in the monitoring account (`oam list-sinks`).
4. Source account is linked and `LinkStatus: LINKED` (`oam list-links`).
5. Widgets reference `@Account` dimension or use variables for account
   selection.
6. Verdict is REVIEW_REQUIRED (cross-account OAM link affects monitoring
   scope across accounts; the operator must confirm which accounts are
   in scope).

**For share-dashboard:**
3. Resource-based policy principal is a specific account ID or OU (not
   `*`).
4. Dashboard does not contain sensitive metric data that should not be
   shared externally.
5. Verdict is REVIEW_REQUIRED (sharing exposes dashboard data to the
   target principal).

**For add-custom-widget:**
3. Lambda function exists and `State: Active`.
4. Lambda resource-based policy allows `cloudwatch.amazonaws.com` to
   `lambda:InvokeFunction`.
5. Lambda code reviewed (custom widgets execute arbitrary code).
6. Verdict is REVIEW_REQUIRED (code execution surface).

### Step 2: OPERATION_COMPLETED or REVIEW_REQUIRED — emit operation plan

If all pre-checks pass and the operation is straightforward (create,
update, add-metric-math, add-anomaly, delete), emit `VERDICT:
OPERATION_COMPLETED` (for already-executed verification scenarios) or
the plan leading to completion. For operations requiring human review
(enable-cross-account, share-dashboard, add-custom-widget), emit
`VERDICT: REVIEW_REQUIRED` with the specific items to review.

The plan includes:
- The exact AWS CLI command with the full dashboard JSON body.
- The expected duration (PutDashboard: <1 second; widget rendering:
  first load takes 5-15 seconds for data to populate).
- The expected side-effects (dashboard visible in console, widgets
  render with data or empty, alarms show state).
- The CONFIRM gate prompt.
- The verification step (GetDashboard confirms body applied; console
  confirms widgets render).

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing API
  (`put-dashboard`, `delete-dashboards`, `put-dashboard-sharing-config`,
  `oam create-link`, `lambda add-permission`), emit:
  `CONFIRM: About to <operation> on <dashboard-name> in account <account>
  region <region>. This will <consequence>. Proceed? (yes/no)`. Do NOT
  execute until the operator confirms.
- Capture pre-state: `aws cloudwatch get-dashboard --dashboard-name <name>
  --output json > /tmp/<name>-pre-$(date +%s).json` (for updates).
- Execute the CLI. For PutDashboard, the API returns immediately with
  a 200 status or error messages.
- Verify: `aws cloudwatch get-dashboard --dashboard-name <name>` —
  confirm the body matches the input.

### Step 4: Post-verification — OPERATION_COMPLETED

After the operation finishes, run post-verification.

1. `get-dashboard --dashboard-name <name>` — confirm the JSON body
   matches the input.
2. Each widget references a valid metric with published data.
3. For cross-account: verify the `@Account` dimension returns data from
   linked source accounts.
4. For alarm widgets: verify the referenced alarms exist and show state.
5. For custom widgets: verify the Lambda function is invocable and
   returns valid HTML.
6. For anomaly detection: verify the band renders (may take 15 minutes
   for initial training data).

If ANY verification fails, emit `VERDICT: ERROR` with the failure
details — do not claim OPERATION_COMPLETED.

## Output format (per operation)

```text
OPERATION: <create-dashboard | update-dashboard | add-metric-math | add-anomaly-detection | share-dashboard | enable-cross-account | add-custom-widget | delete-dashboard>
VERDICT: OPERATION_COMPLETED | REVIEW_REQUIRED
TARGET: <dashboard-name> (widgets: <count>)
PRE_CHECKS:
  - [PASS] <check description>
  - [REVIEW] <check description> — <item requiring human attention>
STEPS:
  1. <CLI command with dashboard JSON>
  2. <verification command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <monitoring, caveats>
```

### Worked example — create RDS monitoring dashboard

```text
OPERATION: create-dashboard
VERDICT: OPERATION_COMPLETED
TARGET: prod-rds-overview (widgets: 8)
PRE_CHECKS:
  - [PASS] Dashboard name "prod-rds-overview" does not already exist
  - [PASS] Namespace AWS/RDS has published data (42 metrics found)
  - [PASS] DBInstanceIdentifier dimension values match live RDS instances
  - [PASS] Alarm rds-cpu-high exists (for alarm widget)
  - [PASS] Dashboard body size: 12 KB (< 256 KB limit)
STEPS:
  1. CONFIRM: About to create dashboard "prod-rds-overview" with 8
     widgets (CPU, memory, connections, storage, query throughput,
     replica lag, alarm, error logs) in account 111111111111 region
     us-east-1. Proceed? (yes/no)
  2. aws cloudwatch put-dashboard \
       --dashboard-name prod-rds-overview \
       --dashboard-body file://prod-rds-overview.json
  3. aws cloudwatch get-dashboard \
       --dashboard-name prod-rds-overview \
       --query 'DashboardName'
POST_VERIFY:
  - [PASS] get-dashboard returns "prod-rds-overview"
  - [PASS] Dashboard body matches input (8 widgets)
  - [PASS] Namespace AWS/RDS has data (widgets will render)
NOTES:
  - Dashboard includes metric math for connection utilization:
    DatabaseConnections / maxConnections * 100
  - Alarm widget shows rds-cpu-high (threshold 80% for 5 min)
  - Set up auto-refresh to 5 minutes in the console (cost-optimized)
  - Store the dashboard JSON in Git for version-controlled IaC:
    git add dashboards/prod-rds-overview.json
```

### Worked example — cross-account via OAM (REVIEW_REQUIRED)

Cross-account OAM worked example (REVIEW_REQUIRED verdict, sink/link pre-checks, Metrics Insights across @Account) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when planning an enable-cross-account operation.

### Worked example — add anomaly detection

Add-anomaly-detection worked example (ANOMALY_DETECTION_BAND, stdev tuning, alarm-on-band CLI) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when adding anomaly detection bands.

### Worked example — Metrics Insights dashboard

Metrics Insights dashboard worked example (top-10 EC2 by CPU query, cost math) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when building top-N Metrics Insights dashboards.

### Worked example — dashboard IaC via Git

Dashboard IaC via Git worked example (additive 8→10 widget diff, CI/CD deploy, envsubst parameterization) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when maintaining dashboards as version-controlled IaC.

## Anti-Patterns — NEVER

- NEVER PutDashboard without capturing the current body first. The API
  overwrites the ENTIRE dashboard. If the new body is incomplete, existing
  widgets are permanently lost. Always GetDashboard, modify, then
  PutDashboard the full body.

- NEVER use dashboard auto-refresh at 1 minute for dashboards with 50+
  widgets. Each refresh triggers GetMetricData calls for every widget.
  With Metrics Insights widgets ($0.005/1K queries), 50 widgets at 1-
  minute refresh generates 72,000 queries/day = $0.36/day per dashboard.
  Use 5-minute refresh for large dashboards.

- NEVER share a dashboard to the `*` principal. This exposes all
  dashboard data (metrics, logs, alarms, annotations) to any AWS account.
  Always scope to specific account IDs or organizational units.

- NEVER deploy a custom Lambda widget without reviewing the Lambda code.
  Custom widgets execute arbitrary code on every dashboard refresh. A
  malicious or buggy Lambda can exfiltrate data, make API calls, or
  crash the dashboard rendering. Review the code, scope the IAM role,
  and test the output format.

- NEVER assume the `@Account` dimension works without OAM. The
  dimension returns no data if there is no OAM sink + link configured.
  Verify `oam list-sinks` and `oam list-links` before using cross-account
  widgets.

- NEVER create an anomaly detection band without checking training data
  age. The band requires a minimum of 15 minutes of data; with less, it
  renders empty. Optimal accuracy requires 2+ weeks. Always verify the
  metric has history before adding the band.

- NEVER use hard-coded dimension values in dashboards meant for reuse.
  Use dashboard variables (`${DBInstance}`, `${FunctionName}`) to enable
  dynamic filtering. Hard-coded values force creating a new dashboard
  for each resource, defeating the purpose of templating.

- NEVER confuse `GetDashboard` output with the input format.
  `DashboardBody` in the response is an escaped JSON string, not a
  nested object. Parse it with `jq -r '.DashboardBody | fromjson'`
  before processing.

- NEVER create a Metrics Insights query without the `LIMIT` clause for
  top-N dashboards. Without `LIMIT`, the query returns all matching
  resources, which can be hundreds of rows and exceed the widget rendering
  capacity. Use `LIMIT 10` or `LIMIT 20`.

- NEVER skip the CONFIRM gate for `delete-dashboards`. Dashboard
  deletion is irreversible — there is no recycle bin. If the dashboard
  JSON is not stored in Git, the work is permanently lost.

- NEVER assume alarm widgets auto-update when the alarm is modified.
  The widget references the alarm by name; if the alarm is renamed or
  deleted, the widget shows "No alarms found." Update the widget
  reference when renaming alarms.

- NEVER exceed the 256 KB dashboard body limit without splitting into
  multiple dashboards. The PutDashboard API silently truncates oversized
  bodies, leading to missing widgets that are difficult to diagnose.

- NEVER use cross-account IAM role assumption for dashboards. This is
  the legacy approach (pre-OAM). It requires one role per source account,
  complex trust policies, and does not scale. Use OAM shared
  observability for all cross-account dashboard needs.

- NEVER deploy dashboards without testing in a non-production account
  first. Widget rendering, metric availability, and Lambda custom
  widgets behave differently across accounts and regions. Validate the
  dashboard JSON in a test account before promoting to production.

- NEVER assume metric math expressions handle missing data gracefully.
  If a referenced metric has no data points (e.g., `m2` is null), the
  expression (`m1 / m2`) returns null. Use `FILL(m2, 0)` to replace
  missing values with zero before computing.

## Pre-flight safety checks (run before any remediation CLI)

Pre-flight safety checks (CONFIRM gate, pre-state capture, OAM verification, Lambda policy verification, JSON validation, additive-update preference) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before executing any remediation CLI.

## Recent AWS features (2024-2026)

Recent AWS features (2024-2026) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when deciding between variables, OAM, Metrics Insights, custom widgets, sharing, or Application Signals auto-dashboards.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert knowledge and Recent AWS features (2024-2026) moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight safety checks moved from SKILL.md
- [references/worked-examples.md](references/worked-examples.md) — four secondary worked examples moved from SKILL.md (primary create-RDS example stays inline)
- [references/cross-account-oam-setup.md](references/cross-account-oam-setup.md) — OAM sink/link setup walkthrough
- [references/dashboard-json-templates.md](references/dashboard-json-templates.md) — service dashboard JSON templates

## Domain

AWS CloudOps / CloudWatch Dashboard Operations, Metric Visualization &
Observability.

## AWS documentation

- **Amazon CloudWatch User Guide — Using dashboards** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Dashboards.html
- **Create a dashboard** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/create_dashboard.html
- **CloudWatch metric math syntax** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/using-metric-math.html
- **Using metric anomalies** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html
- **Cross-account cross-region dashboards** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Cross-Account-Cross-Region-Dashboard.html
- **CloudWatch OAM** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-OAM.html
- **Custom widgets** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/add_custom_widget_dashboard.html
- **CloudWatch Metrics Insights** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/query_with_cloudwatch-metrics-insights.html
- **Dashboard sharing** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch-sharing-dashboards.html
- **CloudWatch API Reference — PutDashboard** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutDashboard.html
- **CloudWatch API Reference — GetDashboard** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_GetDashboard.html
