---
name: opensearch-alerting-deployer
description: >-
  Provisions Amazon OpenSearch Service alerting configurations with
  production defaults: monitor creation (query monitor vs cluster
  metrics monitor vs per-document monitor), trigger conditions
  (threshold, anomaly detection with Random Cut Forest), actions
  (Slack webhook, Amazon SNS, custom webhook, Amazon Chime),
  destination configuration and validation, notification message
  templating (Mustache), alert history, acknowledge alert workflow,
  per-query monitor scheduling (cron vs interval), per-cluster
  metrics monitor (CPU, JVM heap, disk usage), per-document monitor
  for extracted query results, alerting dashboards, alert severity
  levels (1=high to 5=low), and the notification plugin
  (notification.yaml) requirement for SNS actions. Emits a
  READY_TO_DEPLOY checklist with verification commands. Use when
  creating an OpenSearch alerting monitor, configuring a trigger on
  a query threshold, setting up anomaly detection alerts, adding a
  Slack or SNS notification destination, scheduling a monitor with
  cron or interval, or acknowledging an alert. Triggers: create
  OpenSearch monitor, OpenSearch alerting trigger, OpenSearch
  anomaly detection alert, OpenSearch alert destination, OpenSearch
  SNS notification, OpenSearch Slack webhook alert, OpenSearch
  per-query monitor, OpenSearch cluster metrics monitor, OpenSearch
  per-document monitor, OpenSearch alert severity, OpenSearch
  acknowledge alert, OpenSearch alerting dashboard, OpenSearch
  monitor cron schedule.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with opensearch,
  sns, lambda, and secretsmanager access; the OpenSearch cluster
  endpoint must be reachable; the alerting plugin must be enabled
  (default on managed OpenSearch); the notification plugin
  (notification.yaml) must be configured for SNS actions. Works
  with Terraform opensearch_index / opensearch_domain resources
  (alerting via the OpenSearch API or aws_opensearch_domain
  log_publishing_options).
keywords:
  - aws
  - opensearch
  - alerting
  - monitor
  - trigger
  - anomaly detection
  - random cut forest
  - sns
  - slack
  - chime
  - webhook
  - destination
  - notification
  - per-query monitor
  - cluster metrics monitor
  - per-document monitor
  - alert severity
  - acknowledge alert
  - cron schedule
  - cloudops
  - deploy
  - analytics
tags:
  - aws
  - opensearch
  - alerting
  - monitor
  - analytics
  - cloudops
  - deploy
  - sns
  - anomaly-detection
  - notification
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Analytics
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - opensearch
    - alerting
    - monitor
    - analytics
    - cloudops
    - deploy
    - sns
    - anomaly-detection
    - notification
  dependencies:
    - aws-orchestrator
  keywords:
    - create opensearch monitor
    - opensearch alerting trigger
    - opensearch anomaly detection alert
    - opensearch alert destination
    - opensearch sns notification
    - opensearch slack webhook alert
    - opensearch per-query monitor
    - opensearch cluster metrics monitor
    - opensearch per-document monitor
    - opensearch alert severity
    - opensearch acknowledge alert
    - opensearch alerting dashboard
    - opensearch monitor cron schedule
  when_to_use: >-
    Invoke when the user wants to create an OpenSearch alerting
    monitor (per-query, per-cluster-metrics, or per-document),
    configure a trigger with a threshold or anomaly detection
    condition, set up notification actions (Slack, SNS, Chime,
    custom webhook), configure a destination, schedule a monitor
    with cron or interval, acknowledge an alert, or configure alert
    severity levels. Do NOT invoke for OpenSearch domain
    provisioning (use opensearch-domain-deployer), index creation
    (use opensearch-index-deployer), or cluster troubleshooting
    (use opensearch-cluster-troubleshooter).
---

# OpenSearch Alerting Deployer

An AWS CloudOps agent skill that provisions Amazon OpenSearch Service
alerting configurations with correct defaults. The skill walks the
operator through monitor type selection (per-query, per-cluster-
metrics, per-document), trigger configuration (threshold, anomaly
detection with Random Cut Forest), action and destination setup
(Slack, SNS, Chime, custom webhook), message templating, scheduling
(cron vs interval), severity assignment, and alert acknowledgment,
captures requirements, explains why each default matters, and emits
a READY_TO_DEPLOY checklist with copy-pasteable verification
commands.

## Activation keywords

create OpenSearch monitor, OpenSearch alerting trigger, OpenSearch
anomaly detection alert, OpenSearch alert destination, OpenSearch
SNS notification, OpenSearch Slack webhook alert, OpenSearch per-
query monitor, OpenSearch cluster metrics monitor, OpenSearch per-
document monitor, OpenSearch alert severity, OpenSearch acknowledge
alert, OpenSearch alerting dashboard, OpenSearch monitor cron
schedule.

## STRICT output contract

When this skill is invoked with an OpenSearch-alerting-provisioning
request (create a monitor, configure a trigger, set up a
destination, schedule a monitor, or a partial configuration), the
agent MUST respond with the READY_TO_DEPLOY checklist defined in
the "Output format" section using the literal all-caps labels
`OPENSEARCH_ALERTING:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of
the response. This contract is what assertion-based evals and
downstream provisioning pipelines rely on; deviating from the
literal labels breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the
checklist (marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also
appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Monitor type selection | Per-query vs cluster-metrics vs per-document |
| Step 2 — Query definition (per-query monitor) | Search query design |
| Step 3 — Cluster metrics selection | JVM heap, CPU, disk |
| Step 4 — Trigger conditions | Threshold and anomaly detection |
| Step 5 — Anomaly detection (Random Cut Forest) | ML-based alerting |
| Step 6 — Actions and destinations | Slack, SNS, Chime, webhook |
| Step 7 — Notification message templating | Mustache templates |
| Step 8 — Scheduling (cron vs interval) | Monitor execution timing |
| Step 9 — Alert severity levels | 1 (high) to 5 (low) |
| Step 10 — Alert history and acknowledgment | Day-2 operations |
| Step 11 — Alerting dashboards | Observability |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/monitors-and-triggers.md | Monitor + trigger detail |
| references/destinations-and-actions.md | Destination + action detail |

## Mindset

**One-line takeaway:** A per-query monitor runs a search query at
scheduled intervals and evaluates trigger conditions on the results
— the cost scales with query complexity and frequency, so keep
queries efficient. The destination (Slack, SNS, Chime, webhook)
MUST be configured before the monitor references it. SNS actions
require the notification plugin (notification.yaml) to be
configured on the OpenSearch domain.

Three misconceptions dominate OpenSearch alerting misdesign at
provisioning time:

- **"Any monitor type works for any alerting need."** The three
  monitor types serve different purposes. A **per-query monitor**
  runs a search query and triggers on the results (e.g., error count
  > 100 in the last 5 minutes). A **cluster metrics monitor**
  checks OpenSearch cluster health metrics (JVM heap, CPU, disk
  usage) and triggers on threshold breaches. A **per-document
  monitor** extracts documents from query results and triggers per-
  document (useful for per-row alerting). Choosing the wrong type
  leads to either excessive cost (per-query for a cluster health
  check) or missed alerts (cluster metrics for a log-based
  condition).

- **"SNS notification works out of the box."** It does not. The SNS
  action requires the **notification plugin** (notification.yaml)
  to be configured on the OpenSearch domain with the SNS topic ARN
  and IAM role. Without the plugin, the SNS action silently fails
  (or errors at trigger time). Always verify the notification
  plugin configuration before relying on SNS actions.

- **"Monitor frequency has no cost impact."** A per-query monitor
  that runs every minute with a complex aggregation query places
  significant load on the cluster. The cost scales with query
  complexity (aggregations, large time ranges, multi-index searches)
  and frequency. Use the minimum frequency that meets the alerting
  SLA. For example, a 5-minute error count alert does not need a
  1-minute schedule.

## Configuration dependency graph (novel heuristic)

OpenSearch alerting configurations are NOT independent. The monitor
type determines the query/metrics interface. The destination MUST
exist before the monitor references it. The notification plugin
MUST be configured for SNS actions. Anomaly detection requires a
detectors resource. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Destination (Slack/SNS/Chime/webhook) | OpenSearch cluster reachable; SNS topic exists (for SNS); notification.yaml configured (for SNS) | destination credentials stored in OpenSearch keystore; cannot be read back after creation | action reference in monitors |
| Per-query monitor | OpenSearch cluster reachable; target index exists; destination exists (if action configured) | query runs at scheduled interval; complex queries consume cluster resources | threshold-based alerting on search results |
| Cluster metrics monitor | OpenSearch cluster reachable; destination exists | metrics polled from the cluster health API; no query overhead | cluster health alerting (JVM, CPU, disk) |
| Per-document monitor | OpenSearch cluster reachable; target index exists; destination exists | extracts documents from results; triggers per-document (one action per matching doc) | per-row alerting |
| Trigger condition (threshold) | Monitor exists; trigger expression valid | threshold evaluated after each monitor execution; invalid expressions fail silently at runtime | alert firing |
| Trigger condition (anomaly detection) | Anomaly detector exists and is running; monitor references detector by ID | detector must be trained before anomalies are detected; cold start delay | ML-based alerting |
| Action | Destination exists; message template valid (Mustache) | action fires when trigger condition is met; failed actions are retried up to 3 times | notification delivery |
| Schedule (cron or interval) | Monitor exists; schedule expression valid | cron expressions use UTC; invalid cron fails at monitor creation | monitor execution timing |
| Notification plugin (notification.yaml) | OpenSearch domain configuration; IAM role with SNS publish permission | plugin config is domain-level; affects ALL SNS actions on the domain | SNS action delivery |

**The destination-before-monitor row is the one a baseline model
misses.** A monitor that references a non-existent destination
fails at trigger time (not at creation time — the monitor creates
successfully, but the first alert delivery fails). The procedure
below forces destination verification before monitor creation.

**Cross-dependency gotchas:**
- SNS actions require the notification plugin configured at the
  domain level. A destination pointing to an SNS topic without the
  plugin will fail silently.
- Anomaly detection triggers require a trained detector. The
  detector must be created and running before the monitor references
  it. Cold start (training) can take 15+ minutes.
- Per-query monitor cost scales with query complexity and frequency.
  A complex aggregation running every minute on a large index can
  consume significant CPU and memory.
- Alert severity is a metadata field on the trigger, not an action
  routing mechanism. To route alerts by severity (e.g., page on
  severity 1, email on severity 5), use separate triggers with
  different actions.

## Expert heuristic: per-query monitor cost scales with query complexity

A baseline model says "create a monitor with a query." The correct
heuristic recognizes that the monitor runs the query at every
scheduled interval, and the cost depends on the query complexity.

```text
Per-query monitor cost factors:
  Query complexity:
    - Simple count (match_all + count)   → low cost
    - Aggregation (terms, avg, sum)      → medium cost
    - Multi-index, nested aggregation    → high cost
    - Large time range (24h window)      → high cost

  Frequency:
    - Every 1 min  → 1440 executions/day
    - Every 5 min  → 288 executions/day
    - Every 15 min → 96 executions/day

  BAD:  Complex aggregation every 1 min on 500 GB index → 1440 heavy/day
  GOOD: Rollup pre-aggregates; monitor queries rollup every 5 min → 288 light/day
```

**Key implication:** for expensive monitors, use OpenSearch rollups
or transforms to pre-aggregate data into a smaller index, then
monitor the rollup. This reduces query cost by 10-100x.

## Expert heuristic: destination must be configured before monitor

A baseline model creates the monitor and destination in any order.
The correct heuristic recognizes that the destination MUST exist
before the monitor references it, because the monitor validates
the destination ID at creation only for the API contract — but
the actual delivery happens at trigger time.

```text
Provisioning order:
  1. Configure notification plugin (notification.yaml) for SNS
     → domain-level config; required before SNS destinations work
  2. Create the destination (Slack webhook URL, SNS topic ARN,
     Chime webhook URL, custom webhook URL)
     → returns a destination ID
  3. Create the monitor referencing the destination ID
     → monitor creates successfully
  4. Test the destination (optional but recommended)
     → send a test notification to verify delivery
  5. Create the trigger with action referencing the destination
     → trigger fires the action when the condition is met
```

**Key implication:** if the destination does not exist or the
notification plugin is not configured for SNS, the monitor creates
successfully but the FIRST alert fails silently (logged in the
alerting plugin error log, not surfaced to the user).

## Expert heuristic: SNS action requires notification.yaml plugin

SNS is the most common destination for production alerting (it
fans out to email, SMS, Lambda, and other endpoints). But it
requires the notification plugin to be configured at the domain
level.

```text
SNS destination setup:
  1. Create an SNS topic (aws sns create-topic)
  2. Create an IAM role with sns:Publish permission for the topic
  3. Configure notification.yaml on the OpenSearch domain:
     plugin:
       notification:
         sns:
           role_arn: arn:aws:iam::<acct>:role/os-alerting-sns
           topic_arn: arn:aws:sns:<region>:<acct>:alert-topic
  4. Create the destination in OpenSearch pointing to the SNS topic
  5. Reference the destination in the monitor action

Without step 3, the SNS action fails at trigger time with
"notification plugin not configured."
```

**Key implication:** always verify the notification plugin is
configured before relying on SNS actions. For Slack/Chime/webhook
destinations, the plugin is not required (credentials are stored
in the destination config directly).

## Prerequisites (verify before provisioning)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| OpenSearch cluster reachable | Monitors and destinations require API access | `curl -s <endpoint>/_cluster/health` |
| Alerting plugin enabled | Default on managed OpenSearch | `curl <endpoint>/_plugins/_alerting/monitors` |
| Target index exists (per-query/per-document) | Monitor queries a specific index | `curl <endpoint>/<index-name>` |
| Destination configured | Monitor references destination by ID | `curl <endpoint>/_plugins/_alerting/destinations` |
| Notification plugin configured (for SNS) | SNS actions require notification.yaml | `curl <endpoint>/_plugins/_notifications/configs` |
| SNS topic + IAM role (for SNS) | OpenSearch assumes role to publish | `aws sns get-topic-attributes --topic-arn <arn>` |
| Anomaly detector running (for AD triggers) | AD triggers reference a trained detector | `curl <endpoint>/_plugins/_anomaly_detection/detectors/<id>` |
| Webhook URL valid (for webhook actions) | Destination stores the URL | Confirm URL accessible from cluster |

If any prerequisite is missing, output
`VERDICT: PREREQUISITES_MISSING` and cite the specific gap.

## Step 1 — Monitor type selection

| Monitor type | What it does | Use case | Cost |
|---|---|---|---|
| Per-query (`.monitor`) | Runs a search query at intervals; triggers on results | Error count > N, latency p99 > threshold | Scales with query complexity |
| Cluster metrics (`.monitor`) | Polls cluster health metrics; triggers on thresholds | JVM heap > 85%, CPU > 90%, disk > 80% | Low (metrics API) |
| Per-document (`.monitor`) | Extracts documents from query results; triggers per-doc | Per-row alerting (each error doc triggers) | Scales with result count |

**Choose per-query** for log/data-based alerting.
**Choose cluster metrics** for infrastructure health.
**Choose per-document** when each matching document needs a
separate alert (e.g., per-user error notification).

## Step 2 — Query definition (per-query monitor)

The query is a standard OpenSearch search body. The trigger
evaluates the query results.

```json
{
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
}
```

**Trigger evaluation:** the trigger condition references the
aggregation result (e.g., `ctx.results[0].aggregations.error_count.value > 100`).

**Query optimization:**
- Use `size: 0` when you only need aggregations (no document hits).
- Limit the time range to the minimum necessary (e.g., `now-5m`
  not `now-1h`).
- Avoid wildcard queries on large indices.
- Use rollup indices for pre-aggregated data.

## Step 3 — Cluster metrics selection

Cluster metrics monitors poll the OpenSearch cluster health API.

| Metric | API | Threshold |
|---|---|---|
| JVM heap | `_nodes/stats/jvm` | > 85% (GC pressure) |
| CPU | `_nodes/stats/process` | > 90% sustained |
| Disk | `_cat/allocation` | > 80% (low watermark) |
| Status | `_cluster/health` | `red` (immediate action) |
| Unassigned shards | `_cluster/health` | > 0 |
| Pending tasks | `_cluster/pending_tasks` | > 50 |

## Step 4 — Trigger conditions (threshold)

A trigger defines the condition that fires an alert. The condition
is a Painless expression evaluated on the monitor query results.

```json
{
  "trigger": {
    "name": "high-error-count",
    "severity": "1",
    "condition": {
      "script": {
        "source": "ctx.results[0].aggregations.error_count.value > params.threshold",
        "lang": "painless",
        "params": { "threshold": 100 }
      }
    },
    "actions": []
  }
}
```

**Severity mapping:**
| Severity | Label | Color |
|---|---|---|
| 1 | High | Red |
| 2 | Medium-high | Orange |
| 3 | Medium | Yellow |
| 4 | Low-medium | Light yellow |
| 5 | Low | Blue |

## Step 5 — Anomaly detection (Random Cut Forest)

Anomaly detection uses the Random Cut Forest (RCF) algorithm to
detect outliers in time-series data. The monitor references an
anomaly detector by ID.

**Setup flow:**
1. Create an anomaly detector (defines the index, feature, and
   detection interval).
2. Start the detector (begins training; cold start 15+ min).
3. Wait for the detector to be in `running` state.
4. Create a monitor that references the detector ID.
5. The trigger condition checks the anomaly grade or confidence.

```json
{
  "monitor_type": "monitor_composite",
  "anomaly_detector": {
    "detector_id": "<detector-id>"
  },
  "triggers": [{
    "name": "anomaly-detected",
    "severity": "2",
    "condition": {
      "script": {
        "source": "ctx.results[0].anomaly_grade > 0.9"
      }
    }
  }]
}
```

**Cold start:** RCF requires training data. The detector ingests
data for 15+ minutes before producing meaningful anomaly grades.
During cold start, anomaly_grade is 0.0 (no anomalies).

## Step 6 — Actions and destinations

Actions define what happens when a trigger fires. Each action
references a destination.

| Destination type | Setup | Notification plugin required? |
|---|---|---|
| Slack | Webhook URL stored in destination | No |
| Amazon SNS | SNS topic ARN; IAM role with sns:Publish | Yes (notification.yaml) |
| Amazon Chime | Webhook URL stored in destination | No |
| Custom webhook | URL + auth headers stored in destination | No |

**Create a destination (Slack example):**

```bash
curl -X POST "<endpoint>/_plugins/_alerting/destinations" \
  -H "Content-Type: application/json" \
  -u "<user>:<pass>" \
  -d '{
    "type": "slack",
    "name": "ops-alerts-slack",
    "slack": {
      "url": "https://hooks.slack.com/services/T000/B000/XXXXX"
    }
  }'
```

**Create a destination (SNS example):**

```bash
curl -X POST "<endpoint>/_plugins/_alerting/destinations" \
  -H "Content-Type: application/json" \
  -u "<user>:<pass>" \
  -d '{
    "type": "sns",
    "name": "ops-alerts-sns",
    "sns": {
      "topic_arn": "arn:aws:sns:us-east-1:123456789012:alert-topic"
    }
  }'
```

## Step 7 — Notification message templating

Action messages use Mustache templates with access to the monitor
context (`ctx`).

```json
{
  "action": {
    "name": "notify-slack",
    "destination_id": "<destination-id>",
    "message_template": {
      "source": "Alert: {{ctx.monitor.name}}\nSeverity: {{ctx.trigger.severity}}\nErrors: {{ctx.results[0].aggregations.error_count.value}}"
    }
  }
}
```

**Common ctx fields:** `ctx.monitor.name`, `ctx.trigger.name`,
`ctx.trigger.severity`, `ctx.results[0]` (query results),
`ctx.periodStart` / `ctx.periodEnd` (execution window),
`ctx.alert` (alert metadata).

## Step 8 — Scheduling (cron vs interval)

| Schedule type | Format | Use case |
|---|---|---|
| Interval | `{"period": {"interval": 5, "unit": "MINUTES"}}` | Simple recurring |
| Cron | `{"cron": {"expression": "0 */5 * * * ?", "timezone": "UTC"}}` | Complex (business hours, specific days) |

**Cron format:** 6 fields (second minute hour day-of-month month
day-of-week). Timezone defaults to UTC. Prefer interval for simple
frequency; use cron for business-hours-only alerting (e.g.,
`0 9-17 * * MON-FRI ?`).

## Step 9 — Alert severity levels

Severity is metadata on the trigger. It does NOT route alerts
automatically. To route by severity, create separate triggers with
different actions.

```text
Monitor: production-error-monitor
  Trigger 1: severity 1 (high), threshold > 1000
    → Action: SNS → Lambda → PagerDuty (page on-call)
  Trigger 2: severity 3 (medium), threshold > 100
    → Action: Slack #ops-alerts
  Trigger 3: severity 5 (low), threshold > 10
    → Action: Slack #ops-info
```

## Step 10 — Alert history and acknowledgment

Alerts are stored in the `.plugins-alerting-alerts` index. Each
alert has a state: `ACTIVE`, `ACKNOWLEDGED`, `COMPLETED`, `ERROR`.

**Acknowledge an alert:**

```bash
curl -X PUT "<endpoint>/_plugins/_alerting/acks/<alert-id>" \
  -u "<user>:<pass>"
```

Acknowledging an alert does NOT stop the monitor or suppress future
alerts — it marks the alert as `ACKNOWLEDGED` (the team is aware).
New alerts fire for subsequent condition breaches.

**View alert history:**

```bash
curl "<endpoint>/.plugins-alerting-alerts/_search?size=50&sort=start_time:desc" \
  -u "<user>:<pass>"
```

## Step 11 — Alerting dashboards

The OpenSearch Dashboards Alerting plugin provides a UI for viewing
active alerts, acknowledging alerts, viewing monitor execution
history, editing monitors (visual editor for simple monitors), and
viewing anomaly detection results.

**Access:** OpenSearch Dashboards → Alerting → Monitors / Alerts /
Destinations.

## Step 12 — Recent features

**Recent AWS features (2023-2026):**

- **Per-document monitor (2023-2024):** extracts documents from
  query results and triggers per-document. Useful for per-user or
  per-transaction alerting where each matching document needs a
  separate alert.

- **Anomaly detection with RCF improvements (2023-2024):** faster
  cold start (10 min) and improved multi-feature detector accuracy.

- **Notification template improvements (2023-2024):** Mustache
  templates now support conditional blocks and loops over
  aggregation buckets.

- **Composite monitors (2024-2025):** chains monitors together
  (monitor A triggers monitor B if A's condition is met). Useful
  for escalation workflows.

- **Serverless alerting (2024-2025):** OpenSearch Serverless now
  supports per-query monitors (cluster metrics monitors N/A since
  Serverless manages the cluster).

- **Terraform (2023-2024):** no native Terraform resources for
  alerting monitors; use the `curl` provider or local-exec.

## NEVER do these things

1. **NEVER create a monitor before the destination exists.** The
   monitor creates successfully but the first alert delivery fails
   silently. Always create and verify the destination first.

2. **NEVER use SNS actions without the notification plugin.** SNS
   actions require notification.yaml configured at the domain level.
   Without it, the action fails at trigger time.

3. **NEVER run complex aggregation queries every minute on large
   indices.** Per-query monitor cost scales with query complexity
   and frequency. Use rollups or transforms to pre-aggregate, and
   use the minimum frequency that meets the SLA.

4. **NEVER assume anomaly detection works immediately.** RCF
   requires a training period (cold start). The detector must be
   running and trained before anomalies are produced. Check the
   detector state before relying on AD triggers.

5. **NEVER use severity as a routing mechanism.** Severity is
   metadata only. To route by severity, create separate triggers
   with different actions.

6. **NEVER forget the timezone in cron expressions.** Cron defaults
   to UTC. Set the `timezone` field explicitly to avoid off-by-one
   scheduling.

7. **NEVER use `size > 0` in a per-query monitor that only needs
   aggregations.** Setting `size: 0` avoids fetching document hits,
   reducing query cost significantly.

8. **NEVER assume alert acknowledgment stops future alerts.**
   Acknowledging marks the alert but does NOT mute the trigger. New
   alerts fire for subsequent condition breaches.

9. **NEVER use a single monitor for fundamentally different
   conditions.** Create separate monitors per data source,
   severity, or team for easier triage.

10. **NEVER store webhook credentials in plain text in the monitor
    config.** Use the destination resource (keystore-backed) rather
    than inlining URLs.

## Output format

```text
OPENSEARCH_ALERTING: <monitor-name> (<monitor-type>) — <schedule>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Monitor type: per-query | cluster-metrics | per-document
  [✓|✗] Target index: <index-name> (for per-query/per-document)
  [✓|✗] Query: <summary> (for per-query)
  [✓|✗] Cluster metrics: <metric list> (for cluster-metrics)
  [✓|✗] Trigger: <trigger-name> — severity <n> — condition <expression>
  [✓|✗] Anomaly detector: <detector-id> — state <running|stopped> (if AD trigger)
  [✓|✗] Destination: <name> (<type>) — <destination-id>
  [✓|✗] Notification plugin: configured (for SNS) | N/A (for webhook)
  [✓|✗] Action: <action-name> → destination <destination-name>
  [✓|✗] Message template: <summary> (Mustache)
  [✓|✗] Schedule: every <n> <unit> | cron <expression> (<timezone>)
  [✓|✗] Alert severity: <n> (<label>)
  [✓|✗] Alert acknowledgment: enabled (UI/API)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  curl <endpoint>/_plugins/_alerting/monitors/<monitor-id>
  curl <endpoint>/_plugins/_alerting/destinations/<destination-id>
  curl <endpoint>/.plugins-alerting-alerts/_search?size=5&sort=start_time:desc
```

### Worked example — per-query error monitor with Slack notification

```text
OPENSEARCH_ALERTING: error-count-monitor (per-query) — every 5 minutes
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Monitor type: per-query
  [✓] Target index: application-logs-*
  [✓] Query: match level=error, range @timestamp >= now-5m, aggregate value_count
  [✓] Trigger: high-error-count — severity 1 — condition error_count > 100
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

## Error handling

### Monitor creates but alerts never fire
- The trigger condition may never be met. Test the query manually
  in the OpenSearch DevTools console and verify it returns results
  satisfying the condition.

### Action fails at trigger time (SNS)
- The notification plugin (notification.yaml) is not configured at
  the domain level. Configure it with the SNS topic ARN and IAM
  role. Restart the alerting plugin if needed.

### Action fails at trigger time (webhook)
- The webhook URL is invalid or unreachable from the cluster.
  Verify network ACLs, security groups, and firewall rules.

### Anomaly detection produces no anomalies
- The detector may still be in cold start (training). Wait 15+
  minutes for training. Verify the detector is ingesting data by
  checking `last_update_time`.

### Alert storm (fires too frequently)
- Threshold too low or schedule too frequent. Increase threshold,
  reduce frequency, or add a deduplication window. Acknowledge
  active alerts via the `acks` API.

### Monitor execution is slow (cluster impact)
- Query too complex for schedule frequency. Use rollups or
  transforms to pre-aggregate. Increase the interval. Reduce the
  query time range.

## Domain

AWS CloudOps / Amazon OpenSearch Service Alerting & Operational Monitoring.

## AWS documentation

- **OpenSearch Alerting Plugin** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/alerting.html
- **Alerting API** — https://opensearch.org/docs/latest/observing-your-data/alerting/api/
- **Monitors and triggers** — https://opensearch.org/docs/latest/observing-your-data/alerting/monitors/
- **Destinations and actions** — https://opensearch.org/docs/latest/observing-your-data/alerting/destinations/
- **Anomaly detection** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ad.html
- **Notification plugin** — https://opensearch.org/docs/latest/observing-your-data/notifications/
- **Alert acknowledgment** — https://opensearch.org/docs/latest/observing-your-data/alerting/alerts/
- **Cron expressions** — https://opensearch.org/docs/latest/observing-your-data/alerting/monitors/#cron-expressions
