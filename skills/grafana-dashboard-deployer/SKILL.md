---
name: grafana-dashboard-deployer
description: 'Provisions Amazon Managed Grafana workspaces and dashboards with production defaults: workspace creation (authentication via SSO or IAM Identity Center), data sources (CloudWatch, Prometheus/AMP, Timestream, OpenSearch, X-Ray), dashboard JSON model (panels, templating variables, time range), alerting (alert rules, notification policies, contact points), IAM role for data source access, AMP workspace integration, and latest features (Grafana Enterprise, Incident, OnCall). Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Grafana workspace, adding data sources, building dashboards, configuring alerting, or integrating AMP. Triggers: create Grafana workspace, Grafana dashboard, Grafana data source, Grafana alerting, AMP integration, Grafana Enterprise, Grafana Incident.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with grafana, amps, iam, ec2, cloudwatch, timestream, opensearch, and xray access. Works with Terraform aws_grafana_workspace / aws_grafana_workspace_api_key / aws_prometheus_workspace resources and CloudFormation AWS::Grafana::Workspace templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  when_to_use: Invoke when the user wants to create an Amazon Managed Grafana workspace, configure data sources (CloudWatch, AMP, Timestream, OpenSearch, X-Ray), build dashboard JSON models with panels and templating variables, set up alerting rules and notification policies, integrate AMP workspaces, or adopt Grafana Enterprise features (Incident, OnCall). Do NOT invoke for self-managed Grafana on EC2/EKS, Prometheus configuration, or CloudWatch dashboard creation (use deploy-cloudwatch-dashboard).
  activation_triggers: create grafana workspace, deploy grafana dashboard, grafana data source, grafana cloudwatch, grafana prometheus, grafana amp, grafana timestream, grafana opensearch, grafana x-ray, grafana alerting, grafana notification policy, grafana contact point, grafana enterprise, grafana incident, grafana oncall, grafana iam role
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: aws, grafana, dashboard, managed grafana, deploy, cloudops, observability, data source, cloudwatch, prometheus, amp, timestream, opensearch, x-ray, alerting, notification, iam identity center, sso, grafana enterprise, grafana incident, grafana oncall
  tags: aws, grafana, observability, deploy, management, dashboard, cloudwatch, prometheus, alerting, amp
  dependencies: aws-orchestrator
---

# Grafana Dashboard Deployer

## What this skill does

Provisions Amazon Managed Grafana workspaces and dashboards with
production-grade defaults across five core domains: workspace creation
with authentication (SSO/IAM Identity Center), data source integration
(CloudWatch, AMP/Prometheus, Timestream, OpenSearch, X-Ray), dashboard
JSON model design (panels, templating, time range), alerting (rules,
notification policies, contact points), and IAM role configuration for
data source access. Emits a READY_TO_DEPLOY checklist with
copy-pasteable verification commands.

## Activation keywords

create Grafana workspace, Grafana dashboard, Grafana data source,
CloudWatch data source, Prometheus data source, AMP workspace, Timestream
data source, OpenSearch data source, X-Ray data source, Grafana alerting,
alert rules, notification policy, contact point, IAM Identity Center,
SSO authentication, Grafana Enterprise, Grafana Incident, Grafana OnCall,
IAM role for Grafana, workspace API key, service managed IAM role.

## Invocation contract (hard requirement)

When this skill is invoked with a Grafana-provisioning request (workspace
name, authentication mode, data sources, dashboard requirements, or a
partial configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the section "Output format" using the literal
all-caps labels `WORKSPACE:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

## Mindset

**One-line takeaway:** an Amazon Managed Grafana workspace is not just
"Grafana on AWS" — it is a **managed integration boundary** where the
authentication mode (IAM Identity Center vs SAML), the data source IAM
role (service-managed vs customer-managed), and the Grafana version
(Standard vs Enterprise) are decided at workspace creation and cannot
all be changed in place.

Three misconceptions dominate Grafana workspace misdesign at provisioning
time:

- **"I can switch authentication modes after creation."** The
  authentication mode is set at workspace creation via
  `authenticationProviders`. Switching from SAML to IAM Identity Center
  (or vice versa) requires recreating the workspace. Plan the
  authentication strategy before calling `create-workspace`.

- **"Data sources just need a URL — IAM handles the rest."** Managed
  Grafana data sources require either a **service-managed IAM role**
  (Grafana creates and manages it) or a **customer-managed IAM role**
  with specific read permissions for each data source service
  (CloudWatch, AMP, Timestream, etc.). Without the correct IAM role
  permissions, data sources return permission errors on every query.

- **"Alerting is just Grafana's built-in alert manager."** Managed
  Grafana alerting has three layers that must all be configured: alert
  rules (the condition), notification policies (the routing), and
  contact points (the destination). Missing any layer means alerts fire
  but go nowhere, or contact points exist but nothing routes to them.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Deployment checklist + workspace decision gate | Before any deployment |
| **§ Mindset** | Authentication immutability, IAM role gap, alerting layers | Understanding the model |
| **§ Prerequisites** | IAM Identity Center, AMP workspace, VPC, data source roles | Before producing the plan |
| **§ Workspace selection** | Standard vs Enterprise decision matrix | Choosing the right tier |
| **§ Provisioning procedure** | 10-step deploy: workspace, auth, data sources, dashboard, alerting, IAM, AMP, Enterprise | When building the deploy plan |
| **§ Common patterns** | Boilerplate for workspace, CloudWatch, AMP, dashboard JSON, alerting | Boilerplate lookup |
| **§ Output format** | Structured output template with VERDICT, CHECKLIST, VERIFICATION_COMMANDS | Formatting the response |
| **§ STRICT output contract** | Required structure + FORBIDDEN patterns | Validating the output |
| **§ NEVER** | Top 5 anti-patterns | Review before risky operations |
| **§ Expert heuristic** | Data source selection + dashboard panel layout strategy | Design decisions |

## Quick reference — deployment checklist

| Dimension | Requirement | Step |
|---|---|---|
| Workspace name | Globally unique | Step 1 |
| Authentication | IAM Identity Center (recommended) or SAML | Step 1 |
| Grafana version | Standard or Enterprise | Step 1 |
| IAM role | Service-managed (auto) or customer-managed (custom) | Step 2 |
| Data source: CloudWatch | IAM role with cloudwatch:GetMetricData, logs:DescribeLogGroups | Step 3 |
| Data source: AMP | AMP workspace ARN + IAM role with aps:QueryMetrics | Step 3 |
| Data source: Timestream | IAM role with timestream:Select | Step 3 |
| Data source: OpenSearch | OpenSearch endpoint + IAM role with es:ESHttpGet | Step 3 |
| Data source: X-Ray | IAM role with xray:GetTraceSummaries | Step 3 |
| Dashboard JSON | Panels, templating variables, time range, datasource ref | Step 4 |
| Alert rules | Condition, evaluation interval, for duration | Step 5 |
| Notification policies | Routing by labels/severity | Step 5 |
| Contact points | SNS, Slack, email, PagerDuty, webhook | Step 5 |
| AMP workspace | Exists and is ACTIVE (if using Prometheus data source) | Step 6 |
| Enterprise features | Incident, OnCall, reporting, SAML team sync | Step 7 |

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If any
are missing, the verdict is **PREREQUISITES_MISSING** with a specific gap
citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account with Grafana access | Cannot provision without it | `aws sts get-caller-identity` |
| Region selected | Managed Grafana is region-scoped | `aws configure get region` |
| IAM Identity Center enabled (for SSO) | Recommended auth mode; avoids separate SAML setup | `aws sso-admin list-instances` |
| AMP workspace ACTIVE (if Prometheus data source) | Grafana queries the AMP workspace via remote read | `aws amps list-workspaces` |
| OpenSearch domain ACTIVE (if OpenSearch data source) | Grafana queries via the domain endpoint | `aws opensearch list-domain-names` |
| KMS key (for workspace encryption) | Grafana workspace data encryption | `aws kms describe-key --key-id <key-id>` |
| VPC + subnets (for VPC-attached data sources) | Private networking to internal data sources | `aws ec2 describe-subnets` |
| SNS topic (for alert contact points) | Grafana alert notifications via SNS | `aws sns list-topics` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Workspace tier selection (Standard vs Enterprise)

| Tier | Key features | Cost | Use when |
|---|---|---|---|
| **Standard** | Core Grafana, 5 data source types, basic alerting, IAM Identity Center auth | Lower | Most observability workloads, team-level dashboards |
| **Enterprise** | All Standard + Enterprise plugins, SAML, team sync from IdP, reporting, Incident, OnCall, audit logs | Higher | Enterprise SSO, on-call management, compliance reporting, incident response |

**Immutability note:** the Grafana version (Standard vs Enterprise) is
set at workspace creation via the `grafanaVersion` or license type.
Upgrading from Standard to Enterprise is supported via AWS support
ticket; plan the tier before creating the workspace.

## 10-step provisioning procedure

### Step 1 — Workspace creation + authentication

The workspace is the top-level resource. Authentication mode is decided
here and is difficult to change post-creation.

```bash
aws grafana create-workspace \
  --workspace-name <workspace-name> \
  --account-access-type CURRENT_ACCOUNT \
  --authentication-providers AWS_SSO \
  --permission-type SERVICE_MANAGED \
  --data-sources CLOUDWATCH PROMETHEUS XRAY \
  --grafana-version 10.4 \
  --description "Production observability workspace"
```

**Authentication providers:**
- `AWS_SSO` — IAM Identity Center (recommended). Integrates with
  corporate IdP via SAML or external IdP providers.
- `SAML` — direct SAML 2.0 integration (requires SAML metadata URL/JSON).

**Permission types:**
- `SERVICE_MANAGED` — Grafana manages IAM roles for data sources
  automatically. Simpler but less control over permissions.
- `CUSTOMER_MANAGED` — you provide a customer-managed IAM role with
  explicit permissions per data source. Required for fine-grained
  access control and compliance.

**Common mistake:** choosing `SERVICE_MANAGED` for a compliance workload.
Service-managed roles grant broad read across all data sources of the
configured types. For compliance (least-privilege), use `CUSTOMER_MANAGED`.

### Step 2 — IAM role for data source access

**Service-managed (auto-created):** Grafana creates an IAM role with
permissions scoped to the configured data source types. No manual IAM
configuration needed.

**Customer-managed IAM role:** create a role with the `Grafana`
service principal and scoped read permissions:

```bash
# Trust policy for Amazon Managed Grafana
aws iam create-role \
  --role-name GrafanaDataSourceRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow","Principal": {"Service": "grafana.amazonaws.com"},"Action": "sts:AssumeRole"}]
  }'

# Attach inline policy for data source read access
aws iam put-role-policy \
  --role-name GrafanaDataSourceRole \
  --policy-name GrafanaDataSourceRead \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {"Effect": "Allow","Action": ["cloudwatch:GetMetricData","cloudwatch:GetMetricStatistics","cloudwatch:ListMetrics"],"Resource": "*"},
      {"Effect": "Allow","Action": ["logs:DescribeLogGroups","logs:GetLogEvents","logs:StartQuery","logs:GetQueryResults"],"Resource": "*"},
      {"Effect": "Allow","Action": ["aps:GetLabels","aps:GetMetricMetadata","aps:GetSeries","aps:QueryMetrics"],"Resource": "arn:aws:aps:<region>:<acct>:workspace/<amp-id>"},
      {"Effect": "Allow","Action": ["timestream:Select","timestream:DescribeEndpoints"],"Resource": "*"},
      {"Effect": "Allow","Action": ["xray:GetTraceSummaries","xray:GetTraceGraph","xray:GetSamplingRules"],"Resource": "*"},
      {"Effect": "Allow","Action": ["es:ESHttpGet","es:ESHttpHead"],"Resource": "arn:aws:es:<region>:<acct>:domain/<domain>/*"}
    ]
  }'
```

**Associate the role with the workspace:**
```bash
aws grafana update-workspace-configuration \
  --workspace-id <workspace-id> \
  --data-sources CLOUDWATCH PROMETHEUS XRAY
```

### Step 3 — Data source configuration

Managed Grafana supports five native AWS data source types. Each requires
specific configuration in the Grafana workspace.

**CloudWatch** (enabled via `--data-sources CLOUDWATCH`):
- Regions: specify which AWS regions to query
- Namespaces: CloudWatch metric namespaces (e.g., AWS/EC2, AWS/Lambda)
- Log groups: optional, for CloudWatch Logs queries

**Prometheus / AMP** (enabled via `--data-sources PROMETHEUS`):
- AMP workspace ARN: the Prometheus workspace to query
- Requires IAM role with `aps:QueryMetrics` on the AMP workspace

```bash
# Create AMP workspace (if not existing)
aws amps create-workspace \
  --workspace-name <amp-name> \
  --alias <amp-alias>

# Get AMP workspace ID for Grafana data source config
aws amps describe-workspace --workspace-id <amp-id>
```

**Timestream** (enabled via `--data-sources TIMESTREAM`):
- Database/table selection via Grafana query editor
- Requires IAM role with `timestream:Select` and `timestream:DescribeEndpoints`

**OpenSearch** (enabled via `--data-sources OPENSEARCH`):
- OpenSearch domain endpoint URL
- Requires IAM role with `es:ESHttpGet` on the domain

**X-Ray** (enabled via `--data-sources XRAY`):
- Service map and trace visualization
- Requires IAM role with `xray:GetTraceSummaries` and `xray:GetTraceGraph`

**Common mistake:** adding a data source type in Grafana without the
matching IAM permission. The data source appears configured but returns
permission errors on every query. Verify IAM role includes the
specific read actions for each data source.

### Step 4 — Dashboard JSON model (panels, templating, time range)

Grafana dashboards are JSON documents. The dashboard JSON model defines
panels, templating variables, time range, annotations, and refresh rate.

**Dashboard JSON structure:**

```json
{
  "title": "Production Observability",
  "schemaVersion": 39,
  "version": 1,
  "refresh": "30s",
  "time": { "from": "now-6h", "to": "now" },
  "templating": {
    "list": [
      {
        "name": "datasource",
        "type": "datasource",
        "query": "cloudwatch",
        "current": { "text": "CloudWatch", "value": "cloudwatch" }
      },
      {
        "name": "region",
        "type": "query",
        "datasource": "$datasource",
        "query": "regions()",
        "current": { "text": "us-east-1", "value": "us-east-1" }
      }
    ]
  },
  "panels": [
    {
      "type": "timeseries",
      "title": "CPU Utilization",
      "datasource": "$datasource",
      "gridPos": { "h": 8, "w": 12, "x": 0, "y": 0 },
      "targets": [
        {
          "expr": "AWS/EC2 CPUUtilization",
          "namespace": "AWS/EC2",
          "metricName": "CPUUtilization",
          "statistics": ["Average"]
        }
      ]
    }
  ]
}
```

**Templating variables** make dashboards reusable across environments,
regions, and services. Use `datasource`, `query`, and `custom` variable
types for dynamic filtering.

**Panel types by use case:**

| Panel type | Use when |
|---|---|
| `timeseries` | Time-series metrics (CPU, latency, throughput) |
| `stat` | Single-value KPIs (current value, threshold) |
| `gauge` | Single-value with range (0-100%, utilization) |
| `table` | Multi-column data (instance list, log results) |
| `bargauge` | Comparison across categories (cost by service) |
| `heatmap` | Distribution over time (latency percentiles) |
| `nodegraph` | Service maps (X-Ray traces) |
| `logs` | Log viewer (CloudWatch Logs queries) |

**Provisioning dashboards via API:**
```bash
# Get workspace API key
aws grafana create-workspace-api-key \
  --workspace-id <workspace-id> \
  --key-name deploy-key \
  --key-role ADMIN \
  --seconds-to-live 3600 \
  --query 'key' --output text > /tmp/grafana-key

# Import dashboard via Grafana HTTP API
curl -X POST \
  -H "Authorization: Bearer $(cat /tmp/grafana-key)" \
  -H "Content-Type: application/json" \
  -d @dashboard.json \
  https://<workspace-endpoint>/api/dashboards/db
```

### Step 5 — Alerting (rules, notification policies, contact points)

Grafana alerting has three layers that must all be configured:

**Alert rules** — the condition that triggers an alert. Defines the
metric query, threshold, evaluation interval, and `for` duration:

```json
{
  "uid": "cpu-high", "title": "CPU Utilization High",
  "condition": "B",
  "data": [
    {"refId":"A","datasourceUid":"cloudwatch-uid","model":{"namespace":"AWS/EC2","metricName":"CPUUtilization","statistics":["Average"]}},
    {"refId":"B","model":{"expression":"$A > 85","type":"threshold"}}
  ],
  "for": "5m",
  "labels": {"severity":"warning","team":"platform"}
}
```

**Notification policies** — route alert instances to contact points by
label matchers (severity, team, etc.):

```json
{
  "routes": [
    {"receiver":"sns-platform","object_matchers":[["team","=","platform"]]},
    {"receiver":"sns-critical","object_matchers":[["severity","=","critical"]]}
  ]
}
```

**Contact points** — the notification destination (SNS, Slack, email,
PagerDuty, webhook):

```json
{"name":"sns-platform","type":"sns","settings":{"topic":"arn:aws:sns:us-east-1:123456789012:grafana-alerts","authProvider":"aws_iam","region":"us-east-1"}}
```

**Common mistake:** creating alert rules without notification policies or
contact points. The rule fires but no notification is sent — the alert
shows as "firing" in the Grafana UI but nothing reaches the on-call team.
Configure all three layers.

### Step 6 — AMP workspace integration

Amazon Managed Service for Prometheus (AMP) provides serverless Prometheus-
compatible metric storage. Integration with Grafana is via the Prometheus
data source.

```bash
# Create AMP workspace
aws amps create-workspace \
  --workspace-name <amp-name> \
  --alias <amp-alias> \
  --kms-key-arn arn:aws:kms:<region>:<acct>:key/<key-id>

# Wait for ACTIVE status
aws amps describe-workspace --workspace-id <amp-id> \
  --query 'workspace.status.statusCode' --output text

# Configure remote write (from Prometheus / OpenTelemetry / CloudWatch agent)
# The AMP workspace endpoint is:
# https://aps-workspaces.<region>.amazonaws.com/workspaces/<amp-id>/
```

**Remote write sources:**
- CloudWatch agent with embedded metric format
- Prometheus server with `remote_write` to AMP
- OpenTelemetry Collector with Prometheus exporter
- Distroless OTel collector on EKS/ECS

**Common mistake:** querying AMP before metrics are flowing. Verify remote
write is active by checking `aws amps describe-workspace` for ingest
metrics, then querying from Grafana.

### Step 7 — Grafana Enterprise features (Incident, OnCall)

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

## Common patterns (boilerplate)

### Create a workspace with CloudWatch + AMP + X-Ray (production)

```bash
aws grafana create-workspace \
  --workspace-name prod-observability \
  --account-access-type CURRENT_ACCOUNT \
  --authentication-providers AWS_SSO \
  --permission-type CUSTOMER_MANAGED \
  --data-sources CLOUDWATCH PROMETHEUS XRAY \
  --grafana-version 10.4
```

### Create a customer-managed IAM role for data source access

```bash
aws iam create-role --role-name GrafanaDataSourceRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"grafana.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

aws iam put-role-policy --role-name GrafanaDataSourceRole \
  --policy-name DataSourceRead \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["cloudwatch:GetMetricData","cloudwatch:ListMetrics","logs:DescribeLogGroups","aps:QueryMetrics","xray:GetTraceSummaries"],"Resource":"*"}]}'
```

### AMP workspace + dashboard import

```bash
aws amps create-workspace --workspace-name prod-metrics --alias prod

GRAFANA_KEY=$(aws grafana create-workspace-api-key --workspace-id <id> \
  --key-name deploy --key-role ADMIN --seconds-to-live 3600 --query 'key' --output text)

curl -X POST -H "Authorization: Bearer $GRAFANA_KEY" -H "Content-Type: application/json" \
  -d @dashboard.json https://<endpoint>/api/dashboards/db
```

## NEVER do these things (top 5)

1. **NEVER create a Managed Grafana workspace without deciding the
   authentication mode first.** Switching from SAML to IAM Identity
   Center (or vice versa) requires recreating the workspace. Plan auth
   before `create-workspace`. IAM Identity Center (`AWS_SSO`) is the
   recommended default.

2. **NEVER use `SERVICE_MANAGED` permission type for compliance
   workloads.** Service-managed roles grant broad read across all data
   sources of the configured types. For least-privilege and compliance
   (PCI-DSS, HIPAA, SOC2), use `CUSTOMER_MANAGED` with an explicit IAM
   role policy scoped to specific resources.

3. **NEVER configure alert rules without notification policies and
   contact points.** A rule without a notification policy fires but
   goes nowhere. A notification policy without a contact point routes
   to nothing. Configure all three layers: rule -> policy -> contact.

4. **NEVER query an AMP workspace before verifying it is ACTIVE and
   receiving metrics.** The AMP workspace must be `ACTIVE` and the
   remote write source must be sending data. Querying an empty AMP
   workspace returns no results — not an error — leading to false
   confidence that the integration is working.

5. **NEVER hardcode dashboard data sources.** Use templating variables
   (`$datasource`) so dashboards work across environments and regions.
   Hardcoded data source UIDs break when importing dashboards across
   workspaces or environments.

## Expert heuristic: data source selection and dashboard layout

```
DATA SOURCE SELECTION
   ├─ CloudWatch metrics (AWS native)
   │    └─ Namespace: AWS/EC2, AWS/Lambda, AWS/RDS, AWS/ApplicationELB
   │         • Pros: zero setup, all AWS services
   │         • Cons: 1-minute resolution (high-res is 10s with detailed monitoring)
   │         • Best for: AWS infrastructure monitoring
   │
   ├─ AMP/Prometheus (custom + application metrics)
   │    └─ Remote write from app, CloudWatch agent, OTel collector
   │         • Pros: high-resolution (15s or better), PromQL, custom labels
   │         • Cons: requires remote write pipeline setup
   │         • Best for: application metrics, Kubernetes, custom exporters
   │
   ├─ Timestream (high-volume time-series)
   │    └─ IoT, DevOps, application events
   │         • Pros: petabyte-scale, SQL queries, cost-effective at high volume
   │         • Cons: SQL (not PromQL), different query model
   │         • Best for: IoT telemetry, high-cardinality event data
   │
   ├─ OpenSearch (log analytics)
   │    └─ Log queries, full-text search, aggregation
   │         • Pros: Lucene/PPL queries, aggregation pipelines
   │         • Cons: separate from CloudWatch Logs
   │         • Best for: centralized log analytics with OpenSearch
   │
   └─ X-Ray (distributed tracing)
        └─ Service maps, trace waterfalls, latency breakdown
         • Pros: AWS-native tracing, no separate collector needed
         • Cons: limited to instrumented apps with X-Ray SDK
         • Best for: microservices tracing on ECS/EKS/Lambda

DASHBOARD LAYOUT (3-tier pattern)
   Tier 1 (Row 1): Status overview — stat panels (KPIs, health checks)
   Tier 2 (Row 2): Time-series trends — CPU, latency, throughput
   Tier 3 (Row 3): Detail tables — top-N instances, error logs, traces
   ── Use row collapses to keep the dashboard scannable
   ── Use templating variables ($region, $service, $datasource)
   ── Set refresh: 30s for operational, 5m for executive overview
```

## Output format

```text
WORKSPACE: <workspace-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Workspace: <name>, version: <10.4 | 11.0> (Standard | Enterprise)
  [✓|✗] Authentication: AWS_SSO (IAM Identity Center) | SAML
  [✓|✗] Permission type: SERVICE_MANAGED | CUSTOMER_MANAGED
  [✓|✗] IAM role: <role-name> (CloudWatch + AMP + X-Ray read access)
  [✓|✗] Data source: CloudWatch (regions: <list>)
  [✓|✗] Data source: AMP/Prometheus (workspace: <amp-id>, status: ACTIVE)
  [✓|✗] Data source: Timestream (database: <name>)
  [✓|✗] Data source: OpenSearch (domain: <name>)
  [✓|✗] Data source: X-Ray
  [✓|✗] Dashboard: <title> (<N> panels, templating: <list>)
  [✓|✗] Alert rules: <N> rules (evaluation interval: <N>s, for: <N>m)
  [✓|✗] Notification policies: <N> routes (by: severity, team)
  [✓|✗] Contact points: <list> (SNS, Slack, email)
  [✓|✗] VPC config: <subnet-ids, sg-ids> | Public
  [✓|✗] Tags: <list>
VERIFICATION_COMMANDS:
  aws grafana describe-workspace --workspace-id <id>
  aws grafana list-workspaces
  aws amps describe-workspace --workspace-id <amp-id>
  aws iam get-role --role-name GrafanaDataSourceRole
```

### Worked example — production observability with CloudWatch + AMP + X-Ray

```text
WORKSPACE: prod-observability
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Workspace: prod-observability, version: 10.4 (Standard)
  [✓] Authentication: AWS_SSO (IAM Identity Center)
  [✓] Permission type: CUSTOMER_MANAGED
  [✓] IAM role: GrafanaDataSourceRole (cloudwatch:GetMetricData, aps:QueryMetrics, xray:GetTraceSummaries)
  [✓] Data source: CloudWatch (regions: us-east-1, us-west-2)
  [✓] Data source: AMP/Prometheus (workspace: ws-abc123, status: ACTIVE)
  [✓] Data source: X-Ray
  [✓] Dashboard: Production Overview (12 panels, templating: $datasource, $region)
  [✓] Alert rules: 5 rules (evaluation: 60s, for: 5m)
  [✓] Notification policies: 2 routes (severity=critical -> sns-critical, team=platform -> sns-platform)
  [✓] Contact points: SNS (arn:aws:sns:us-east-1:123456789012:grafana-alerts)
  [✓] Tags: Environment=production, Workload=observability
VERIFICATION_COMMANDS:
  aws grafana describe-workspace --workspace-id g-abc123
  aws amps describe-workspace --workspace-id ws-abc123
  aws iam get-role --role-name GrafanaDataSourceRole
```

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
WORKSPACE: <workspace-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] <check description>
VERIFICATION_COMMANDS:
  <aws grafana / amps / iam commands>
```

### FORBIDDEN output patterns

- NEVER start with conversational preamble. The WORKSPACE/VERDICT block
  is the FIRST line, always. Use uppercase verdict values only
  (`READY_TO_DEPLOY`, `PREREQUISITES_MISSING`).
- NEVER omit the CHECKLIST — every dimension (workspace, auth, permission
  type, IAM role, data sources, dashboard, alerting layers, tags) must
  appear with a pass/fail marker.
- NEVER recommend `SERVICE_MANAGED` permission type for compliance
  workloads without flagging it as a WARN finding (broad read access).
- NEVER list a CLI command with placeholder flags in a READY_TO_DEPLOY
  plan — every flag must be populated with actual values from the input.
- NEVER recommend a dashboard with hardcoded data source UIDs without
  flagging the portability risk across workspaces.

## Recent AWS features (2024-2026)

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

## Domain

AWS CloudOps / Amazon Managed Grafana Workspace Provisioning, Data Source
Integration, Dashboard Design, and Alerting.

## AWS documentation

- **Amazon Managed Grafana User Guide** — https://docs.aws.amazon.com/grafana/latest/userguide/what-is-amazon-managed-grafana.html
- **Create a Workspace** — https://docs.aws.amazon.com/grafana/latest/userguide/AMG-manage-workspace.html
- **Data Sources** — https://docs.aws.amazon.com/grafana/latest/userguide/AMG-data-sources.html
- **CloudWatch Data Source** — https://docs.aws.amazon.com/grafana/latest/userguide/CloudWatch-template.html
- **AMP Integration** — https://docs.aws.amazon.com/grafana/latest/userguide/AMP-configure-data-source.html
- **Grafana Alerting** — https://docs.aws.amazon.com/grafana/latest/userguide/alerts.html
- **IAM Identity Center** — https://docs.aws.amazon.com/grafana/latest/userguide/AMG-with-IAM-Identity-Center.html
- **Grafana Enterprise** — https://docs.aws.amazon.com/grafana/latest/userguide/enterprise.html
- **Grafana API Reference** — https://docs.aws.amazon.com/grafana/latest/APIReference/
- **Amazon Managed Service for Prometheus** — https://docs.aws.amazon.com/prometheus/latest/userguide/what-is-Amazon-Managed-Service-Prometheus.html
