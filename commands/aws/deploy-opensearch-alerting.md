---
description: Provision an Amazon OpenSearch Service alerting configuration with production-grade defaults (per-query / cluster-metrics / per-document monitors, threshold and anomaly detection triggers, Slack/SNS/Chime/webhook destinations, notification.yaml for SNS, Mustache message templating, cron/interval scheduling, severity levels, alert acknowledgment). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create opensearch monitor"
  - "deploy opensearch alerting"
  - "opensearch alerting"
  - "opensearch monitor"
  - "opensearch trigger"
  - "opensearch anomaly detection alert"
  - "opensearch alert destination"
  - "opensearch sns notification"
  - "opensearch slack alert"
  - "opensearch chime alert"
  - "opensearch webhook alert"
  - "opensearch per-query monitor"
  - "opensearch cluster metrics monitor"
  - "opensearch per-document monitor"
  - "opensearch alert severity"
  - "opensearch acknowledge alert"
  - "opensearch cron schedule"
routes_to: opensearch-alerting-deployer
---

# /aws:deploy-opensearch-alerting

Activate the `opensearch-alerting-deployer` skill and provision an
Amazon OpenSearch Service alerting configuration with production-
grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Monitor type selection (per-query, cluster-metrics, per-document)
2. Query definition (per-query monitor) with size:0 optimization
3. Cluster metrics selection (JVM heap, CPU, disk)
4. Trigger conditions (threshold, Painless scripts)
5. Anomaly detection (Random Cut Forest) triggers
6. Actions and destinations (Slack, SNS, Chime, custom webhook)
7. Notification message templating (Mustache)
8. Scheduling (cron vs interval)
9. Alert severity levels (1=high to 5=low)
10. Alert history and acknowledgment
11. Alerting dashboards

## When to use

- You need to create an OpenSearch alerting monitor.
- You are configuring a trigger on a query threshold.
- You are setting up anomaly detection alerts.
- You need to add a Slack, SNS, Chime, or webhook notification.
- You need to schedule a monitor with cron or interval.
- You need to configure alert severity levels.

## When NOT to use

- **OpenSearch domain provisioning** — use opensearch-domain-deployer.
- **Index creation** — use opensearch-index-deployer.
- **Cluster troubleshooting** — use opensearch-cluster-troubleshooter.
- **Serverless collection setup** — use opensearch-serverless-deployer.

## How to invoke

### Slash command

```
/aws:deploy-opensearch-alerting
```

Then provide: cluster endpoint, monitor type, target index (for
per-query/per-document), query/metrics, trigger condition and
severity, destination name, schedule, tags.

### Natural language

Any of these routes to the same skill:

- "create an OpenSearch error count monitor"
- "set up anomaly detection alerts on my cluster"
- "configure a Slack notification for OpenSearch alerts"
- "create a cluster metrics monitor for JVM heap"
- "schedule an OpenSearch monitor with cron"

### CLI routing

```bash
node cli/bin/cli.js route "create an opensearch alerting monitor"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create
OpenSearch alerting monitors. The output checklist feeds into
verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-opensearch-alerting

     Create an OpenSearch error count monitor on
     search-prod.example.com. Alert on > 100 errors in 5 minutes.
     Notify Slack destination ops-alerts-slack. Schedule every
     5 minutes. Severity 1.

Skill:
  OPENSEARCH_ALERTING: error-count-monitor (per-query) — every 5 minutes
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Monitor type: per-query
    [✓] Query: match level=error, range now-5m, aggregate value_count
    [✓] Trigger: high-error-count — severity 1 — error_count > 100
    [✓] Destination: ops-alerts-slack (slack)
    [✓] Schedule: every 5 MINUTES
    [✓] Alert severity: 1 (high)
  VERIFICATION_COMMANDS:
    curl <endpoint>/_plugins/_alerting/monitors/<monitor-id>
    curl <endpoint>/_plugins/_alerting/destinations/<destination-id>
```

## References

- Skill definition: `skills/opensearch-alerting-deployer/SKILL.md`
- Monitors and triggers guide: `skills/opensearch-alerting-deployer/references/monitors-and-triggers.md`
- Destinations and actions guide: `skills/opensearch-alerting-deployer/references/destinations-and-actions.md`
- Eval suite: `skills/opensearch-alerting-deployer/evals/evals.json`
