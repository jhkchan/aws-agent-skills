# Eval: enterprise-incident-oncall

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Enterprise tier, SAML team sync, Incident, OnCall, 5 data sources

## Prompt

Create an Amazon Managed Grafana Enterprise workspace in us-east-1 for
enterprise observability. Workspace name "enterprise-obs". SAML
authentication with team sync from the corporate IdP. Permission type
CUSTOMER_MANAGED. Data sources: CloudWatch, AMP (workspace ws-prod-metrics,
ACTIVE), Timestream, OpenSearch (domain prod-logs), X-Ray. Grafana
version 11.0. Enable Grafana Incident for real-time incident declaration
and tracking. Enable Grafana OnCall for escalation schedule management
with integration to Slack channel #oncall-platform. IAM role
"GrafanaEnterpriseRole" with read access to all data source types.
Dashboard suite: executive overview, service health, incident response.
Alerting with escalation policy: severity=critical pages on-call
immediately, severity=warning notifies Slack channel. Tags:
Environment=production, Workload=enterprise-observability, Tier=enterprise.
Account ID: 123456789012.
