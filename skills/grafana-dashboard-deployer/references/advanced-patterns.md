# Advanced Patterns — Grafana Dashboard Deployer

Load-on-demand detail moved verbatim from SKILL.md.

## Step 7 — Grafana Enterprise features (Incident, OnCall) — moved from SKILL.md

**Grafana Incident** (Enterprise):
- Real-time incident declaration and tracking
- Integrated with Grafana dashboards and alerting
- Post-incident timeline and root-cause analysis

**Grafana OnCall** (Enterprise):
- On-call schedule management
- Escalation policies (PagerDuty-like)
- Integration with Slack, Telegram, phone calls

**Enabling Enterprise features:**
Enterprise features require a Grafana Enterprise workspace. Upgrade from
Standard via AWS support or create a new Enterprise workspace:

```bash
aws grafana create-workspace \
  --workspace-name <workspace-name>-enterprise \
  --account-access-type CURRENT_ACCOUNT \
  --authentication-providers AWS_SSO \
  --permission-type CUSTOMER_MANAGED \
  --data-sources CLOUDWATCH PROMETHEUS XRAY \
  --grafana-version 11.0 \
  --workspace-data-sources CLOUDWATCH PROMETHEUS XRAY \
  --network-access-control-configuration '{...}' \
  --description "Enterprise observability with Incident and OnCall"
```

**Enterprise SAML team sync:** maps IdP groups to Grafana teams
automatically. Configure in the workspace SAML settings with group
attribute statements from the IdP.

## Recent AWS features (2024-2026) — moved from SKILL.md

- **Grafana version 11.x support (2025):** Managed Grafana supports
  Grafana 11.x with new panel types, improved alerting UI, and canvas
  panels. Provisioning tip: specify `--grafana-version 11.0` at workspace
  creation; version upgrades are managed by AWS.

- **Grafana Enterprise on AWS (2024-2025):** Enterprise tier with
  Incident (real-time incident management), OnCall (escalation schedules),
  reporting (scheduled PDF reports), SAML team sync, and audit logs.
  Provisioning tip: Enterprise requires a separate license; create as
  Enterprise workspace or upgrade via AWS support.

- **AMP cross-account observability (2024):** AMP workspaces can ingest
  metrics from multiple accounts via cross-account IAM roles. Provisioning
  tip: configure the remote write source with a cross-account role that
  has `aps:RemoteWrite` on the central AMP workspace.

- **Grafana data source for AWS IoT SiteWise (2024):** Managed Grafana
  supports IoT SiteWise as a data source for industrial asset metrics.
  Provisioning tip: add `IOTSITEWISE` to `--data-sources` at workspace
  creation.

- **Grafana workspace API key automation (2024-2025):** Programmatic
  API key creation for CI/CD dashboard deployment. Provisioning tip:
  use short-lived keys (`--seconds-to-live 3600`) for deployment pipelines;
  rotate regularly.

- **Grafana alerting with SNS integration (2024):** Native SNS contact
  point type for Grafana-managed alerting. Provisioning tip: configure
  the SNS contact point with `authProvider: aws_iam` and the Grafana
  workspace IAM role must have `sns:Publish` on the topic.

- **Managed Grafana VPC configuration (2024):** Workspaces can be
  deployed within a VPC for private data source access. Provisioning
  tip: specify `--network-access-control-configuration` with VPC subnets
  and security groups at creation.
