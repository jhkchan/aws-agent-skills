# Advanced Patterns (load on demand) — CloudWatch Dashboards Operator

Step 0 expert-knowledge deep dives, edge cases, and recent AWS feature notes moved verbatim from SKILL.md. Loaded on demand.

---

## Step 0: Expert knowledge — non-obvious CloudWatch dashboard behaviors (moved from SKILL.md)


These behaviors are easy to misjudge without operational CloudWatch
experience. Each changes a plan if ignored:

- **PutDashboard overwrites the ENTIRE dashboard body.** There is no
  partial update. If the dashboard has 10 widgets and you PutDashboard
  with 3 widgets, the result is 3 widgets — the other 7 are gone. Always
  capture the current body via GetDashboard, modify it, then PutDashboard
  the full body. This is why version-controlled IaC is critical: the Git
  diff shows exactly what changed.

- **Metric math enables derived calculations.** The `metrics` array in a
  widget supports math expressions: `{"expression": "m1 / m2 * 100",
  "label": "Error Rate (%)", "id": "e1"}`. Reference earlier metrics by
  their `id` field (`m1`, `m2`). This is the only way to compute rates,
  ratios, and percentages from raw CloudWatch metrics within the dashboard
  itself. Without metric math, operators export data to external tools.

- **Cross-account dashboards use OAM shared observability.** Create a
  sink in the monitoring account (`oam create-sink`), then create links
  from source accounts to the sink (`oam create-link`). The monitoring
  account's dashboard can then filter by the `@Account` dimension to see
  metrics from linked source accounts. This replaces the legacy approach
  of cross-account IAM role assumption per source account and scales to
  hundreds of accounts via AWS Organizations.

- **Anomaly detection bands require training data.** The
  `ANOMALY_DETECTION_BAND` math function creates a band of expected
  values. It needs a minimum of 15 minutes of metric data; optimal
  accuracy requires 2+ weeks. The band width (`stdev` parameter) controls
  sensitivity: `stdev: 1` (tight, more anomalies flagged) vs `stdev: 3`
  (loose, fewer false positives). Start with `stdev: 2` and tune.

- **Custom widgets execute Lambda functions.** A custom widget type
  (`"type": "custom"`) invokes a Lambda function URL or function ARN to
  render arbitrary content (HTML, SVG, tables). The Lambda must have a
  resource-based policy allowing `cloudwatch.amazonaws.com` to invoke it.
  The Lambda receives the dashboard context (time range, variables) and
  returns HTML. Custom widgets are powerful but introduce a code execution
  surface — review the Lambda code before deploying.

- **Dashboard sharing uses a resource-based policy.** By default,
  dashboards are private to the account. `cloudwatch
  put-dashboard-sharing-config` (or the console) adds a resource-based
  policy that allows other accounts to view the dashboard. Avoid sharing
  to `*` principal — it exposes all dashboard data (metrics, logs,
  alarms) publicly. Share to specific account IDs or OUs.

- **Dashboard variables enable dynamic filtering.** Variables (introduced
  2024) let dashboard users select values from dropdowns that filter
  widgets. Define variables in the dashboard body: `{"name": "DBInstance",
  "type": "dimension", "value": "*", "label": "DB Instance"}`. Widgets
  reference variables via `${DBInstance}`. This replaces hard-coded
  dimension values and makes a single dashboard reusable across resources.

- **Auto-refresh intervals affect cost.** Dashboards auto-refresh at the
  interval configured in the browser (1m, 2m, 5m, 15m). Each refresh
  triggers GetMetricData API calls for each widget. With Metrics Insights
  widgets ($0.005/1K queries) or many widgets (50+), frequent refresh
  can accumulate costs. Set 5m as the default; 1m only for ops bridges.

- **Metrics Insights enables SQL-like metric queries.** `SELECT
  avg(CPUUtilization) FROM AWS/RDS WHERE DBInstanceIdentifier LIKE
  'prod-%' GROUP BY DBInstanceIdentifier ORDER BY avg() DESC LIMIT 10`.
  This returns aggregated metrics across many resources without
  pre-defining individual widgets. Use for top-N dashboards (top 10 EC2
  instances by CPU, top 10 Lambda functions by duration).

- **Alarm widgets show alarm state in context.** Add a `"type": "alarm"`
  widget to display one or more CloudWatch Alarms directly in the
  dashboard. The alarm's OK/ALARM/INSUFFICIENT_DATA state renders
  visually. Clicking the alarm navigates to the alarm details. This is
  the standard way to integrate alerting into operational dashboards.

- **Cross-section switching uses `@Account` and `@Region`.** When OAM is
  configured, dashboard widgets can filter by `@Account` (source account
  ID) and `@Region` (AWS region). Add these as dashboard variables for a
  cross-region, cross-account operational view. Without OAM, these
  dimensions return no data.

- **Service-specific dashboard templates reduce setup time.** The common
  service dashboards (RDS, EC2, Lambda, ECS) follow standard patterns:
  RDS shows CPU, memory, connections, storage, and query throughput;
  EC2 shows CPU, network, disk, and status checks; Lambda shows
  invocations, errors, duration, and throttles; ECS shows CPU, memory,
  and task counts. The templates in this skill's reference cover the
  exact JSON for each.

- **Dashboard body has a 256 KB size limit.** This translates to
  approximately 100-200 widgets depending on complexity. Metrics
  Insights queries and custom widgets consume more space due to their
  expression strings. For very large deployments, split into multiple
  dashboards (e.g., per service or per environment).

- **GetDashboard returns the body as an escaped JSON string.** The
  `DashboardBody` field in the GetDashboard response is a JSON string
  (not a nested object). Parse it with `jq -r '.DashboardBody | fromjson'`
  to work with it programmatically. This is a common stumbling block for
  IaC pipelines.

- **CloudWatch logs widgets use Logs Insights queries.** A `"type":
  "log"` widget runs a Logs Insights query and renders the results.
  `query: "fields @timestamp, @message | sort @timestamp desc | limit
  20"`. This integrates log context directly into metric dashboards for
  faster incident response.

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Dashboard variables (2024-2025):** Dynamic variables enable dropdown
  filters that replace hard-coded dimension values. Variables can be
  metric dimensions (`DBInstanceIdentifier`, `FunctionName`) or custom
  value sets. A single dashboard with variables replaces dozens of
  resource-specific dashboards.

- **CloudWatch OAM shared observability GA (2024):** Observability
  Access Manager creates a sink in the monitoring account and links from
  source accounts. The monitoring account sees metrics, logs, and traces
  from all linked accounts via the `@Account` dimension. OAM scales to
  hundreds of accounts via AWS Organizations integration.

- **Metrics Insights in dashboard widgets (2024-2025):** SQL-like
  queries (`SELECT avg(CPUUtilization) FROM AWS/EC2 GROUP BY InstanceId
  ORDER BY avg() DESC LIMIT 10`) render as top-N tables or time-series
  charts. Enables cross-resource aggregation without pre-defining
  individual widgets.

- **Anomaly detection on custom metrics (2024-2025):** The
  `ANOMALY_DETECTION_BAND` function now supports custom metric
  namespaces (not just AWS namespaces). Training uses the last 15 days
  of data by default; supports up to 90 days for seasonal patterns.

- **Custom widget improvements (2024-2025):** Custom widgets now support
  POST method (not just GET), enabling richer dashboard interactions
  (buttons, forms). Lambda function URLs are the recommended invocation
  path (replacing the legacy direct-ARN method).

- **Dashboard sharing via resource-based policy (2024-2025):**
  `put-dashboard-sharing-config` API enables sharing dashboards with
  specific accounts, OUs, or organizations. Shared dashboards are
  read-only in the target account.

- **Cross-region dashboard via @Region variable (2024-2025):** The
  `@Region` variable (paired with `@Account`) enables cross-region
  dashboards. Widgets filter by region without requiring separate
  dashboards per region.

- **CloudWatch logs in metric dashboards (2025):** Log widgets now
  support embedded Logs Insights queries with time-series visualization.
  Correlate metric spikes with log entries in a single dashboard view.

- **Dashboard-as-code via CloudFormation (2024-2025):** The
  `AWS::CloudWatch::Dashboard` resource type supports the full dashboard
  JSON body. Deploy via CloudFormation or CDK for GitOps workflows.

- **Automatic dashboard creation for new resources (2025):** Application
  Signals auto-creates dashboards for new RDS, EC2, Lambda, ECS, and
  DynamoDB resources. These dashboards are editable and serve as
  starting templates for custom operational views.
