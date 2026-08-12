# Monitors and Triggers — OpenSearch Alerting Deployer

Deep reference on monitor types (per-query, cluster metrics, per-
document), trigger condition authoring (threshold Painless scripts,
anomaly detection with Random Cut Forest), scheduling (cron vs
interval), and query optimization for per-query monitors. Loaded on
demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Per-query monitors

A per-query monitor runs a search query at a scheduled interval and
evaluates trigger conditions on the query results.

### Monitor creation

```bash
curl -X POST "<endpoint>/_plugins/_alerting/monitors" \
  -H "Content-Type: application/json" \
  -u "<user>:<pass>" \
  -d '{
    "type": "monitor",
    "name": "error-count-monitor",
    "monitor": {
      "type": "monitor",
      "schedule": {
        "period": {
          "interval": 5,
          "unit": "MINUTES"
        }
      },
      "indices": ["application-logs-*"],
      "query": {
        "size": 0,
        "query": {
          "bool": {
            "must": [
              { "match": { "level": "error" } },
              { "range": { "@timestamp": { "gte": "now-5m" } } }
            ]
          }
        },
        "aggregations": {
          "error_count": { "value_count": { "field": "_id" } }
        }
      },
      "triggers": [
        {
          "name": "high-error-count",
          "severity": "1",
          "condition": {
            "script": {
              "source": "ctx.results[0].aggregations.error_count.value > params.threshold",
              "lang": "painless",
              "params": { "threshold": 100 }
            }
          },
          "actions": [
            {
              "name": "notify-slack",
              "destination_id": "<destination-id>",
              "message_template": {
                "source": "Alert: {{ctx.monitor.name}}\nErrors: {{ctx.results[0].aggregations.error_count.value}}"
              }
            }
          ]
        }
      ]
    }
  }'
```

### Query optimization

The query runs at every scheduled interval. Optimize for cost:

1. **Use `size: 0`** when only aggregations are needed. This avoids
   fetching document hits, reducing query cost significantly.

2. **Limit the time range** to the minimum necessary. Use `now-5m`
   not `now-1h` if the alerting window is 5 minutes.

3. **Use rollup indices** for expensive aggregations. OpenSearch
   Rollups pre-aggregate data into a smaller index. Monitor the
   rollup index instead of the raw index.

```bash
# Create a rollup job for hourly error counts
curl -X PUT "<endpoint>/_plugins/_rollup/jobs/error-hourly-rollup" \
  -H "Content-Type: application/json" \
  -d '{
    "rollup": {
      "enabled": true,
      "schedule": { "interval": { "period": 1, "unit": "Hours" } },
      "last_update_time": 0,
      "source_index": "application-logs-*",
      "target_index": "error-hourly-rollup",
      "metrics": [{
        "source": "level",
        "metrics": [{ "count": {} }]
      }]
    }
  }'

# Monitor queries the rollup index (much smaller)
```

4. **Avoid wildcard queries** on large indices. Use specific index
   names or index patterns with date suffixes.

### Trigger condition context (ctx)

The Painless script has access to the `ctx` object:

| Field | Description |
|---|---|
| `ctx.monitor.name` | Monitor name |
| `ctx.monitor.type` | Monitor type |
| `ctx.trigger.name` | Trigger name |
| `ctx.trigger.severity` | Severity (1-5) |
| `ctx.results` | Array of query results |
| `ctx.results[0].hits.total.value` | Total hit count |
| `ctx.results[0].aggregations` | Aggregation results |
| `ctx.periodStart` | Monitor execution window start |
| `ctx.periodEnd` | Monitor execution window end |
| `ctx.alert` | Alert metadata (on alert actions) |

### Trigger condition examples

**Threshold on aggregation:**
```painless
ctx.results[0].aggregations.error_count.value > params.threshold
```

**Threshold on hit count:**
```painless
ctx.results[0].hits.total.value > 1000
```

**Multiple conditions (AND):**
```painless
ctx.results[0].aggregations.error_count.value > 100 &&
ctx.results[0].aggregations.avg_latency.value > 500
```

**Multiple conditions (OR):**
```painless
ctx.results[0].aggregations.error_count.value > 100 ||
ctx.results[0].aggregations.error_count.value == 0
```

## Cluster metrics monitors

A cluster metrics monitor polls OpenSearch cluster health metrics
and triggers on threshold breaches. No search query overhead.

### Monitor creation

```bash
curl -X POST "<endpoint>/_plugins/_alerting/monitors" \
  -H "Content-Type: application/json" \
  -u "<user>:<pass>" \
  -d '{
    "type": "cluster_metrics_monitor",
    "name": "jvm-heap-monitor",
    "cluster_metrics_monitor": {
      "schedule": {
        "period": { "interval": 1, "unit": "MINUTES" }
      },
      "indices": [],
      "cluster_metrics": {
        "path": "_nodes/stats/jvm",
        "path_params": {},
        "query_key": "nodes.*.jvm.mem.heap_used_percent",
        "aggregation": "max"
      },
      "triggers": [
        {
          "name": "heap-exceeded",
          "severity": "1",
          "condition": {
            "script": {
              "source": "ctx.results[0].value > 85"
            }
          },
          "actions": [...]
        }
      ]
    }
  }'
```

### Available cluster metrics

| Metric | API path | Query key |
|---|---|---|
| JVM heap % | `_nodes/stats/jvm` | `nodes.*.jvm.mem.heap_used_percent` |
| CPU % | `_nodes/stats/process` | `nodes.*.process.cpu.percent` |
| Disk % | `_cat/allocation` | `*.*.disk.percent` |
| Cluster status | `_cluster/health` | `status` |
| Unassigned shards | `_cluster/health` | `unassigned_shards` |
| Pending tasks | `_cluster/pending_tasks` | (count) |

### Aggregation methods

For numeric metrics, choose an aggregation:
- `max` — maximum across nodes (for heap, CPU)
- `min` — minimum across nodes
- `avg` — average across nodes
- `sum` — total across nodes (for shard counts)

## Per-document monitors

A per-document monitor extracts documents from query results and
triggers an action per matching document. This is useful for per-
user or per-transaction alerting.

### Monitor creation

```bash
curl -X POST "<endpoint>/_plugins/_alerting/monitors" \
  -H "Content-Type: application/json" \
  -u "<user>:<pass>" \
  -d '{
    "type": "monitor",
    "name": "per-user-error-monitor",
    "monitor": {
      "type": "doc_level_monitor",
      "schedule": {
        "period": { "interval": 10, "unit": "MINUTES" }
      },
      "indices": ["application-logs-*"],
      "query": {
        "query": {
          "bool": {
            "must": [
              { "match": { "level": "error" } },
              { "range": { "@timestamp": { "gte": "now-5m" } } }
            ]
          }
        }
      },
      "triggers": [
        {
          "name": "per-user-error",
          "severity": "2",
          "condition": {
            "script": {
              "source": "ctx.docs[0].level == \"error\""
            }
          },
          "actions": [
            {
              "name": "notify-webhook",
              "destination_id": "<webhook-destination-id>",
              "message_template": {
                "source": "User {{ctx.docs[0].user_id}} error: {{ctx.docs[0].message}}"
              }
            }
          ]
        }
      ]
    }
  }'
```

### Per-document trigger context

For per-document monitors, `ctx.docs` is an array of matching
documents (not `ctx.results`). Each document's fields are accessible
directly (e.g., `ctx.docs[0].user_id`).

**Warning:** per-document monitors can generate a large number of
actions if many documents match. Each action triggers a separate
notification. Use a deduplication mechanism in the destination
(e.g., Slack thread, SNS message deduplication).

## Anomaly detection triggers

Anomaly detection triggers reference a trained RCF detector.

### Detector lifecycle

1. **Create detector:**
```bash
curl -X POST "<endpoint>/_plugins/_anomaly_detection/detectors" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "latency-detector-001",
    "description": "API latency anomaly detection",
    "time_field": "@timestamp",
    "indices": ["api-metrics-*"],
    "feature_attributes": [{
      "feature_name": "p99_latency",
      "feature_enabled": true,
      "aggregation_query": { "p99": { "percentiles": { "field": "latency_ms", "percents": [99] } } }
    }],
    "detection_interval": { "period": { "interval": 10, "unit": "MINUTES" } },
    "window_size": 10
  }'
```

2. **Start detector:**
```bash
curl -X POST "<endpoint>/_plugins/_anomaly_detection/detectors/<id>/_start"
```

3. **Check detector state:**
```bash
curl "<endpoint>/_plugins/_anomaly_detection/detectors/<id>/_profile"
# Look for "state": "RUNNING" (not "INIT" or "COLD_START")
```

4. **Create monitor referencing the detector:**
```bash
curl -X POST "<endpoint>/_plugins/_alerting/monitors" \
  -d '{
    "type": "monitor_composite",
    "name": "latency-anomaly-monitor",
    "anomaly_detector": { "detector_id": "<id>" },
    "triggers": [{
      "name": "anomaly-detected",
      "severity": "2",
      "condition": {
        "script": { "source": "ctx.results[0].anomaly_grade > 0.9" }
      },
      "actions": [...]
    }]
  }'
```

### Anomaly grade vs confidence

- `anomaly_grade`: 0.0 to 1.0. Higher = more anomalous. Threshold
  typically 0.7 to 0.99.
- `confidence`: 0.0 to 1.0. Higher = more confident in the anomaly
  assessment. Useful for filtering out low-confidence anomalies.

### Cold start

RCF requires training data. During cold start (first 10-15 minutes
after detector start), `anomaly_grade` is 0.0. No anomalies are
detected during this period. Wait for the detector to exit cold
start before relying on AD triggers.

## Scheduling

### Interval schedule

```json
{
  "schedule": {
    "period": { "interval": 5, "unit": "MINUTES" }
  }
}
```

Units: `MINUTES`, `HOURS`, `DAYS`.

### Cron schedule

```json
{
  "schedule": {
    "cron": {
      "expression": "0 */5 * * * ?",
      "timezone": "UTC"
    }
  }
}
```

**Cron format:** 6 fields:
`second minute hour day-of-month month day-of-week`

Common patterns:
- Every 5 minutes: `0 */5 * * * ?`
- Every hour at :00: `0 0 * * * ?`
- Weekdays 9am-5pm: `0 9-17 * * MON-FRI ?`
- First of month at midnight: `0 0 1 * * ?`

**Timezone:** defaults to UTC. Set explicitly to avoid confusion:
`"timezone": "America/New_York"`.

## Terraform notes

The Terraform AWS provider does not have native resources for
OpenSearch alerting monitors or destinations. Use the `curl`
provider, a `local-exec` provisioner, or a Lambda function that
calls the OpenSearch API.

```hcl
# Example: local-exec provisioner for monitor creation
resource "null_resource" "error_count_monitor" {
  triggers = { always = timestamp() }

  provisioner "local-exec" {
    command = <<-EOT
      curl -X POST "${var.opensearch_endpoint}/_plugins/_alerting/monitors" \
        -H "Content-Type: application/json" \
        -u "${var.os_user}:${var.os_pass}" \
        -d @monitor_config.json
    EOT
  }
}
```

## Common pitfalls

1. **Using `size > 0` for aggregation-only monitors.** Always set
   `size: 0` when only aggregations are needed. This avoids fetching
   documents and reduces cost.

2. **Not verifying the detector state for AD triggers.** A detector
   in `COLD_START` or `INIT` state produces no anomalies. Always
   check the detector profile before relying on AD triggers.

3. **Using per-document monitors for high-volume alerts.** Each
   matching document triggers a separate action. For high-volume
   indices, this generates alert storms. Use per-query monitors
   with aggregation instead.

4. **Forgetting the timezone in cron.** Cron defaults to UTC. If
   the team operates in another timezone, set `timezone` explicitly.

5. **Not testing trigger conditions.** Always test the Painless
   script with sample results before deploying. Invalid scripts fail
   silently at runtime (the monitor executes but the trigger never
   fires).
