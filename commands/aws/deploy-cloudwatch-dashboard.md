---
description: Provision CloudWatch dashboards with production-grade widget layouts, metric selections, and sharing models. Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create cloudwatch dashboard"
  - "provision dashboard"
  - "deploy dashboard"
  - "metric widget dashboard"
  - "log insights dashboard"
  - "alarm widget dashboard"
  - "metric math dashboard"
  - "custom metrics dashboard"
  - "cross-account dashboard"
  - "shared dashboard"
  - "snapshot sharing dashboard"
  - "dashboard variables"
  - "SLO dashboard"
  - "operational dashboard"
  - "executive dashboard"
  - "metric explorer dashboard"
  - "application signals dashboard"
  - "cloudwatch put-dashboard"
  - "embedded metrics format dashboard"
routes_to: cloudwatch-dashboard-deployer
---

# /aws:deploy-cloudwatch-dashboard

Activate the `cloudwatch-dashboard-deployer` skill and provision a
CloudWatch dashboard with production-grade widget layouts, metric
selections, and sharing models.

## What it does

The skill walks a pre-check gate and emits a READY_TO_DEPLOY checklist:

1. Dashboard JSON structure validation (widgets, layout, positions)
2. Metric widget verification (namespace, dimensions, statistic, period)
3. Log insights widget verification (log group existence, query syntax)
4. Alarm widget verification (alarm ARN resolution)
5. Text widget validation (Markdown syntax)
6. Metric math expression validation (m-ID / e-ID conventions)
7. Dashboard variable configuration ($INSTANCE_ID, etc.)
8. Cross-account sharing role verification
9. Snapshot sharing configuration
10. Application Signals / Metric Explorer integration

## When to use

- You need to create a new CloudWatch dashboard with production defaults.
- You are designing an operational, SLO, or executive dashboard layout.
- You need cross-account or cross-region dashboard sharing.
- You need to add log insights widgets to a dashboard.
- You want to use metric math expressions combining multiple metrics.
- You need to validate that dashboard widgets render correctly.
- You need copy-pasteable put-dashboard commands.

## How to invoke

### Slash command

```
/aws:deploy-cloudwatch-dashboard
```

Then provide: dashboard name, region, widget specifications (type,
namespace, metric, dimensions, statistic, period, position), sharing
model (single-account / cross-account / snapshot), and any optional
features (dashboard variables, Application Signals SLO, auto-refresh).

### Natural language

Any of these routes to the same skill:

- "create a production CloudWatch dashboard"
- "deploy an operational dashboard for EC2"
- "build an SLO burn-rate dashboard"
- "set up a cross-account shared dashboard"
- "add log insights widgets to my dashboard"

### CLI routing

```bash
node cli/bin/cli.js route "create a cloudwatch dashboard"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or update
CloudWatch dashboards. The output checklist feeds into verification
pipelines and audit skills (cloudwatch-alarm-auditor for post-deploy
dashboard alarm widget audit).

## Example

```
You: /aws:deploy-cloudwatch-dashboard

     Create a production operational dashboard "prod-ec2-ops" in
     us-east-1 with CPU (AWS/EC2 CPUUtilization), Memory (CWAgent
     mem_used_percent), and Network (metric math NetworkIn+NetworkOut)
     widgets. Use dashboard variable INSTANCE_ID. Account: 111111111111.

Skill:
  DASHBOARD: prod-ec2-ops
  VERDICT: READY_TO_DEPLOY
  TARGET: prod-ec2-ops
  PRE_CHECKS:
    [PASS] DashboardBody valid JSON, 3 widgets, 0 overlaps
    [PASS] Widget 1: AWS/EC2 CPUUtilization returns datapoints
    [PASS] Widget 2: CWAgent mem_used_percent returns datapoints
    [PASS] Widget 3: metric math valid (NetworkIn + NetworkOut)
    [PASS] Dashboard variable INSTANCE_ID maps to valid dimension
    [PASS] 3 widgets <= 100 cap
  WIDGETS: 3 (3 metric, 0 log, 0 alarm, 0 text)
  SHARING: single-account
```

## References

- Skill definition: `skills/cloudwatch-dashboard-deployer/SKILL.md`
- Widget patterns reference: `skills/cloudwatch-dashboard-deployer/references/dashboard-widget-patterns.md`
- Eval suite: `skills/cloudwatch-dashboard-deployer/evals/evals.json`
