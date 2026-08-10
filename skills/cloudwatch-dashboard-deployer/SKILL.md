---
name: cloudwatch-dashboard-deployer
description: >-
  Provisions CloudWatch dashboards with widget layouts, metric
  selections, and sharing models. Covers dashboard JSON (widgets,
  layout), metric widgets (namespace/metric/dimensions/statistics),
  log insights widgets (query syntax), alarm widgets, text widgets,
  metric math expressions, custom metrics (CloudWatch agent,
  PutMetricData, EMF), cross-account shared dashboards, snapshot
  sharing, dashboard variables ($INSTANCE_ID), SLO/operational/
  executive dashboards, Metric Explorer, and Application Signals
  auto-discovery. Runs pre-checks (namespace availability, metric
  publishing, IAM, cross-account role), emits put-dashboard CLI
  behind a CONFIRM gate, and verifies widget rendering. Emits
  READY_TO_DEPLOY | PREREQUISITES_MISSING. Use when creating
  operational, SLO, executive, cross-account, log insights, or
  metric math dashboards.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline plan classification. Live-account
  operations use aws cloudwatch put-dashboard, get-dashboard,
  list-dashboards, delete-dashboards, get-metric-statistics (AWS CLI v2,
  SSO or key-based credentials).
keywords:
  - CloudWatch
  - dashboards
  - put-dashboard
  - metric widgets
  - log insights widgets
  - alarm widgets
  - text widgets
  - metric math
  - custom metrics
  - CloudWatch agent
  - PutMetricData
  - embedded metrics format
  - cross-account dashboards
  - snapshot sharing
  - dashboard variables
  - SLO dashboards
  - operational dashboards
  - executive dashboards
  - metric explorer
  - Application Signals
  - auto-discovery
tags: [cloudwatch, monitoring, dashboards, observability, deploy, metric-widgets, cross-account]
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Management
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - cloudwatch
    - monitoring
    - dashboards
    - observability
    - deploy
    - metric-widgets
    - cross-account
  dependencies:
    - aws-orchestrator
  keywords:
    - CloudWatch
    - dashboards
    - metric widgets
    - log insights
    - metric math
    - cross-account
  when_to_use: >-
    Creating CloudWatch dashboards (operational, SLO, executive, cross-
    account), building metric widgets with correct namespace/dimensions/
    statistics, adding log insights widgets with query syntax, using metric
    math to combine multiple metrics, configuring dashboard variables for
    dynamic filtering, deploying shared cross-account dashboards, setting
    up snapshot sharing, leveraging Application Signals auto-discovery, or
    auditing dashboard widget correctness.
  activation_triggers:
    - "create CloudWatch dashboard"
    - "provision dashboard"
    - "metric widget"
    - "log insights widget"
    - "alarm widget"
    - "text widget"
    - "metric math dashboard"
    - "custom metrics dashboard"
    - "cross-account dashboard"
    - "snapshot sharing dashboard"
    - "dashboard variables"
    - "SLO dashboard"
    - "operational dashboard"
    - "executive dashboard"
    - "metric explorer"
    - "Application Signals dashboard"
  invocation_schema: >-
    Input: either (a) a dashboard deployment intent (create, update, share)
    with target dashboard name, widget specifications, metric namespace/
    dimensions, and sharing model, OR (b) a dashboard name for live-account
    update or validation. Output: deterministic DASHBOARD/VERDICT/PRE_CHECKS/
    STEPS/POST_VERIFY block per operation, where VERDICT is one of
    READY_TO_DEPLOY, PREREQUISITES_MISSING.
---

# CloudWatch Dashboard Deployer

## What this skill does

Provisions CloudWatch dashboards with correct widget layouts, metric
selections, and sharing models. Runs deterministic pre-checks before any
state-changing CLI (do the namespaces exist? are dimensions correct?
is the cross-account sharing role configured? does the IAM principal hold
`cloudwatch:PutDashboard`?), emits the exact `put-dashboard` CLI behind a
CONFIRM gate, and verifies widget rendering after apply. Every dashboard
plan surfaces the widget count cap, the 24-hour auto-refresh limit, and the
metric-math expression limits.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds + pre-check priority order + widget types | Before any operation |
| **§ Mindset** | Why widget layout matters, dashboard JSON structure, sharing limits | Understanding the deployment model |
| **§ Pre-flight** | Metric/metadata gate — namespace, dimensions, sharing role | Before executing any CLI |
| **§ Process** | Per-operation planning: create, update, share, validate | When choosing which operation |
| **§ Common patterns** | Operational / SLO / executive / cross-account boilerplate | Boilerplate lookup |
| **§ Output format** | Structured output template with VERDICT, COMMANDS, POST_VERIFY | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that cause empty/broken dashboards | Review before deploy |
| **§ Pre-flight safety** | Additional checks before any provisioning CLI | Defense-in-depth |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `PREREQUISITES_MISSING` | One or more pre-checks failed (namespace not publishing, dimensions wrong, cross-account role absent, IAM permission missing, dashboard JSON invalid) | List failures, do NOT execute |
| `READY_TO_DEPLOY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence with dashboard JSON body, wait for operator yes |

**Priority order for pre-checks (apply in this sequence, all must pass for
READY_TO_DEPLOY):**

1. **Dashboard JSON structure** — valid DashboardBody with widgets array,
   each widget has type, properties, position (x, y, width, height).
2. **Metric namespace + dimensions** — for each metric widget, the namespace
   exists and dimensions match the metric's native structure.
3. **Metric publishing** — `get-metric-statistics` returns non-empty
   datapoints for the metrics referenced in each widget.
4. **Statistic / period alignment** — Statistic matches metric semantics
   (Sum for counts, Average for utilization); Period >= native publishing
   interval.
5. **Log group existence** — for log insights widgets, the referenced log
   groups exist and are receiving log events.
6. **Alarm existence** — for alarm widgets, the referenced alarm names
   resolve to existing alarms.
7. **Cross-account sharing role** — for cross-account dashboards, the
   CloudWatch-CrossAccountSharingRole is configured in each source account.
8. **IAM permissions** — the operator principal holds
   `cloudwatch:PutDashboard` and (for sharing) `iam:PassRole`.
9. **Widget count** — total widgets <= 100 per dashboard (hard cap).
10. **Dashboard variables** — referenced variables ($INSTANCE_ID, etc.)
    match available metric dimensions.

**Dashboard limits (2026):**

- Max widgets per dashboard: 100.
- Max dashboard name length: 255 chars.
- DashboardBody max size: 256 KB.
- Widget grid: 24 columns wide, unlimited rows.
- Metric expressions per widget: up to 100 metrics/expressions.
- Auto-refresh intervals: 1m, 2m, 5m, 10m, 15m (max 15m).
- Cross-account dashboards: up to 200 source accounts per sharing account.

## Mindset

**One-line takeaway:** a dashboard is only as good as its widgets are
correct. A widget with the wrong namespace or dimensions renders blank
forever — no error, no alert, just an empty chart that erodes operator
trust. Driven by three CloudWatch realities:

- **PutDashboard overwrites atomically.** Dashboard names are unique
  within account+region. `put-dashboard` replaces the ENTIRE
  DashboardBody — there is no partial update. A deployment that adds one
  widget but omits the existing widgets silently deletes the old layout.
  Always snapshot via `get-dashboard` first.

- **Metric widgets silently render empty.** If the namespace, metric name,
  or dimensions are wrong, the widget shows no error — just a flat empty
  chart. Operators assume the metric has no data, when in fact the widget
  config is incorrect. The only way to verify a widget is correct is
  `get-metric-statistics` on the exact same namespace/metric/dimensions.

- **Cross-account sharing requires a role in EACH source account.** The
  sharing (monitoring) account can see metrics from source accounts only
  if each source account has the `CloudWatch-CrossAccountSharingRole`
  trust policy granting the sharing account access. Missing the role in
  one source account means that account's metrics silently render empty
  on the shared dashboard.

## Pre-flight: dashboard metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `list-dashboards` returns at most 1000 dashboards per
page (via `--page-size`). Use `--starting-token` to drain.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws cloudwatch get-dashboard --dashboard-name <name>` — confirm the
   dashboard exists (or doesn't, for create ops). Capture the full
   DashboardBody for snapshot/diff.
2. `aws cloudwatch get-metric-statistics --namespace <ns> --metric-name
   <mn> --dimensions <dims> --start-time <iso> --end-time <iso> --period
   <p> --statistics <stat>` — for each metric widget, confirm the metric
   is publishing and observe the typical range.
3. `aws logs describe-log-groups --log-group-name-prefix <prefix>` — for
   log insights widgets, verify the referenced log groups exist.
4. `aws cloudwatch describe-alarms --alarm-names <name>` — for alarm
   widgets, verify the referenced alarms exist.
5. `aws iam get-role --role-name CloudWatch-CrossAccountSharingRole` —
   for cross-account dashboards, verify the sharing role exists in each
   source account.
6. `aws cloudwatch list-dashboards` — check for naming conflicts.

**Malformed input:** if the dashboard JSON is invalid or missing required
fields, emit `VERDICT: PREREQUISITES_MISSING` with `REASON: Dashboard
JSON is not valid or is missing required widget fields — cannot plan.`
and `REMEDIATION: Validate the DashboardBody structure at
https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/cloudwatch-dashboards.html.`

| Attribute | Effect on operation |
|---|---|
| Dashboard name already exists | Update operation. Must snapshot existing body first; put-dashboard overwrites. |
| Metric widget with 0 datapoints | Widget will render empty. Surface as PREREQUISITES_MISSING: verify namespace/dimensions. |
| Log insights widget referencing non-existent log group | Widget will error at render time. PREREQUISITES_MISSING. |
| Alarm widget referencing non-existent alarm | Widget renders "Alarm not found." PREREQUISITES_MISSING. |
| Cross-account dashboard without sharing role | Source account metrics render empty. PREREQUISITES_MISSING. |
| > 100 widgets in DashboardBody | PutDashboard API rejects. PREREQUISITES_MISSING. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious CloudWatch dashboard behaviors

These behaviors are easy to misjudge without operational dashboard
experience. Each changes a plan if ignored:

- **PutDashboard replaces the ENTIRE DashboardBody.** There is no
  "add widget" API. To add a widget to an existing dashboard, you must
  fetch the current body, parse the JSON, insert the new widget, and
  PUT the entire modified body. Omitting existing widgets deletes them.

- **Widget positions use a 24-column grid.** x ranges 0-23, width 1-24.
  Overlapping widgets are accepted by the API but render incorrectly.
  The y-axis is unbounded — widgets stack vertically based on y + height.

- **Metric widget period defaults to auto.** If not specified, CloudWatch
  auto-selects the period based on the dashboard time range (1m for
  short ranges, 5m/1h for long ranges). For consistent dashboards, set
  period explicitly in the widget properties.

- **Log insights widgets require a literal query string.** The query
  syntax uses CloudWatch Logs Insights commands: `fields`, `filter`,
  `stats`, `sort`, `limit`. The query runs at dashboard render time —
  expensive queries on large log groups slow dashboard load.

- **Metric math expressions use a specific ID convention.** Each metric
  in a metric math widget has an ID (e.g., `m1`, `m2`), and expressions
  reference these IDs (e.g., `e1: m1 / m2`). The expression ID must
  start with `e` and the metric ID must start with `m`.

- **Cross-account dashboards require the AccountId field in each
  metric.** Without `AccountId` in the metric object, the dashboard
  queries the current (sharing) account only. The wrong AccountId
  silently monitors the wrong account.

- **Dashboard variables use ${VARIABLE_NAME} syntax.** Variables are
  resolved at render time from the URL query string or the dashboard's
  variable configuration. `$INSTANCE_ID` in a dimension value is
  replaced when the operator selects a specific instance from the
  dropdown.

- **Shared dashboards are read-only for viewers.** Cross-account shared
  dashboards can be viewed by principals in the sharing account, but
  only the dashboard owner account can modify the dashboard body.

- **Snapshot sharing creates a point-in-time copy.** A dashboard
  snapshot is a static image of the dashboard at a specific time — it
  does not auto-update. Snapshots are shareable via S3 presigned URLs.

- **Application Signals auto-discovers services.** When enabled,
  CloudWatch Application Signals automatically discovers EKS/ECS/EC2
  services and creates default SLOs. Dashboard widgets can reference
  these auto-discovered metrics via the `AWS/ApplicationSignals`
  namespace.

- **Metric Explorer is interactive, not a dashboard widget.** The
  CloudWatch Metric Explorer is a separate UI tool for ad-hoc
  cross-account metric exploration. It cannot be embedded as a
  dashboard widget — but saved Metric Explorer views can be linked
  from text widgets.

- **Text widgets support Markdown.** The `markdown` field in a text
  widget supports a subset of Markdown (headers, bold, links, lists).
  Use text widgets for runbook links, dashboard descriptions, and
  separator headers between sections.

- **Dashboard auto-refresh maxes at 15 minutes.** The `start` and `end`
  fields support relative time (e.g., `-PT1H` for last 1 hour).
  Operators can set auto-refresh from 1m to 15m; beyond that, the
  dashboard goes stale.

- **Custom metrics from PutMetricData cost extra.** Each custom metric
  costs $0.30/month (first 10,000 free). Dashboards referencing
  thousands of custom metrics (e.g., per-instance memory) can incur
  significant metric costs. Consider metric math to aggregate before
  plotting.

- **Embedded Metrics Format (EMF) is the cheapest custom metric path.**
  EMF payloads are logged to CloudWatch Logs (one log event) and
  auto-extracted as metrics — no separate PutMetricData API call.
  Ideal for high-cardinality application metrics (request latency per
  endpoint).

### Step 1: Pre-check gate — PREREQUISITES_MISSING if any check fails

Run ALL of the following pre-checks. If ANY fails, the verdict is
PREREQUISITES_MISSING with the failed checks enumerated in PRE_CHECKS.
Do NOT execute.

**For ALL operations:**
1. The DashboardBody is valid JSON with the required `widgets` array.
2. Dashboard name is <= 255 chars, matches `^[a-zA-Z0-9-_./]+$`.
3. Total widget count <= 100.
4. No widget positions overlap (x+width <= 24, no y-axis collisions).
5. The IAM principal holds `cloudwatch:PutDashboard`.

**For create/update dashboard (`put-dashboard`):**
6. For each **metric widget**: namespace + metric name + dimensions
   return datapoints via `get-metric-statistics` within the last hour.
7. For each **metric widget**: Period >= metric native publishing
   interval; Statistic matches metric semantics.
8. For each **log insights widget**: referenced log groups exist and
   are receiving events (`aws logs describe-log-groups`).
9. For each **alarm widget**: referenced alarm names resolve via
   `describe-alarms`.
10. For each **metric math expression**: expression syntax is valid
    (m-IDs reference defined metrics, e-IDs use valid math operators).
11. For each **dashboard variable**: the variable maps to a valid
    dimension name in the referenced metric namespace.

**For cross-account shared dashboard:**
12. `CloudWatch-CrossAccountSharingRole` exists in each source account.
13. The sharing account has `sts:AssumeRole` permission on each source
    account's sharing role.
14. Each metric widget includes the correct `AccountId` field for the
    source account.

**For snapshot sharing:**
12. The S3 bucket for snapshot storage exists and the operator has
    `s3:PutObject` permission.
13. The bucket policy allows presigned URL generation for the intended
    recipients.

### Step 2: READY_TO_DEPLOY — emit deployment plan

If all pre-checks pass, emit `VERDICT: READY_TO_DEPLOY` with the exact
CLI sequence and the CONFIRM gate. The plan includes:

- The exact `aws cloudwatch put-dashboard` CLI with the DashboardBody
  as a JSON string (or file reference).
- The expected widget count and layout summary.
- The expected sharing behavior (single-account vs cross-account).
- The CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`put-dashboard`, `delete-dashboards`), emit:
  `CONFIRM: About to <operation> dashboard <name> in account <account>
  region <region>. This will <consequence>. Proceed? (yes/no)`. Do NOT
  execute until the operator confirms.
- Snapshot the current dashboard config before modification:
  `aws cloudwatch get-dashboard --dashboard-name <name> --output json >
  /tmp/<name>-backup-$(date +%s).json`.
- Execute the CLI with the full DashboardBody.

### Step 4: Post-verification

After the operation finishes, run post-verification:

1. `get-dashboard --dashboard-name <name>` returns the expected
   DashboardBody with all widgets present.
2. For each metric widget: the metric is rendering (no empty charts) —
   verify by checking `get-metric-statistics` for the widget's
   namespace/metric/dimensions.
3. For cross-account dashboards: verify at least one source account's
   metrics render by spot-checking a metric widget with `AccountId`
   set.
4. Dashboard loads within 30 seconds (no slow log insights queries
   blocking render).

## Common dashboard patterns (boilerplate)

### Operational dashboard — EC2 fleet (metric widgets)

```bash
aws cloudwatch put-dashboard \
  --dashboard-name "prod-ec2-ops" \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "x": 0, "y": 0, "width": 12, "height": 6,
        "properties": {
          "metrics": [
            ["AWS/EC2", "CPUUtilization", "InstanceId", "${INSTANCE_ID}", {"label": "CPU %"}]
          ],
          "period": 300,
          "stat": "Average",
          "region": "us-east-1",
          "title": "CPU Utilization",
          "view": "timeSeries",
          "stacked": false,
          "liveData": true
        }
      },
      {
        "type": "metric",
        "x": 12, "y": 0, "width": 12, "height": 6,
        "properties": {
          "metrics": [
            ["CWAgent", "mem_used_percent", "InstanceId", "${INSTANCE_ID}", {"label": "Memory %"}]
          ],
          "period": 300,
          "stat": "Average",
          "title": "Memory Utilization (CWAgent)",
          "view": "timeSeries"
        }
      },
      {
        "type": "metric",
        "x": 0, "y": 6, "width": 24, "height": 3,
        "properties": {
          "metrics": [
            ["AWS/EC2", "NetworkIn", "InstanceId", "${INSTANCE_ID}", {"label": "Network In (MB)", "id": "m1"}],
            ["AWS/EC2", "NetworkOut", "InstanceId", "${INSTANCE_ID}", {"label": "Network Out (MB)", "id": "m2"}],
            [{"expression": "m1/1048576", "label": "In MB/s", "id": "e1"}],
            [{"expression": "m2/1048576", "label": "Out MB/s", "id": "e2"}]
          ],
          "period": 300,
          "stat": "Sum",
          "title": "Network Traffic",
          "view": "timeSeries"
        }
      }
    ]
  }'
```

### Log insights widget — error analysis

```json
{
  "type": "log",
  "x": 0, "y": 0, "width": 24, "height": 6,
  "properties": {
    "query": "SOURCE '/aws/lambda/prod-checkout' | fields @timestamp, @message\n| filter @message like /ERROR/\n| stats count() by bin(5m)\n| sort @timestamp desc\n| limit 100",
    "region": "us-east-1",
    "stacked": false,
    "title": "Lambda Errors (5-min buckets)",
    "view": "timeSeries"
  }
}
```

### Alarm widget

```json
{
  "type": "alarm",
  "x": 0, "y": 0, "width": 12, "height": 3,
  "properties": {
    "title": "Production Alarms",
    "alarms": [
      "arn:aws:cloudwatch:us-east-1:111111111111:alarm:ec2-cpu-high-prod-web-1",
      "arn:aws:cloudwatch:us-east-1:111111111111:alarm:lambda-errors-high-prod-checkout"
    ]
  }
}
```

### Text widget (Markdown runbook link)

```json
{
  "type": "text",
  "x": 0, "y": 0, "width": 24, "height": 2,
  "properties": {
    "markdown": "# Production Operations Dashboard\n**Runbook**: [Incident Response](https://runbooks.example.com/incident)\n**On-call rotation**: PagerDuty schedule `prod-oncall`\n**Escalation**: Slack `#prod-incidents`"
  }
}
```

### Metric math — error rate (errors / total requests)

```json
{
  "type": "metric",
  "x": 0, "y": 0, "width": 12, "height": 6,
  "properties": {
    "metrics": [
      ["AWS/ApplicationELB", "HTTPCode_ELB_5XX_Count", "LoadBalancer", "app/prod-alb/1234567890", {"id": "m1"}],
      ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", "app/prod-alb/1234567890", {"id": "m2"}],
      [{"expression": "m1/m2*100", "label": "Error Rate %", "id": "e1"}]
    ],
    "period": 60,
    "stat": "Sum",
    "title": "ALB 5xx Error Rate (%)",
    "view": "timeSeries",
    "yAxis": {"left": {"min": 0, "max": 10}}
  }
}
```

### SLO dashboard — burn rate (Application Signals)

```json
{
  "type": "metric",
  "x": 0, "y": 0, "width": 24, "height": 6,
  "properties": {
    "metrics": [
      ["AWS/ApplicationSignals", "ConsumedRAT", "ServiceName", "checkout-service", "SLO", "checkout-availability-slo", {"id": "m1"}],
      ["AWS/ApplicationSignals", "RequestedRAT", "ServiceName", "checkout-service", "SLO", "checkout-availability-slo", {"id": "m2"}],
      [{"expression": "m1/m2", "label": "Burn Rate", "id": "e1"}]
    ],
    "period": 300,
    "stat": "Sum",
    "title": "SLO Burn Rate — Checkout Availability",
    "view": "timeSeries",
    "annotations": {"horizontal": [{"label": "Fast burn (2h)", "value": 14.4}, {"label": "Slow burn (6h)", "value": 6}]}
  }
}
```

### Cross-account dashboard (shared)

```json
{
  "type": "metric",
  "x": 0, "y": 0, "width": 12, "height": 6,
  "properties": {
    "metrics": [
      ["AWS/EC2", "CPUUtilization", "InstanceId", "i-0123456789abcdef0", {"AccountId": "222222222222", "label": "Dev Account CPU"}],
      ["AWS/EC2", "CPUUtilization", "InstanceId", "i-0abcdef1234567890", {"AccountId": "333333333333", "label": "Staging Account CPU"}]
    ],
    "period": 300,
    "stat": "Average",
    "region": "us-east-1",
    "title": "Cross-Account CPU Comparison",
    "view": "timeSeries"
  }
}
```

### Executive dashboard — KPI summary (single-value widgets)

```json
{
  "type": "metric",
  "x": 0, "y": 0, "width": 6, "height": 3,
  "properties": {
    "metrics": [["AWS/ApplicationELB", "RequestCount", "LoadBalancer", "app/prod-alb/1234567890"]],
    "period": 3600,
    "stat": "Sum",
    "title": "Total Requests (1h)",
    "view": "singleValue",
    "setPeriodToTimeRange": true
  }
}
```

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no conversational
opening:

```text
DASHBOARD: <dashboard-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
TARGET: <dashboard-name>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> dashboard <name> in account <account> region <region>. This will <consequence>. Proceed? (yes/no)
  2. <exact CLI command with DashboardBody — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
WIDGETS: <count> widgets (<metric>, <log>, <alarm>, <text>)
SHARING: <single-account | cross-account:N-source-accounts | snapshot>
NOTES: <widget layout rationale, sharing caveats, variable configuration>
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze…" or "I'll create…" — the VERDICT
  block is the FIRST line, always. No conversational preamble.
- NEVER use lowercase verdict values — emit `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING` (not `ready`, `prerequisites`).
- NEVER omit PRE_CHECKS — every pre-check run must appear with `[PASS]`
  or `[FAIL]` and a specific reason for each failure. An empty
  PRE_CHECKS block is non-compliant.
- NEVER emit a metric widget with placeholder dimensions (e.g.,
  `"<instance-id>"`) in a READY_TO_DEPLOY plan — every field must be
  populated with actual values or dashboard variables from the input.
- NEVER omit the CONFIRM gate as the first STEPS entry for any
  state-changing operation.
- NEVER claim success without verifying that each metric widget's
  namespace/metric/dimensions actually return datapoints — empty widgets
  are the #1 dashboard failure mode.
- NEVER put-dashboard without snapshotting the existing body first —
  PutDashboard replaces the entire DashboardBody with no diff or rollback.
- NEVER reference a dashboard variable without confirming it maps to a
  valid dimension in the referenced metric namespace.

### Perfect example output

```text
DASHBOARD: prod-ec2-ops
VERDICT: READY_TO_DEPLOY
TARGET: prod-ec2-ops
PRE_CHECKS:
  - [PASS] DashboardBody valid JSON, 3 widgets, 0 overlaps
  - [PASS] Widget 1: AWS/EC2 CPUUtilization InstanceId=${INSTANCE_ID} returns datapoints
  - [PASS] Widget 2: CWAgent mem_used_percent InstanceId=${INSTANCE_ID} returns datapoints
  - [PASS] Widget 3: metric math m1/1048576 valid (NetworkIn exists)
  - [PASS] Dashboard variable INSTANCE_ID maps to valid dimension on AWS/EC2
  - [PASS] IAM principal holds cloudwatch:PutDashboard
  - [PASS] 3 widgets <= 100 cap
STEPS:
  1. CONFIRM: About to put-dashboard prod-ec2-ops in account 111111111111 region us-east-1. This will CREATE a new dashboard with 3 metric widgets (CPU, Memory, Network). Proceed? (yes/no)
  2. aws cloudwatch put-dashboard --dashboard-name prod-ec2-ops --dashboard-body '{"widgets":[...]}'
POST_VERIFY:
  - (pending execution)
  - get-dashboard returns 3 widgets with correct positions
  - Each metric widget renders non-empty within the dashboard time range
WIDGETS: 3 widgets (3 metric, 0 log, 0 alarm, 0 text)
SHARING: single-account
NOTES:
  - Dashboard variable INSTANCE_ID configured for dynamic instance selection.
  - CWAgent widget requires CloudWatch agent installed on target instances —
    verify agent status if memory chart renders empty.
  - No auto-refresh configured — set to 5m for operational use via the
    console or dashboard update.
```

## Anti-Patterns — NEVER do these things

- NEVER PutDashboard without snapshotting the existing body first.
  `get-dashboard --output json > /tmp/<name>-backup-$(date +%s).json`.
  PutDashboard replaces the entire body with no version history.

- NEVER create a metric widget without verifying via
  `get-metric-statistics` that the metric is publishing. A wrong
  namespace or dimension produces an empty chart that silently erodes
  operator trust — no error is surfaced.

- NEVER use Period < metric native publishing interval in a widget.
  A 5-minute metric (basic monitoring) with Period=60 produces mostly
  empty windows. Match the period to the metric's resolution.

- NEVER hardcode instance IDs in production dashboards. Use dashboard
  variables ($INSTANCE_ID) so the dashboard adapts to fleet changes.
  Hardcoded IDs break when instances are replaced.

- NEVER build a cross-account dashboard without verifying the
  `CloudWatch-CrossAccountSharingRole` exists in each source account.
  Missing the role causes source account metrics to silently render
  empty — the dashboard appears configured but shows no data.

- NEVER create a log insights widget with an unbounded query (no
  `limit` clause, no time bucketing). Expensive queries on large log
  groups can take minutes to render and cause dashboard timeouts.

- NEVER exceed 100 widgets per dashboard. The PutDashboard API silently
  rejects the 101st widget. Split into multiple dashboards or use a
  dashboard link in a text widget.

- NEVER mix regions in widget properties without setting the `region`
  field explicitly in each widget. A dashboard in us-east-1 with a
  widget missing the `region` field queries us-east-1 — even if the
  operator intended a multi-region view.

- NEVER use `stat: "Sum"` for utilization metrics (CPU, memory, disk).
  Sum aggregates across all datapoints in the period, producing
  misleadingly high values for high-resolution metrics. Use `Average`
  for utilization, `Sum` for counts/volumes.

- NEVER auto-execute PutDashboard without the CONFIRM gate. PutDashboard
  overwrites the entire dashboard config with no version history and no
  rollback path. Always snapshot first.

- NEVER create a dashboard with overlapping widget positions. The API
  accepts overlapping positions but the rendering is unpredictable —
  widgets may occlude each other or render in the wrong z-order.

- NEVER forget the `view` field in widget properties. Without `view`
  (e.g., `timeSeries`, `singleValue`, `bar`, `pie`, `gauge`), the
  widget defaults to `timeSeries` which may not match the intended
  visualization for KPI/executive dashboards.

- NEVER use Embedded Metrics Format (EMF) without testing the metric
  extraction. EMF payloads with malformed JSON or missing metric
  directives silently produce no metrics — verify via
  `get-metric-statistics` on the expected namespace after deploying
  the EMF log ingestion.

## Pre-flight safety checks (run before any provisioning CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`put-dashboard`, `delete-dashboards`), the operator MUST emit:
  `CONFIRM: About to <action> dashboard <name> in account <account>
  region <region>. This affects <consequence>. Proceed? (yes/no)`. Do
  NOT execute the CLI command until the operator confirms.

- **PutDashboard overwrites the entire dashboard body.** Always snapshot
  before modification:
  `aws cloudwatch get-dashboard --dashboard-name <name> --output json >
  /tmp/<name>-backup-$(date +%s).json`.

- For cross-account dashboards, verify the sharing role exists in EACH
  source account before deploying. A missing role is the #1 cause of
  empty cross-account widgets.

- For dashboards with log insights widgets, test the query in the
  CloudWatch Logs Insights console first to estimate render time.
  Queries on large log groups (>100 GB ingested) can take 30+ seconds
  and cause dashboard load timeouts.

- Prefer additive changes (add widgets, add dashboard variables) over
  destructive changes (replace entire dashboard body) — additive
  changes are reversible and do not risk removing existing operational
  views.

- For dashboards shared via snapshot, ensure the S3 bucket lifecycle
  policy is configured — snapshots accumulate and incur storage costs
  if not cleaned up.

## Expert heuristic: empty widgets vs no data

An empty widget does NOT mean "the metric has no data." It means **the
widget's metric query returned zero datapoints for the dashboard's time
range** — which can be caused by either a real data gap or (more commonly)
a widget configuration error.

**Diagnostic decision tree:**

```
Empty metric widget
   ├─ Is the namespace correct? (case-sensitive)
   │    ├─ NO → Fix namespace (AWS/EC2 not aws/ec2)
   │    └─ YES → Check dimensions
   │              ├─ Are dimension names/values correct?
   │              ├─ If dashboard variable: does the variable resolve?
   │              └─ If cross-account: is AccountId set correctly?
   │
   └─ Confirm via get-metric-statistics:
        aws cloudwatch get-metric-statistics \
          --namespace <widget-namespace> \
          --metric-name <widget-metric> \
          --dimensions <widget-dimensions> \
          --start-time <now-1h> --end-time <now> \
          --period <widget-period> --statistics <widget-stat>
        If datapoints > 0 → widget config is wrong somewhere
        If datapoints = 0 → metric is genuinely not publishing
```

**Per-widget-type empty render causes:**

| Widget type | What to check when widget is empty |
|---|---|
| Metric | Namespace case? Dimensions match? Period >= native resolution? Stat matches? Cross-account AccountId correct? |
| Log insights | Log group exists? Query syntax valid? Log group receiving events? Time range matches? |
| Alarm | Alarm ARN/name correct? Alarm still exists (not deleted)? |
| Text | Markdown syntax valid? (rarely empty — usually a rendering issue) |

**Fix — verify the widget config against get-metric-statistics:**
- If `get-metric-statistics` returns datapoints but the widget is empty:
  the widget config is wrong. Diff the widget's namespace/metric/
  dimensions against the working CLI command.
- If `get-metric-statistics` also returns nothing: the metric source
  is not publishing. Check the CloudWatch agent, the PutMetricData
  calls, or the EMF log ingestion.

ALWAYS test a dashboard's metric widgets by rendering it in the console
after PutDashboard — the API confirms structure but not visual correctness.

## Recent AWS features (2024-2026)

- **CloudWatch Metric Explorer (2024-2025):** interactive cross-account,
  cross-region metric exploration without pre-configuring dashboards.
  Use to discover the right metric/dimension set before building a
  dashboard. Saved Metric Explorer views can be linked from dashboard
  text widgets.
- **CloudWatch Application Signals (2024-2025):** auto-discovered
  services and SLOs from CloudWatch Agent on EC2/ECS/EKS. Dashboard
  widgets can reference `AWS/ApplicationSignals` metrics for burn-rate,
  latency, and availability monitoring without manual instrumentation.
- **Cross-account dashboard sharing improvements (2024):** streamlined
  role-based sharing model. Up to 200 source accounts per sharing
  account. Shared dashboards are now editable from the sharing account
  (previously read-only).
- **Dashboard variables (2024-2025):** dynamic dashboard parameters
  ($INSTANCE_ID, $AWS_REGION) that operators select from dropdowns.
  Enables one dashboard to serve an entire fleet without duplication.
- **Embedded Metrics Format v2 (2024):** enhanced EMF with multi-value
  metrics and dimension filtering. Reduces PutMetricData API costs for
  high-cardinality application metrics.
- **CloudWatch snapshot sharing via S3 (2025):** point-in-time dashboard
  snapshots shareable via presigned S3 URLs. Useful for executive
  reporting and compliance evidence without granting live dashboard
  access.
- **Application Signals auto-remediation hooks (2025):** when Application
  Signals detects an SLO breach, it can trigger a Lambda or SSM
  Automation runbook. Dashboard widgets surface the remediation status.

## AWS documentation

- **Amazon CloudWatch User Guide** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html
- **CloudWatch Dashboards** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Dashboards.html
- **Dashboard JSON Structure** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch-dashboards.html
- **Cross-Account Cross-Region Dashboards** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Cross-Account-Cross-Region-Dashboard.html
- **CloudWatch Logs Insights** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html
- **Metric Math** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/using-metric-math.html
- **Embedded Metrics Format** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format.html
- **CloudWatch Application Signals** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals.html

## Domain

AWS CloudOps / CloudWatch Dashboard Provisioning & Observability Visualization.
