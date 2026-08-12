---
description: Provision an Amazon Managed Grafana workspace with production-grade defaults (workspace creation, SAML/SSO or IAM Identity Center authentication, data source configuration with per-service IAM permissions, workspace API key, dashboard provisioning, notification channels). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create grafana workspace"
  - "grafana data source"
  - "grafana cloudwatch data source"
  - "grafana prometheus data source"
  - "grafana athena data source"
  - "grafana timestream data source"
  - "grafana opensearch data source"
  - "grafana x-ray data source"
  - "grafana saml sso"
  - "grafana workspace api key"
  - "grafana dashboard provisioning"
  - "managed grafana"
  - "grafana iam role"
routes_to: grafana-data-source-deployer
---

# /aws:deploy-grafana-data-source

Activate the `grafana-data-source-deployer` skill and provision an
Amazon Managed Grafana workspace with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Workspace creation (name, auth provider, permission type)
2. Authentication (SAML SSO or IAM Identity Center)
3. Workspace IAM role with per-service read permissions
4. Data source configuration (CloudWatch, Prometheus/AMP, Athena,
   Timestream, OpenSearch, X-Ray)
5. Workspace API key creation
6. Dashboard provisioning (JSON import/export)
7. User and group management
8. Notification channels
9. Plugin management
10. Version control integration

## When to use

- You need to create a Managed Grafana workspace.
- You need to configure data sources (CloudWatch, Prometheus, Athena,
  Timestream, OpenSearch, X-Ray).
- You need to set up SAML SSO with an external IdP.
- You need to provision dashboards programmatically.
- You need to create workspace API keys.
- You need to configure notification channels for alerting.
- You need to manage workspace users and groups.

## When NOT to use

- **Self-hosted Grafana** — for EC2/ECS Grafana deployments.
- **CloudWatch dashboards** — for native AWS CloudWatch dashboards.
- **Amazon QuickSight** — for BI/reporting use cases.

## How to invoke

### Slash command

```
/aws:deploy-grafana-data-source
```

Then provide: workspace name, authentication method, data source
list, IAM role name, IdP details (if SAML), API key requirements,
dashboard files, notification channel config, tags.

### Natural language

Any of these routes to the same skill:

- "create a managed grafana workspace with cloudwatch"
- "set up grafana with prometheus data source"
- "configure grafana saml sso"
- "create a grafana workspace api key"
- "provision dashboards in grafana"

### CLI routing

```bash
node cli/bin/cli.js route "create a grafana workspace"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create Grafana
workspaces or configure data sources. The output checklist feeds into
verification pipelines and downstream observability skills.

## Example

```
You: /aws:deploy-grafana-data-source

     Create a Grafana workspace named prod-observability with
     CloudWatch data source. Use IAM Identity Center. Region
     us-east-1.

Skill:
  GRAFANA: g-aaaa1111 (prod-observability, AWS_SSO)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Authentication: AWS_SSO (IAM Identity Center)
    [✓] Workspace IAM role: GrafanaWorkspaceRole — attached
    [✓] CloudWatch permissions: cloudwatch:GetMetricData
    [✓] Data sources: CloudWatch (default)
    [✓] Workspace endpoint: https://g-aaaa1111.grafana-workspace.us-east-1.amazonaws.com
  VERIFICATION_COMMANDS:
    aws grafana describe-workspace --workspace-id <id> --region us-east-1
```

## References

- Skill definition: `skills/grafana-data-source-deployer/SKILL.md`
- Data sources and IAM guide: `skills/grafana-data-source-deployer/references/data-sources-and-iam.md`
- Authentication and access guide: `skills/grafana-data-source-deployer/references/authentication-and-access.md`
- Eval suite: `skills/grafana-data-source-deployer/evals/evals.json`
