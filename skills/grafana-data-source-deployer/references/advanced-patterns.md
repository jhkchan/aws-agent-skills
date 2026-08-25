# Advanced Patterns — Grafana Data Source Deployer

Load-on-demand detail moved verbatim from SKILL.md.

## Step 7 — Version control integration — moved from SKILL.md

Grafana Enterprise supports Git-based dashboard provisioning:

```bash
aws grafana update-workspace-configuration \
  --workspace-id "$WORKSPACE_ID" \
  --configuration '{"versionControl":{"provider":"github","repository":"my-org/grafana-dashboards","branch":"main","directory":"/dashboards"}}' \
  --region us-east-1
```

## Step 8 — Recent features — moved from SKILL.md

- **Grafana Enterprise features (2023-2024):** Enhanced RBAC, data
  source permissions, reporting, audit logs, and SAML team sync.
- **Native SNS notification channel (2023-2024):** Direct SNS
  integration for alert notifications.
- **AMP auto-discovery (2023-2024):** Streamlined Prometheus data
  source creation that auto-discovers AMP workspaces.
- **CloudWatch Logs Insights (2024-2025):** Enhanced Logs query syntax
  support in Grafana panels.
- **Workspace configuration API (2024-2025):** Network access
  controls and enterprise settings without recreating the workspace.
- **Terraform provider (2023-2024):** Full support for workspace, API
  key, role association, and permission resources.
