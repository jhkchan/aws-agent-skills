---
description: Provision an Amazon QuickSight dashboard with production-grade defaults (account edition, data source, SPICE vs Direct Query dataset, analysis, dashboard sharing, template-based multi-tenant deployment, row-level security, VPC connection, IAM role, user provisioning, refresh schedule, parameters). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create quicksight dashboard"
  - "deploy quicksight dashboard"
  - "quicksight data source"
  - "quicksight spice"
  - "quicksight template"
  - "quicksight row-level security"
  - "quicksight rls"
  - "quicksight vpc connection"
  - "quicksight user provisioning"
  - "quicksight enterprise"
  - "quicksight multi-tenant"
  - "quicksight dashboard"
  - "quicksight analysis"
routes_to: quicksight-dashboard-deployer
---

# /aws:deploy-quicksight-dashboard

Activate the `quicksight-dashboard-deployer` skill and provision an
Amazon QuickSight dashboard with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Account creation and edition (Standard/Enterprise)
2. Data source connection (Athena, RDS, Redshift, S3, Aurora)
3. Dataset (SQL/custom query, join, calculated field)
4. SPICE vs Direct Query decision
5. Analysis and dashboard creation
6. Template-based multi-tenant deployment
7. Row-level security (RLS)
8. VPC connection and IAM role
9. User provisioning, namespaces, groups
10. Refresh schedule and parameters

## When to use

- You need to create a QuickSight dashboard.
- You are connecting QuickSight to a data source (Athena, RDS, etc.).
- You need to decide between SPICE and Direct Query.
- You need row-level security for dashboard data.
- You are deploying template-based multi-tenant dashboards.
- You need a VPC connection for private data stores.
- You need to provision QuickSight users and groups.

## When NOT to use

- **Amazon Athena workgroup management** — use Athena skills.
- **Redshift cluster provisioning** — use Redshift skills.
- **General BI tool comparisons** — not a provisioning task.
- **Auditing existing QuickSight resources** — use QuickSight audit skills.

## How to invoke

### Slash command

```
/aws:deploy-quicksight-dashboard
```

Then provide: QuickSight account ID, edition (Standard/Enterprise),
data source type and connection details, dataset name and query mode
(SPICE/Direct Query), analysis and dashboard name, RLS requirements,
template requirements (if multi-tenant), VPC connection details (if
private source), user emails for sharing, refresh schedule, tags.

### Natural language

Any of these routes to the same skill:

- "create a QuickSight dashboard backed by Athena"
- "set up SPICE ingestion for my QuickSight dataset"
- "deploy a multi-tenant QuickSight dashboard from a template"
- "enable row-level security on my QuickSight dataset"
- "connect QuickSight to a private RDS instance via VPC connection"

### CLI routing

```bash
node cli/bin/cli.js route "create a quicksight dashboard"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create QuickSight
dashboards. The output checklist feeds into verification pipelines and
downstream audit skills.

## Example

```
You: /aws:deploy-quicksight-dashboard

     Create a QuickSight Enterprise dashboard backed by Athena
     with SPICE, hourly refresh, and row-level security by region.
     Account 123456789012, us-east-1.

Skill:
  QUICKSIGHT_DASHBOARD: sales-dashboard (version 1)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Data source: ds-athena-prod (type: Athena)
    [✓] Dataset: ds-sales-metrics (mode: SPICE)
    [✓] SPICE refresh schedule: HOURLY
    [✓] Row-level security: ENABLED
  VERIFICATION_COMMANDS:
    aws quicksight describe-dashboard --aws-account-id 123456789012 --dashboard-id sales-dashboard --region us-east-1
```

## References

- Skill definition: `skills/quicksight-dashboard-deployer/SKILL.md`
- SPICE and ingestion guide: `skills/quicksight-dashboard-deployer/references/spice-and-ingestion.md`
- Templates and RLS guide: `skills/quicksight-dashboard-deployer/references/templates-and-rls.md`
- Eval suite: `skills/quicksight-dashboard-deployer/evals/evals.json`
