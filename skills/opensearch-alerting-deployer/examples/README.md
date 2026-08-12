# End-to-End Example: OpenSearch Alerting Deployment

A walkthrough showing how to use the `opensearch-alerting-deployer`
skill from invocation through verification. Mirrors the structured-
eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a per-query error count monitor on an
OpenSearch cluster with a Slack notification destination. The
monitor needs:

- Monitor type: per-query
- Target index: application-logs-*
- Query: match level=error, range @timestamp >= now-5m, aggregate
  value_count
- Trigger: error_count > 100, severity 1
- Destination: ops-alerts-slack (Slack webhook, already configured)
- Schedule: every 5 minutes
- Cluster: https://search-prod.example.com

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-opensearch-alerting
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create an OpenSearch error count monitor on
      search-prod.example.com. Alert on > 100 errors in 5 minutes.
      Notify Slack destination ops-alerts-slack. Schedule every
      5 minutes. Severity 1."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create an opensearch alerting monitor"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
OPENSEARCH_ALERTING: error-count-monitor (per-query) — every 5 minutes
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Monitor type: per-query
  [✓] Target index: application-logs-*
  [✓] Query: match level=error, range now-5m, aggregate value_count
  [✓] Trigger: high-error-count — severity 1 — error_count > 100
  [✓] Destination: ops-alerts-slack (slack) — dest-id-xxx
  [✓] Action: notify-slack → destination ops-alerts-slack
  [✓] Message template: "Alert: {{ctx.monitor.name}} — Errors: {{ctx.results[0].aggregations.error_count.value}}"
  [✓] Schedule: every 5 MINUTES
  [✓] Alert severity: 1 (high)
  [✓] Alert acknowledgment: enabled (UI/API)
  [✓] Tags: Environment=production, Team=ops
VERIFICATION_COMMANDS:
  curl <endpoint>/_plugins/_alerting/monitors/<monitor-id>
  curl <endpoint>/_plugins/_alerting/destinations/<destination-id>
  curl <endpoint>/.plugins-alerting-alerts/_search?size=5&sort=start_time:desc
```

---

## Step 3 — Provisioning commands

```bash
ENDPOINT="https://search-prod.example.com"
AUTH="admin:password"

# Step 1: Verify the destination exists
curl -s "$ENDPOINT/_plugins/_alerting/destinations" \
  -u "$AUTH" | jq '.destinations[] | select(.name=="ops-alerts-slack")'

# Step 2: Create the monitor
MONITOR_ID=$(curl -s -X POST "$ENDPOINT/_plugins/_alerting/monitors" \
  -H "Content-Type: application/json" \
  -u "$AUTH" \
  -d '{
    "type": "monitor",
    "name": "error-count-monitor",
    "monitor": {
      "type": "monitor",
      "schedule": {
        "period": { "interval": 5, "unit": "MINUTES" }
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
              "destination_id": "dest-xxx",
              "message_template": {
                "source": "Alert: {{ctx.monitor.name}}\nSeverity: {{ctx.trigger.severity}}\nErrors: {{ctx.results[0].aggregations.error_count.value}}\nTime: {{ctx.periodStart}} to {{ctx.periodEnd}}"
              }
            }
          ]
        }
      ]
    }
  }' | jq -r '._id')

echo "Monitor ID: $MONITOR_ID"
```

---

## Step 4 — Post-deployment verification

```bash
# Verify the monitor exists and check its configuration
curl -s "$ENDPOINT/_plugins/_alerting/monitors/$MONITOR_ID" \
  -u "$AUTH" | jq '.monitor | {name, type, schedule, triggers}'

# Verify the destination
curl -s "$ENDPOINT/_plugins/_alerting/destinations/dest-xxx" \
  -u "$AUTH" | jq '.destination | {name, type}'

# Check for recent alerts
curl -s "$ENDPOINT/.plugins-alerting-alerts/_search?size=5&sort=start_time:desc" \
  -u "$AUTH" | jq '.hits.hits[]._source | {state, trigger_name, start_time}'

# Acknowledge an alert (if any are active)
# curl -X PUT "$ENDPOINT/_plugins/_alerting/acks/<alert-id>" -u "$AUTH"
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Destination ordering | Monitor before destination | Destination before monitor | Monitor creates OK but first alert fails silently |
| Query size | `size > 0` (fetches documents) | `size: 0` (aggregations only) | Avoids unnecessary document fetch cost |
| SNS notification plugin | Not checked | notification.yaml verified | SNS actions fail without the plugin |
| Monitor type | Generic "monitor" | Correct type (per-query/cluster/per-doc) | Wrong type = wrong behavior or missed alerts |
| Severity routing | Severity routes alerts | Severity is metadata; separate triggers needed | Severity alone does not route to different channels |
| Anomaly detection cold start | Immediate anomalies expected | Cold start 10-15 min noted | AD triggers produce no anomalies during training |
| Acknowledgment semantics | Stops future alerts | Marks alert; does NOT mute trigger | New alerts fire for subsequent breaches |
| Cost scaling | Any frequency | Frequency x query complexity cited | Complex queries every minute degrade cluster |

---

## Related artifacts

- **Skill definition:** `skills/opensearch-alerting-deployer/SKILL.md`
- **Monitors and triggers guide:** `skills/opensearch-alerting-deployer/references/monitors-and-triggers.md`
- **Destinations and actions guide:** `skills/opensearch-alerting-deployer/references/destinations-and-actions.md`
- **Slash command:** `commands/aws/deploy-opensearch-alerting.md`
- **Eval suite:** `skills/opensearch-alerting-deployer/evals/evals.json`
- **Legacy test cases:** `skills/opensearch-alerting-deployer/eval/test-cases.yaml`
