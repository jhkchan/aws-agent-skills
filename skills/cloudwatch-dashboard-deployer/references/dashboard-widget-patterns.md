# CloudWatch Dashboard Widget Patterns Reference

Load this reference when planning or executing any CloudWatch dashboard
deployment. The procedures below are the canonical widget configurations,
sharing models, and verification sequences for each dashboard archetype.

## Decision tree — which dashboard archetype

| Scenario | Use | Why |
|---|---|---|
| Fleet health (CPU, memory, disk, network) | **Operational dashboard** | Per-instance metric widgets with dashboard variables |
| Service-level objectives (availability, latency, burn rate) | **SLO dashboard** | Application Signals metrics with burn-rate annotations |
| Business KPIs (request volume, error rate, cost) | **Executive dashboard** | Single-value widgets with large time ranges |
| Multi-account visibility | **Cross-account dashboard** | Shared dashboard with AccountId in each metric |
| Point-in-time compliance evidence | **Snapshot sharing** | Static S3-hosted snapshot via presigned URL |
| Log-based error analysis | **Log insights dashboard** | Log widget with filter/stats query syntax |
| Combining multiple metrics (rate, ratio) | **Metric math dashboard** | Expression widgets combining m-IDs |

## Metric widget procedure

**When to use:** time-series visualization of one or more CloudWatch
metrics.

**Pre-checks:**
1. Namespace + MetricName + Dimensions return datapoints via
   `get-metric-statistics` (case-sensitive).
2. Period >= metric native publishing interval (60s detailed, 300s basic).
3. Statistic matches metric semantics (Sum for counts, Average for
   utilization).
4. Dashboard variables map to valid dimension names.

**Widget JSON structure:**
```json
{
  "type": "metric",
  "x": 0, "y": 0, "width": 12, "height": 6,
  "properties": {
    "metrics": [
      ["AWS/EC2", "CPUUtilization", "InstanceId", "${INSTANCE_ID}"]
    ],
    "period": 300,
    "stat": "Average",
    "region": "us-east-1",
    "title": "CPU Utilization",
    "view": "timeSeries",
    "stacked": false,
    "liveData": true,
    "setPeriodToTimeRange": true
  }
}
```

**Key fields:**
- `metrics`: array of metric arrays `[namespace, metric, dimName, dimValue, {options}]`.
- `period`: seconds (60, 300, 3600, etc.).
- `stat`: Average, Sum, Maximum, Minimum, SampleCount, p99, etc.
- `view`: timeSeries, singleValue, bar, pie, gauge.
- `liveData`: true shows the most recent datapoint even if period isn't
  complete.
- `setPeriodToTimeRange`: true adjusts period to match dashboard time
  range for singleValue widgets.

**Common failure modes:**
- Empty chart — wrong namespace, wrong dimensions, or metric not
  publishing. Verify via `get-metric-statistics`.
- Misleading values — `Sum` on high-resolution utilization metrics
  inflates values. Use `Average` for utilization.

## Log insights widget procedure

**When to use:** visualizing log query results on a dashboard.

**Widget JSON structure:**
```json
{
  "type": "log",
  "x": 0, "y": 6, "width": 24, "height": 6,
  "properties": {
    "query": "SOURCE '/aws/lambda/prod-checkout'\n| fields @timestamp, requestId, @message\n| filter @message like /ERROR/\n| stats count() by bin(5m)\n| sort @timestamp desc\n| limit 100",
    "region": "us-east-1",
    "title": "Lambda Errors (5-min buckets)",
    "view": "timeSeries"
  }
}
```

**Query syntax reference:**
- `SOURCE 'log-group-name'` — specify log group (or use account-level
  selection in console).
- `fields field1, field2` — select fields to display.
- `filter condition` — WHERE clause (supports `like`, `=`, `>`, `<`,
  `and`, `or`, `not`).
- `stats count() by bin(5m)` — aggregation with time bucketing.
- `sort field desc` — order results.
- `limit N` — cap result count (ALWAYS include for performance).

**Common failure modes:**
- Dashboard timeout — unbounded query on large log group. Always add
  `limit` and time bucketing (`bin(5m)`).
- Empty results — log group exists but not receiving events, or filter
  condition is too restrictive.

## Alarm widget procedure

**When to use:** displaying alarm state on a dashboard.

**Widget JSON structure:**
```json
{
  "type": "alarm",
  "x": 0, "y": 0, "width": 12, "height": 3,
  "properties": {
    "title": "Production Critical Alarms",
    "alarms": [
      "arn:aws:cloudwatch:us-east-1:111111111111:alarm:ec2-cpu-high-prod-web-1",
      "arn:aws:cloudwatch:us-east-1:111111111111:alarm:lambda-errors-high-prod-checkout"
    ]
  }
}
```

**Key fields:**
- `alarms`: array of full alarm ARNs (not names).

**Common failure modes:**
- "Alarm not found" — alarm deleted or ARN region/account wrong.
- Stale state — alarm widget shows the state at dashboard render time,
  not live.

## Text widget procedure

**When to use:** section headers, runbook links, dashboard descriptions.

**Widget JSON structure:**
```json
{
  "type": "text",
  "x": 0, "y": 0, "width": 24, "height": 2,
  "properties": {
    "markdown": "# Production Operations\n**Runbook**: [Incident Guide](https://runbooks.example.com)\n- On-call: PagerDuty `prod-oncall`\n- Escalation: `#prod-incidents`"
  }
}
```

**Markdown support:** headers (#, ##, ###), bold (**text**), italic
(*text*), links ([label](url)), lists (- item), inline code (`code`).

## Metric math widget procedure

**When to use:** combining multiple metrics (rate, ratio, percentage,
aggregation).

**Widget JSON structure:**
```json
{
  "type": "metric",
  "x": 12, "y": 0, "width": 12, "height": 6,
  "properties": {
    "metrics": [
      ["AWS/ApplicationELB", "HTTPCode_ELB_5XX_Count", "LoadBalancer", "app/prod-alb/1234567890", {"id": "m1"}],
      ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", "app/prod-alb/1234567890", {"id": "m2"}],
      [{"expression": "m1/m2*100", "label": "Error Rate %", "id": "e1"}]
    ],
    "period": 60,
    "stat": "Sum",
    "title": "ALB 5xx Error Rate (%)",
    "view": "timeSeries"
  }
}
```

**Metric math ID convention:**
- `m1`, `m2`, ... — metric IDs (assigned via `{"id": "m1"}` in the
  metric options).
- `e1`, `e2`, ... — expression IDs (assigned via the expression object).
- Expressions reference metric IDs: `m1/m2`, `m1+m2`, `FILL(m1, 0)`,
  `m1 PERIOD(m2)`, etc.

**Useful expressions:**
- Rate: `m1 / m2` (e.g., errors / total requests).
- Percentage: `m1/m2 * 100`.
- Fill missing data: `FILL(m1, 0)`.
- Per-period rate: `m1 / PERIOD(m1)`.
- Average across dimensions: `AVG(m1)`.

## Custom metric sources

| Source | How metrics get in | Best for | Cost |
|---|---|---|---|
| AWS services (AWS/EC2, AWS/Lambda, etc.) | Auto-published | Infrastructure monitoring | Free |
| CloudWatch Agent (CWAgent namespace) | Agent on EC2/ECS | OS-level metrics (memory, disk, swap) | Free (agent metrics) |
| PutMetricData API | CLI / SDK call | Application custom metrics | $0.30/metric/month |
| Embedded Metrics Format (EMF) | Log to CloudWatch Logs | High-cardinality app metrics | Log ingestion cost only |
| OpenTelemetry (AWS/OTel) | OTel collector | Multi-cloud standard metrics | Free (ingestion-based) |

**EMF example (Node.js):**
```javascript
{
  "_aws": {
    "Timestamp": Date.now(),
    "CloudWatchMetrics": [{
      "Namespace": "MyApp",
      "Dimensions": [["ServiceName", "Operation"]],
      "Metrics": [{"Name": "LatencyMs", "Unit": "Milliseconds"}]
    }]
  },
  "ServiceName": "checkout",
  "Operation": "processOrder",
  "LatencyMs": 245
}
```

## Cross-account dashboard sharing procedure

**When to use:** central monitoring account viewing metrics from
multiple source accounts.

**Step 1: Create sharing role in each source account:**
```bash
aws iam create-role \
  --role-name CloudWatch-CrossAccountSharingRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
      "Action": "sts:AssumeRole",
      "Condition": {}
    }]
  }'

aws iam attach-role-policy \
  --role-name CloudWatch-CrossAccountSharingRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/CloudWatch-CrossAccountSharingRolePolicy
```

**Step 2: Enable cross-account sharing in the monitoring account:**
```bash
aws cloudwatch put-dashboard \
  --dashboard-name "cross-account-ops" \
  --dashboard-body '{"widgets":[...]}'
```

Each metric widget must include `AccountId` in the metric options:
```json
["AWS/EC2", "CPUUtilization", "InstanceId", "i-0123456789abcdef0",
  {"AccountId": "222222222222", "label": "Dev Account CPU"}]
```

**Common failure modes:**
- Empty widgets — sharing role missing in source account. Verify via
  `aws iam get-role --role-name CloudWatch-CrossAccountSharingRole`.
- Partial visibility — role exists but lacks permission for specific
  namespaces. Check the attached policy.

## Dashboard variable configuration

Variables enable dynamic dimension selection from the dashboard UI.

**Variable in a widget dimension:**
```json
["AWS/EC2", "CPUUtilization", "InstanceId", "${INSTANCE_ID}"]
```

**Variable definition (set via console or DashboardBody):**
- `$INSTANCE_ID` — replaced at render time with the operator-selected
  value from the variable dropdown.
- Supports wildcard `${INSTANCE_ID}` — selects all instances if no
  value chosen.

**Common variable patterns:**
- Per-instance: `InstanceId=${INSTANCE_ID}` for fleet dashboards.
- Per-region: `Region=${REGION}` for multi-region views.
- Per-service: `ServiceName=${SERVICE}` for microservice dashboards.

## Layout best practices

| Dashboard type | Layout pattern |
|---|---|
| Operational (fleet) | 2-column grid (12+12 width), top-to-bottom by urgency |
| SLO | Full-width (24) burn-rate charts, annotations for thresholds |
| Executive | 4-column singleValue widgets (6 width each), large time range |
| Log analysis | Full-width (24) log widgets, stacked vertically |
| Alarm overview | 3-column alarm widgets (8 width each) |

**Position rules:**
- x: 0-23 (24-column grid).
- width: 1-24 (typical: 6, 12, or 24).
- y: 0+ (unbounded, auto-stacking).
- height: 1+ (typical: 2-6).

## Cost reference (2026)

- Dashboards: $3/dashboard/month (first 3 free).
- Dashboard refresh API calls: free.
- Metric API calls (get-metric-statistics): $0.01/1,000 requests.
- Custom metrics: $0.30/metric/month (first 10,000 free).
- EMF metrics: free (only pay for log ingestion).
- Cross-account sharing: no additional charge (role-based).

For a fleet of 50 dashboards + 500 custom metrics, monthly cost is
~$300 — dominated by custom metric volume.
---

## Operational dashboard — EC2 fleet (metric widgets) (boilerplate) (moved from SKILL.md)

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
---

## Log insights widget — error analysis (boilerplate) (moved from SKILL.md)

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
---

## Alarm widget (boilerplate) (moved from SKILL.md)

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
---

## Text widget (Markdown runbook link) (boilerplate) (moved from SKILL.md)

```json
{
  "type": "text",
  "x": 0, "y": 0, "width": 24, "height": 2,
  "properties": {
    "markdown": "# Production Operations Dashboard\n**Runbook**: [Incident Response](https://runbooks.example.com/incident)\n**On-call rotation**: PagerDuty schedule `prod-oncall`\n**Escalation**: Slack `#prod-incidents`"
  }
}
```
---

## Metric math — error rate (errors / total requests) (boilerplate) (moved from SKILL.md)

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
---

## SLO dashboard — burn rate (Application Signals) (boilerplate) (moved from SKILL.md)

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
---

## Cross-account dashboard (shared) (boilerplate) (moved from SKILL.md)

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
---

## Executive dashboard — KPI summary (single-value widgets) (boilerplate) (moved from SKILL.md)

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
