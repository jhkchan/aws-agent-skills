# Eval: prometheus-amp-data-source

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Prometheus AMP data source, SigV4 auth with workspace role, aps:QueryMetrics permission

## Prompt

Create a Managed Grafana workspace named amp-observability
in us-east-1. Use IAM Identity Center authentication. Data source:
Prometheus connected to AMP workspace ws-aaa111. Workspace IAM
role GrafanaWorkspaceRole with aps:QueryMetrics and
aps:ListWorkspaces permissions. SigV4 authentication using
workspace IAM role. Tags: Environment=production, Source=amp.
