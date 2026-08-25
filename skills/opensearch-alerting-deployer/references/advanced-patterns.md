# Advanced patterns — opensearch-alerting-deployer

Configuration dependency graph, per-query monitor cost heuristic, and recent AWS features, moved verbatim from SKILL.md (load on demand).

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

## Recent AWS features (2023-2026)

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
