# Data Sources and Dashboard JSON — Grafana Dashboard Deployer

Reference for configuring each AWS data source type in Managed Grafana,
and the dashboard JSON model structure for panels, templating, and alerting.

## Data source types

### CloudWatch

| Setting | Value |
|---|---|
| Type | `cloudwatch` |
| Auth | SigV4 (uses workspace IAM role) |
| Regions | Specify per-region or all |
| Metrics | CloudWatch metric namespaces (AWS/EC2, AWS/Lambda, etc.) |
| Logs | CloudWatch Logs Insights queries |

**Required IAM permissions:**
```json
[
  "cloudwatch:GetMetricData",
  "cloudwatch:GetMetricStatistics",
  "cloudwatch:ListMetrics",
  "logs:DescribeLogGroups",
  "logs:GetLogEvents",
  "logs:StartQuery",
  "logs:GetQueryResults"
]
```

**Query example (metric):**
```json
{
  "namespace": "AWS/EC2",
  "metricName": "CPUUtilization",
  "statistics": ["Average"],
  "dimensions": {"InstanceId": "i-abc123"},
  "period": "300"
}
```

### AMP / Prometheus

| Setting | Value |
|---|---|
| Type | `prometheus` |
| URL | `https://aps-workspaces.<region>.amazonaws.com/workspaces/<amp-id>/` |
| Auth | SigV4 (uses workspace IAM role) |
| Query language | PromQL |

**Required IAM permissions:**
```json
[
  {"Action": "aps:GetLabels", "Resource": "<amp-workspace-arn>"},
  {"Action": "aps:GetMetricMetadata", "Resource": "<amp-workspace-arn>"},
  {"Action": "aps:GetSeries", "Resource": "<amp-workspace-arn>"},
  {"Action": "aps:QueryMetrics", "Resource": "<amp-workspace-arn>"}
]
```

**Query example (PromQL):**
```promql
rate(http_requests_total{status="500"}[5m]) / rate(http_requests_total[5m]) * 100
```

### Timestream

| Setting | Value |
|---|---|
| Type | `timestream` |
| Auth | SigV4 (uses workspace IAM role) |
| Database | Specify via query (USE database.table) |
| Query language | SQL (Timestream-compatible) |

**Required IAM permissions:**
```json
[
  "timestream:Select",
  "timestream:DescribeEndpoints"
]
```

**Query example:**
```sql
SELECT region, avg(measure_value::double) as avg_cpu
FROM "infra"."metrics"
WHERE measure_name = 'cpu_utilization'
  AND time > ago(1h)
GROUP BY region
ORDER BY avg_cpu DESC
```

### OpenSearch

| Setting | Value |
|---|---|
| Type | `elasticsearch` (OpenSearch compatible) |
| URL | `https://<domain>.<region>.es.amazonaws.com` |
| Auth | AWS SigV4 (uses workspace IAM role) |
| Index pattern | Specify per dashboard (e.g., `logstash-*`) |
| Query language | Lucene, PPL (OpenSearch) |

**Required IAM permissions:**
```json
[
  {"Action": "es:ESHttpGet", "Resource": "<opensearch-domain-arn>/*"},
  {"Action": "es:ESHttpHead", "Resource": "<opensearch-domain-arn>/*"}
]
```

### X-Ray

| Setting | Value |
|---|---|
| Type | `xray` |
| Auth | SigV4 (uses workspace IAM role) |
| Regions | Specify per-region |
| Query | Service map, trace summaries, response time |

**Required IAM permissions:**
```json
[
  "xray:GetTraceSummaries",
  "xray:GetTraceGraph",
  "xray:GetSamplingRules",
  "xray:GetSamplingTargets"
]
```

## Dashboard JSON model

### Full structure

```json
{
  "title": "Dashboard Title",
  "schemaVersion": 39,
  "version": 1,
  "refresh": "30s",
  "time": {"from": "now-6h", "to": "now"},
  "timepicker": {"refresh_intervals": ["5s", "10s", "30s", "1m", "5m"]},
  "templating": {
    "list": []
  },
  "annotations": {
    "list": []
  },
  "panels": [],
  "links": []
}
```

### Templating variables

| Variable type | Use case | Example |
|---|---|---|
| `datasource` | Switch between data sources | `{"name": "ds", "type": "datasource", "query": "cloudwatch"}` |
| `query` | Dynamic values from a data source | `{"name": "region", "type": "query", "datasource": "$ds", "query": "regions()"}` |
| `custom` | Hardcoded options | `{"name": "env", "type": "custom", "query": "prod,staging,dev"}` |
| `interval` | Time aggregation | `{"name": "interval", "type": "interval", "query": "1m,5m,15m,1h"}` |
| `text` | Free text input | `{"name": "threshold", "type": "text", "default": "85"}` |

### Panel grid layout

Grafana uses a 24-column grid. Panels are positioned via `gridPos`:

```json
{
  "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
}
```

- `h`: height in grid units (1 unit ~ 30px)
- `w`: width in grid units (max 24 for full width)
- `x`: horizontal position (0-23)
- `y`: vertical position (0+)

### Panel types and when to use them

| Panel type | Grafana identifier | Use when | Data shape |
|---|---|---|---|
| Time series | `timeseries` | Metrics over time | Time-value pairs |
| Stat | `stat` | Single KPI (current value) | Scalar or latest |
| Gauge | `gauge` | Single value with range | Scalar (0-100%) |
| Bar gauge | `bargauge` | Compare categories | Key-value pairs |
| Table | `table` | Tabular data | Rows + columns |
| Heatmap | `heatmap` | Distribution over time | Buckets by time + value |
| Node graph | `nodegraph` | Service map / topology | Nodes + edges |
| Logs | `logs` | Log viewer | Timestamp + text |
| Geomap | `geomap` | Geographic data | Lat/long + value |
| Candlestick | `candlestick` | OHLC data | Open/high/low/close |
| Pie chart | `piechart` | Proportional data | Key-value pairs |
| Bar chart | `barchart` | Categorical comparison | Key-value pairs |

### Common panel patterns

**Time series with threshold:**
```json
{
  "type": "timeseries",
  "title": "CPU Utilization",
  "datasource": {"type": "cloudwatch", "uid": "$ds"},
  "fieldConfig": {
    "defaults": {
      "thresholds": {
        "steps": [
          {"color": "green", "value": 0},
          {"color": "yellow", "value": 70},
          {"color": "red", "value": 85}
        ]
      }
    }
  },
  "targets": [{
    "namespace": "AWS/EC2",
    "metricName": "CPUUtilization",
    "statistics": ["Average"],
    "period": "300"
  }]
}
```

**Stat panel with calculation:**
```json
{
  "type": "stat",
  "title": "Active Instances",
  "datasource": {"type": "cloudwatch", "uid": "$ds"},
  "options": {
    "reduceOptions": {"calcs": ["lastNotNull"], "fields": ""}
  },
  "targets": [{
    "namespace": "AWS/EC2",
    "metricName": "StatusCheckFailed",
    "statistics": ["Sum"],
    "period": "300"
  }]
}
```

## Alerting model

### Alert rule structure

```json
{
  "uid": "rule-uid",
  "title": "Rule Title",
  "condition": "B",
  "data": [
    {"refId": "A", "datasourceUid": "<ds-uid>", "model": {}},
    {"refId": "B", "model": {"expression": "$A > 85", "type": "math"}}
  ],
  "evalInterval": "1m",
  "for": "5m",
  "annotations": {"summary": "Brief description", "description": "Detailed description"},
  "labels": {"severity": "warning", "team": "platform"}
}
```

### Notification policy tree

```json
{
  "receiver": "default",
  "group_by": ["alertname", "severity"],
  "routes": [
    {
      "receiver": "sns-critical",
      "object_matchers": [["severity", "=", "critical"]],
      "group_wait": "0s",
      "group_interval": "10s",
      "repeat_interval": "1h"
    },
    {
      "receiver": "slack-warnings",
      "object_matchers": [["severity", "=", "warning"]],
      "group_wait": "30s",
      "group_interval": "5m",
      "repeat_interval": "4h"
    }
  ]
}
```

### Contact point types

| Type | Key settings | Use when |
|---|---|---|
| `sns` | topic, authProvider, region | AWS-native, integrates with Lambda/SES |
| `slack` | url, channel, text | Team chat |
| `email` | addresses | Broad distribution |
| `pagerduty` | integrationKey, severity | On-call escalation |
| `webhook` | url, httpMethod | Custom integrations |
| `opsgenie` | apiKey, priority | Enterprise incident management |
| `telegram` | bottoken, chatid | Mobile notifications |

## Step 4 — Dashboard JSON model (panels, templating, time range) — moved from SKILL.md

**Dashboard JSON structure:**

```json
{
  "title": "Production Observability",
  "schemaVersion": 39,
  "version": 1,
  "refresh": "30s",
  "time": { "from": "now-6h", "to": "now" },
  "templating": {
    "list": [
      {
        "name": "datasource",
        "type": "datasource",
        "query": "cloudwatch",
        "current": { "text": "CloudWatch", "value": "cloudwatch" }
      },
      {
        "name": "region",
        "type": "query",
        "datasource": "$datasource",
        "query": "regions()",
        "current": { "text": "us-east-1", "value": "us-east-1" }
      }
    ]
  },
  "panels": [
    {
      "type": "timeseries",
      "title": "CPU Utilization",
      "datasource": "$datasource",
      "gridPos": { "h": 8, "w": 12, "x": 0, "y": 0 },
      "targets": [
        {
          "expr": "AWS/EC2 CPUUtilization",
          "namespace": "AWS/EC2",
          "metricName": "CPUUtilization",
          "statistics": ["Average"]
        }
      ]
    }
  ]
}
```

**Templating variables** make dashboards reusable across environments,
regions, and services. Use `datasource`, `query`, and `custom` variable
types for dynamic filtering.

**Panel types by use case:**

| Panel type | Use when |
|---|---|
| `timeseries` | Time-series metrics (CPU, latency, throughput) |
| `stat` | Single-value KPIs (current value, threshold) |
| `gauge` | Single-value with range (0-100%, utilization) |
| `table` | Multi-column data (instance list, log results) |
| `bargauge` | Comparison across categories (cost by service) |
| `heatmap` | Distribution over time (latency percentiles) |
| `nodegraph` | Service maps (X-Ray traces) |
| `logs` | Log viewer (CloudWatch Logs queries) |

**Provisioning dashboards via API:**
```bash
# Get workspace API key
aws grafana create-workspace-api-key \
  --workspace-id <workspace-id> \
  --key-name deploy-key \
  --key-role ADMIN \
  --seconds-to-live 3600 \
  --query 'key' --output text > /tmp/grafana-key

# Import dashboard via Grafana HTTP API
curl -X POST \
  -H "Authorization: Bearer $(cat /tmp/grafana-key)" \
  -H "Content-Type: application/json" \
  -d @dashboard.json \
  https://<workspace-endpoint>/api/dashboards/db
```

## Step 6 — AMP workspace integration — moved from SKILL.md

Amazon Managed Service for Prometheus (AMP) provides serverless Prometheus-
compatible metric storage. Integration with Grafana is via the Prometheus
data source.

```bash
# Create AMP workspace
aws amps create-workspace \
  --workspace-name <amp-name> \
  --alias <amp-alias> \
  --kms-key-arn arn:aws:kms:<region>:<acct>:key/<key-id>

# Wait for ACTIVE status
aws amps describe-workspace --workspace-id <amp-id> \
  --query 'workspace.status.statusCode' --output text

# Configure remote write (from Prometheus / OpenTelemetry / CloudWatch agent)
# The AMP workspace endpoint is:
# https://aps-workspaces.<region>.amazonaws.com/workspaces/<amp-id>/
```

**Remote write sources:**
- CloudWatch agent with embedded metric format
- Prometheus server with `remote_write` to AMP
- OpenTelemetry Collector with Prometheus exporter
- Distroless OTel collector on EKS/ECS

**Common mistake:** querying AMP before metrics are flowing. Verify remote
write is active by checking `aws amps describe-workspace` for ingest
metrics, then querying from Grafana.
