---
description: Deploy an Amazon Managed Grafana workspace and dashboards with production defaults (IAM Identity Center auth, CloudWatch/AMP/Timestream/OpenSearch/X-Ray data sources, customer-managed IAM role, dashboard JSON, alerting). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create grafana workspace"
  - "deploy grafana dashboard"
  - "grafana data source"
  - "grafana cloudwatch"
  - "grafana prometheus"
  - "grafana amp"
  - "grafana timestream"
  - "grafana opensearch"
  - "grafana x-ray"
  - "grafana alerting"
  - "grafana notification policy"
  - "grafana contact point"
  - "grafana enterprise"
  - "grafana incident"
  - "grafana oncall"
  - "grafana iam role"
routes_to: grafana-dashboard-deployer
---

# /aws:deploy-grafana-dashboard

Activate the `grafana-dashboard-deployer` skill and provision an Amazon
Managed Grafana workspace with production-grade defaults.

## What it does

The skill walks a 10-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Workspace creation + authentication (IAM Identity Center or SAML)
2. IAM role for data source access (service-managed or customer-managed)
3. Data source configuration (CloudWatch, AMP, Timestream, OpenSearch, X-Ray)
4. Dashboard JSON model (panels, templating variables, time range)
5. Alerting (rules, notification policies, contact points)
6. AMP workspace integration (Prometheus remote write + Grafana query)
7. Grafana Enterprise features (Incident, OnCall, reporting, SAML team sync)

## When to use

- You need to create a Managed Grafana workspace.
- You want to configure data sources (CloudWatch, AMP, Timestream, OpenSearch, X-Ray).
- You need to build dashboards with templating variables and panels.
- You want to set up alerting rules with notification routing.
- You want to integrate AMP/Prometheus with Grafana.
- You want to adopt Grafana Enterprise (Incident, OnCall).

## How to invoke

### Slash command

```
/aws:deploy-grafana-dashboard
```

Then provide: workspace name, authentication mode, data source types,
permission type, Grafana version, dashboard requirements, and any
optional features (AMP workspace ID, alerting rules, Enterprise tier).

### Natural language

Any of these routes to the same skill:

- "create a Managed Grafana workspace"
- "set up Grafana with CloudWatch and AMP"
- "configure Grafana alerting with SNS"
- "deploy a Grafana Enterprise workspace with Incident"
- "integrate AMP Prometheus with Grafana"

### CLI routing

```bash
node cli/bin/cli.js route "create a grafana workspace"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline. The
orchestrator routes to it when the user wants to create or configure a
Managed Grafana workspace. The output checklist feeds into verification
pipelines and audit skills.

## Example

```
You: /aws:deploy-grafana-dashboard

     Create a Grafana workspace "prod-observability" in us-east-1.
     IAM Identity Center auth. Customer-managed IAM role with CloudWatch
     read. CloudWatch data source for us-east-1, us-west-2. Grafana 10.4.
     Dashboard with 12 panels for EC2/Lambda/RDS. Alert on CPU > 85%
     with SNS. Account: 123456789012.

Skill:
  WORKSPACE: prod-observability
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Authentication: AWS_SSO (IAM Identity Center)
    [✓] Permission type: CUSTOMER_MANAGED
    [✓] IAM role: GrafanaDataSourceRole (CloudWatch read)
    [✓] Data source: CloudWatch (us-east-1, us-west-2)
    [✓] Dashboard: Production Observability (12 panels)
    [✓] Alert rules: CPU > 85%, Lambda errors > 5
    [✓] Contact points: SNS grafana-alerts
  VERIFICATION_COMMANDS:
    aws grafana describe-workspace --workspace-id <id>
    aws iam get-role --role-name GrafanaDataSourceRole
```

## References

- Skill definition: `skills/grafana-dashboard-deployer/SKILL.md`
- Provisioning CLI commands: `skills/grafana-dashboard-deployer/references/provisioning-cli-commands.md`
- Data sources and dashboard JSON: `skills/grafana-dashboard-deployer/references/data-sources-and-dashboard-json.md`
- Eval suite: `skills/grafana-dashboard-deployer/evals/evals.json`
