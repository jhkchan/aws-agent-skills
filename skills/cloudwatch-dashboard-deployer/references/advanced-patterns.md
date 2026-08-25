# Advanced Patterns (load on demand) — CloudWatch Dashboard Deployer

Step 0 expert-knowledge deep dives, edge cases, and recent AWS feature notes moved verbatim from SKILL.md. Loaded on demand.

---

## Step 0: Expert knowledge — non-obvious CloudWatch dashboard behaviors (moved from SKILL.md)

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
---

## Recent AWS features (2024-2026) (moved from SKILL.md)

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
