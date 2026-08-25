---
name: grafana-data-source-deployer
description: 'Provisions Amazon Managed Grafana workspaces with production defaults: workspace creation, SAML/SSO authentication, data source configuration (CloudWatch, Prometheus/AMP, Athena, Timestream, OpenSearch, X-Ray), IAM role for data source access (workspace role with per-service read permissions), workspace API key, dashboard provisioning (import/export JSON), user/group management, workspace endpoint, plugin management, organization units, notification channels, version control integration, and Grafana Enterprise features. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Grafana workspace, configuring data sources, setting up SAML SSO, provisioning dashboards, or managing workspace permissions. Triggers: create grafana workspace, grafana data source cloudwatch, grafana prometheus data source, grafana athena data source, grafana saml sso, grafana workspace api key, grafana dashboard provisioning, grafana iam role.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with grafana and iam access. Works with Terraform aws_grafana_workspace / aws_grafana_workspace_api_key / aws_grafana_role_association resources and CloudFormation AWS::Grafana::Workspace templates.'
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
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, grafana, managed-grafana, cloudops, deploy, management, provisioning, observability, dashboards, data-source, saml-sso
  dependencies: aws-orchestrator
  keywords: aws, grafana, managed grafana, data source, cloudops, deploy, provisioning, workspace, saml, sso, cloudwatch, prometheus, dashboard, visualization
  when_to_use: Invoke when the user wants to create an Amazon Managed Grafana workspace, configure data sources (CloudWatch, Prometheus/AMP, Athena, Timestream, OpenSearch, X-Ray), set up SAML SSO authentication, provision dashboards, create workspace API keys, manage workspace users/groups, or configure notification channels. Do NOT invoke for self-hosted Grafana (EC2/ECS), Amazon CloudWatch dashboards (use cloudwatch-dashboard skills), or QuickSight.
---

# Grafana Data Source Deployer

An AWS CloudOps agent skill that provisions Amazon Managed Grafana
workspaces with correct defaults. The skill walks the operator
through workspace creation, authentication (SAML SSO or IAM Identity
Center), data source configuration with per-service IAM permissions,
workspace API key creation, dashboard provisioning, and notification
channels. It captures integration decisions, explains why each default
matters, and emits a READY_TO_DEPLOY checklist with copy-pasteable
verification commands.

## Activation keywords

create Grafana workspace, Grafana data source CloudWatch, Grafana
Prometheus data source, Grafana Athena data source, Grafana SAML SSO,
Grafana workspace API key, Grafana dashboard provisioning, Grafana
IAM role.

## STRICT output contract

When this skill is invoked with a Grafana workspace provisioning
request (create a workspace, configure a data source, set up SSO,
provision dashboards, or a partial configuration), the agent MUST
respond with the READY_TO_DEPLOY checklist defined in the "Output
format" section using the literal all-caps labels `GRAFANA:`,
`VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface
the checklist with prose, headings, or disclaimers — emit the block
as the first lines of the response. This contract is what assertion-
based evals and downstream provisioning pipelines rely on; deviating
from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Workspace creation | Core workspace model |
| Step 2 — Authentication (SAML SSO or IAM Identity Center) | Access control |
| Step 3 — Workspace IAM role and permissions | Per-service data access |
| Step 4 — Data source configuration | Connecting AWS services |
| Step 5 — Workspace API key and dashboard provisioning | Programmatic access + dashboards |
| Step 6 — User management, notifications, plugins | Operations |
| Step 7 — Version control integration | GitOps |
| Step 8 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/data-sources-and-iam.md | Data source + IAM detail |
| references/authentication-and-access.md | SSO + user management detail |

## Mindset

**One-line takeaway:** Amazon Managed Grafana is a fully managed
Grafana server. The workspace IAM role must have per-service read
permissions for each configured data source (CloudWatch read,
Prometheus query, Athena query, etc.). SAML SSO requires an external
Identity Provider. Data sources are added via the Grafana API or
console after the workspace IAM role has the correct permissions.

Three misconceptions dominate Grafana workspace misdesign at
provisioning time:

- **"Creating the workspace is enough to see data."** It is not. The
  workspace starts with no data sources configured. Each data source
  must be explicitly added through the Grafana API or console. The
  workspace IAM role must have the correct per-service read
  permissions — without them, data source queries fail with permission
  errors.

- **"One IAM role fits all data sources."** It does not. Each data
  source requires specific IAM permissions. CloudWatch needs
  `cloudwatch:ListMetrics` and `cloudwatch:GetMetricData`. Prometheus
  (AMP) needs `aps:QueryMetrics`. Athena needs
  `athena:StartQueryExecution` and `athena:GetQueryResults`. A single
  broad role without the right actions is an anti-pattern — use per-
  service scoped permissions.

- **"SAML SSO works out of the box."** It does not. SAML SSO requires
  an external Identity Provider (Okta, Azure AD, etc.). You must
  configure the IdP metadata, the Grafana SAML assertion attributes,
  and the ACS URL. Without the IdP setup, SAML authentication cannot
  function.

## Configuration dependency graph (novel heuristic)

Grafana workspace configurations are NOT independent. The IAM role
must be attached before data sources work. SAML SSO requires the
IdP metadata. Dashboard provisioning requires an API key or SSO
user with admin rights. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Workspace creation | Unique name; authentication type chosen | Workspace is `CREATING` then `ACTIVE`; cannot query until ACTIVE | the workspace endpoint |
| Workspace IAM role | Trust policy for `grafana.amazonaws.com`; per-service read permissions | Without CloudWatch read, CloudWatch data source queries return empty; without AMP query, Prometheus fails | data source access |
| Data source: CloudWatch | Workspace ACTIVE; IAM role has `cloudwatch:ListMetrics`, `cloudwatch:GetMetricData` | Missing permissions = silent empty results (no error in UI) | CloudWatch metrics and logs |
| Data source: Prometheus | Workspace ACTIVE; IAM role has `aps:QueryMetrics`, `aps:ListWorkspaces` | Missing permissions = error in query panel | AMP metrics |
| Data source: Athena | Workspace ACTIVE; IAM role has `athena:StartQueryExecution`, `athena:GetQueryResults`, S3 read for results | Missing S3 permissions = query execution fails | Athena query results |
| SAML SSO | External IdP configured; IdP metadata URL/XML; assertion attributes mapped | Without IdP metadata, SAML login fails | SSO user login |
| Workspace API key | Workspace ACTIVE | API key cannot be retrieved after creation (store immediately) | Programmatic dashboard provisioning |
| Dashboard provisioning | API key or SSO admin; data sources configured | Unknown data source UID in JSON = panels show "No data" | dashboards visible in Grafana |
| Notification channels | Workspace ACTIVE; external endpoint configured | Misconfigured webhook = alerts silently fail | alerting |

**The IAM-role-per-service row is the one a baseline model misses.**
Creating the workspace is necessary but not sufficient. Each data
source needs specific IAM permissions in the workspace role. Without
CloudWatch read, the CloudWatch data source connects but returns
empty results — a silent failure that is extremely hard to debug.

**Cross-dependency gotchas:**
- The workspace IAM role must be attached at creation time or via
  `update-workspace`. Changing the role requires a workspace update.
- Data source UID in imported dashboard JSON must match the workspace
  data source UID. Mismatched UIDs cause panels to show "No data".
- API keys are shown ONCE at creation. If lost, a new key must be
  created.
- SAML SSO and IAM Identity Center are mutually exclusive.

## Expert heuristic: per-service IAM permissions for data sources

A baseline model says "create a workspace role." The correct heuristic
recognizes that each data source requires specific IAM permissions.

```text
Workspace IAM Role Decision:
  ├── CloudWatch data source?
  │     → cloudwatch:ListMetrics, cloudwatch:GetMetricData
  │       cloudwatch:GetMetricStatistics, cloudwatch:DescribeAlarms
  │       logs:DescribeLogGroups, logs:StartQuery, logs:GetQueryResults
  ├── Prometheus (AMP) data source?
  │     → aps:QueryMetrics, aps:ListWorkspaces, aps:DescribeWorkspace
  │       aps:GetLabels, aps:GetSeries
  ├── Athena data source?
  │     → athena:StartQueryExecution, athena:GetQueryResults
  │       athena:StopQueryExecution, athena:GetWorkGroup
  │       s3:GetObject (query results bucket), glue:GetTable, glue:GetDatabase
  ├── Timestream data source?
  │     → timestream:DescribeEndpoints, timestream:SelectQuery
  │       timestream:ListMeasures, timestream:ListDatabases
  ├── OpenSearch data source?
  │     → es:ESHttpGet, es:ESHttpPost, es:DescribeDomain
  └── X-Ray data source?
        → xray:BatchGetTraces, xray:GetTraceSummaries
          xray:GetGroups, xray:GetSamplingRules
```

**Key implication:** missing permissions cause silent empty results.
There is no error in the Grafana UI. The data source appears connected,
but queries return no data. Always verify per-service permissions.

## Expert heuristic: SAML SSO requires external IdP

IdP-first SAML setup flow (ACS URL, attribute mappings, update-workspace-saml-configuration) moved verbatim to [references/authentication-and-access.md](references/authentication-and-access.md).
Load on demand when the authentication mode is SAML.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Authentication method chosen | SAML SSO or IAM Identity Center | Confirm auth type |
| IdP metadata available (for SAML) | SAML SSO requires external IdP | Confirm IdP metadata URL/XML |
| IAM role with per-service permissions | Data source access requires scoped permissions | Verify role policy |
| AMP workspace ARN (for Prometheus) | Prometheus data source needs the AMP workspace | `aws amp list-workspaces` |
| Athena workgroup and results bucket (for Athena) | Athena queries need a workgroup and results location | `aws athena list-work-groups` |
| OpenSearch domain ARN (for OpenSearch) | OpenSearch data source needs the domain | `aws opensearch list-domain-names` |
| Data source list identified | Each data source needs specific configuration | Confirm data sources |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Workspace creation

**Create a Managed Grafana workspace:**

```bash
WORKSPACE_ID=$(aws grafana create-workspace \
  --workspace-name prod-observability \
  --account-access-type CURRENT_ACCOUNT \
  --authentication-provider AWS_SSO \
  --permission-type SERVICE_MANAGED \
  --data-sources CLOUDWATCH PROMETHEUS ATHENA \
  --description "Production observability Grafana workspace" \
  --region us-east-1 \
  --query 'workspace.id' --output text)
```

| Parameter | Options | Notes |
|---|---|---|
| `--account-access-type` | `CURRENT_ACCOUNT`, `ORGANIZATION` | Use CURRENT_ACCOUNT for standalone |
| `--authentication-provider` | `AWS_SSO`, `SAML` | AWS_SSO = IAM Identity Center |
| `--permission-type` | `SERVICE_MANAGED`, `CUSTOM` | SERVICE_MANAGED uses Identity Center groups |
| `--data-sources` | `CLOUDWATCH`, `PROMETHEUS`, `ATHENA`, `TIMESTREAM`, `OPENSEARCH`, `XRAY` | Pre-register or add later via API |

**Verify workspace is ACTIVE:**

```bash
aws grafana describe-workspace \
  --workspace-id "$WORKSPACE_ID" \
  --query 'workspace.{Status:status,Endpoint:endpoint}' --region us-east-1
# Expected: Status: ACTIVE
```

## Step 2 — Authentication (SAML SSO or IAM Identity Center)

### IAM Identity Center (AWS SSO)

```bash
# Configured at creation time via --authentication-provider AWS_SSO
# After workspace creation, assign users/groups:
aws grafana update-permissions \
  --workspace-id "$WORKSPACE_ID" \
  --update-instruction-batch \
    "action=ADD,role=ADMIN,users=[{\"id\":\"user-id\",\"ssoId\":\"user@example.com\"}]"
```

### SAML SSO

```bash
# Create workspace with SAML
aws grafana create-workspace \
  --authentication-provider SAML \
  --workspace-role-arn arn:aws:iam::123456789012:role/GrafanaWorkspaceRole ...

# Configure SAML after workspace is ACTIVE
aws grafana update-workspace-saml-configuration \
  --workspace-id "$WORKSPACE_ID" \
  --saml-configuration '{
    "idpMetadata": {"url": "https://idp.example.com/saml/metadata"},
    "assertionAttributes": {"email": "email", "name": "displayName", "login": "email"},
    "roleValues": {"admin": "grafana-admins", "editor": "grafana-editors"}
  }' --region us-east-1
```

**Critical:** SAML SSO requires an external IdP configured first.

## Step 3 — Workspace IAM role and permissions

The workspace IAM role grants Grafana access to AWS services for data
source queries. Each data source needs specific permissions.

**Create the role and attach permissions:**

```bash
# Create trust policy for grafana.amazonaws.com
WORKSPACE_ROLE_ARN=$(aws iam create-role \
  --role-name GrafanaWorkspaceRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"grafana.amazonaws.com"},"Action":"sts:AssumeRole"}]}' \
  --query 'Role.Arn' --output text)

# Attach per-service permissions policy
aws iam put-role-policy \
  --role-name GrafanaWorkspaceRole \
  --policy-name GrafanaDataSourcePermissions \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {"Effect": "Allow", "Actions": ["cloudwatch:ListMetrics","cloudwatch:GetMetricData","cloudwatch:GetMetricStatistics","cloudwatch:DescribeAlarms","logs:DescribeLogGroups","logs:StartQuery","logs:GetQueryResults"], "Resource": "*"},
      {"Effect": "Allow", "Actions": ["aps:QueryMetrics","aps:ListWorkspaces","aps:DescribeWorkspace","aps:GetLabels","aps:GetSeries"], "Resource": "*"},
      {"Effect": "Allow", "Actions": ["athena:StartQueryExecution","athena:GetQueryResults","athena:StopQueryExecution","athena:GetWorkGroup","glue:GetTable","glue:GetDatabase"], "Resource": "*"},
      {"Effect": "Allow", "Actions": ["s3:GetObject","s3:ListBucket"], "Resource": "arn:aws:s3:::athena-query-results-*/*"},
      {"Effect": "Allow", "Actions": ["timestream:DescribeEndpoints","timestream:SelectQuery","timestream:ListMeasures","timestream:ListDatabases"], "Resource": "*"}
    ]
  }'

# Attach role to workspace
aws grafana update-workspace \
  --workspace-id "$WORKSPACE_ID" \
  --workspace-role-arn "$WORKSPACE_ROLE_ARN" --region us-east-1
```

**Critical:** without the correct permissions, data sources connect but
return empty results. This is a silent failure — no error in the UI.

## Step 4 — Data source configuration

Data sources are added via the Grafana HTTP API after the workspace is
ACTIVE and the IAM role has correct permissions.

**Create a workspace API key first:**

```bash
API_KEY=$(aws grafana create-workspace-api-key \
  --workspace-id "$WORKSPACE_ID" \
  --key-name "datasource-provisioning" \
  --key-role ADMIN \
  --seconds-to-live 3600 --region us-east-1 \
  --query 'key' --output text)

ENDPOINT="https://g-${WORKSPACE_ID}.grafana-workspace.us-east-1.amazonaws.com"
```

**Add CloudWatch data source:**

```bash
curl -s -X POST "$ENDPOINT/api/datasources" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d '{"name":"CloudWatch-prod","type":"cloudwatch","access":"proxy","jsonData":{"authType":"ec2_iam_role","defaultRegion":"us-east-1"},"isDefault":true}'
```

**Add Prometheus (AMP) data source:**

```bash
curl -s -X POST "$ENDPOINT/api/datasources" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d '{"name":"Prometheus-AMP","type":"prometheus","access":"proxy","url":"https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-xxx/api/v1","jsonData":{"httpMethod":"POST","sigV4Auth":true,"sigV4AuthType":"workspace","sigV4Region":"us-east-1"}}'
```

**Add Athena data source:**

```bash
curl -s -X POST "$ENDPOINT/api/datasources" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d '{"name":"Athena-prod","type":"athena","access":"proxy","jsonData":{"authType":"default","defaultRegion":"us-east-1","catalog":"AwsDataCatalog","database":"default","workgroup":"primary","outputLocation":"s3://athena-query-results-123456789012/"}}'
```

**Key:** use `authType: ec2_iam_role` for CloudWatch and `sigV4Auth: true`
for Prometheus. Never hardcode AWS credentials in the data source JSON.

## Step 5 — Workspace API key and dashboard provisioning

**Create a workspace API key:**

```bash
API_KEY=$(aws grafana create-workspace-api-key \
  --workspace-id "$WORKSPACE_ID" \
  --key-name "ci-cd-provisioning" \
  --key-role ADMIN \
  --seconds-to-live 86400 --region us-east-1 \
  --query 'key' --output text)
```

| Role | Permissions |
|---|---|
| `ADMIN` | Full workspace access |
| `EDITOR` | Create/edit dashboards, query data sources |
| `VIEWER` | View dashboards only |

**Critical:** the API key is shown ONCE. Store it in AWS Secrets Manager.

**Import a dashboard from JSON:**

```bash
curl -s -X POST "$ENDPOINT/api/dashboards/db" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d @dashboard.json
```

**Critical:** ensure data source UIDs in the dashboard JSON match the
workspace data source UIDs. Mismatches cause panels to show "No data".

## Step 6 — User management, notifications, plugins

User/group assignment commands, Slack contact point, and plugin listing moved verbatim to [references/authentication-and-access.md](references/authentication-and-access.md).
Load on demand for user, notification, or plugin operations.

## Step 7 — Version control integration

Version control (GitOps) configuration command moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for Git-based dashboard provisioning.

## Step 8 — Recent features

2023-2026 feature list (Enterprise RBAC, SNS channel, AMP auto-discovery, Logs Insights, config API, Terraform) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when recent features matter.

## NEVER do these things

1. **NEVER assume the workspace is ready immediately after creation.**
   The workspace goes through `CREATING` to `ACTIVE`. Data source
   configuration and API calls fail until `ACTIVE`.

2. **NEVER create data sources without correct IAM permissions.** Each
   data source needs specific per-service permissions. Missing
   permissions = silent empty results.

3. **NEVER put AWS credentials in data source JSON.** Use
   `authType: ec2_iam_role` or `sigV4Auth: true` with the workspace
   IAM role.

4. **NEVER assume SAML SSO works without an external IdP.** SAML
   requires an external Identity Provider configured first.

5. **NEVER lose the workspace API key.** The key is shown ONCE. Store
   it in AWS Secrets Manager.

6. **NEVER import dashboard JSON without verifying data source UIDs.**
   Mismatched UIDs cause panels to show "No data" silently.

7. **NEVER mix SAML SSO and IAM Identity Center.** A workspace can use
   one authentication provider, not both.

8. **NEVER grant overly broad IAM permissions.** Scope the workspace
   role to specific services and resources.

9. **NEVER forget notification channels for alerts.** Alert rules
   without contact points silently fire without notifying anyone.

10. **NEVER assume Managed Grafana supports all community plugins.**
    Verify plugin availability before designing dashboards.

## Output format

```text
GRAFANA: <workspace-id> (<workspace-name>, <auth-provider>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Workspace name: <name>
  [✓|✗] Authentication: AWS_SSO (IAM Identity Center) | SAML (IdP: <provider>)
  [✓|✗] SAML IdP metadata: configured (for SAML) | N/A (for AWS_SSO)
  [✓|✗] Permission type: SERVICE_MANAGED | CUSTOM
  [✓|✗] Workspace IAM role: <role-arn> — attached
  [✓|✗] CloudWatch permissions: cloudwatch:GetMetricData, logs:StartQuery
  [✓|✗] Prometheus permissions: aps:QueryMetrics (for AMP data source)
  [✓|✗] Athena permissions: athena:StartQueryExecution, s3:GetObject (for Athena data source)
  [✓|✗] Data sources: CloudWatch | Prometheus | Athena | Timestream | OpenSearch | X-Ray
  [✓|✗] Workspace API key: created (role: <role>)
  [✓|✗] Dashboard provisioning: <count> dashboards imported
  [✓|✗] Notification channels: <list>
  [✓|✗] Workspace endpoint: https://g-<id>.grafana-workspace.<region>.amazonaws.com
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws grafana describe-workspace --workspace-id <workspace-id> --region <region>
  aws grafana list-permissions --workspace-id <workspace-id> --region <region>
  aws iam get-role-policy --role-name <role-name> --policy-name <policy-name>
```

### Worked example — CloudWatch + Prometheus workspace with SSO

```text
GRAFANA: g-aaaa1111 (prod-observability, AWS_SSO)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Workspace name: prod-observability
  [✓] Authentication: AWS_SSO (IAM Identity Center)
  [✓] Permission type: SERVICE_MANAGED
  [✓] Workspace IAM role: arn:aws:iam::123456789012:role/GrafanaWorkspaceRole — attached
  [✓] CloudWatch permissions: cloudwatch:GetMetricData, cloudwatch:ListMetrics, logs:StartQuery, logs:GetQueryResults
  [✓] Prometheus permissions: aps:QueryMetrics, aps:ListWorkspaces
  [✓] Data sources: CloudWatch (default), Prometheus-AMP
  [✓] Workspace API key: created (role: ADMIN, ttl: 86400s)
  [✓] Dashboard provisioning: 3 dashboards imported
  [✓] Notification channels: ops-team-slack
  [✓] Workspace endpoint: https://g-aaaa1111.grafana-workspace.us-east-1.amazonaws.com
  [✓] Tags: Environment=production, Team=ops
VERIFICATION_COMMANDS:
  aws grafana describe-workspace --workspace-id g-aaaa1111 --region us-east-1
  aws grafana list-permissions --workspace-id g-aaaa1111 --region us-east-1
  aws iam get-role-policy --role-name GrafanaWorkspaceRole --policy-name GrafanaDataSourcePermissions
```

## Error handling

Five failure modes (empty results, SAML login, Prometheus query, UID mismatch, key expiry) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when diagnosing a failed deployment.

## References (load on demand)

- [references/data-sources-and-iam.md](references/data-sources-and-iam.md) — per-data-source IAM permissions, data source JSON, and the complete workspace IAM role policy
- [references/authentication-and-access.md](references/authentication-and-access.md) — SSO/SAML setup, API keys, user/group management, notifications, plugins
- [references/advanced-patterns.md](references/advanced-patterns.md) — version control (GitOps) integration and 2023-2026 feature notes
- [references/error-handling.md](references/error-handling.md) — symptom-to-root-cause for empty results, SAML login, Prometheus, UID mismatch, key expiry

## Domain

AWS CloudOps / Amazon Managed Grafana Workspace Provisioning &
Observability Visualization.

## AWS documentation

- **Managed Grafana User Guide** — https://docs.aws.amazon.com/grafana/latest/userguide/what-is-amazon-managed-grafana.html
- **Create a workspace** — https://docs.aws.amazon.com/grafana/latest/userguide/AMG-get-started.html
- **Data sources** — https://docs.aws.amazon.com/grafana/latest/userguide/AMG-datasources.html
- **SAML authentication** — https://docs.aws.amazon.com/grafana/latest/userguide/AMG-authentication.html
- **IAM Identity Center** — https://docs.aws.amazon.com/grafana/latest/userguide/AMG-IC-manage-users-groups.html
- **Workspace role** — https://docs.aws.amazon.com/grafana/latest/userguide/AMG-and-IAM.html
- **API keys** — https://docs.aws.amazon.com/grafana/latest/userguide/AMG-admin-permissions.html
- **Dashboard provisioning** — https://docs.aws.amazon.com/grafana/latest/userguide/AMG-dashboard-export-import.html
- **Grafana API reference** — https://docs.aws.amazon.com/grafana/latest/userguide/Using-Grafana-API.html
- **CloudWatch data source** — https://docs.aws.amazon.com/grafana/latest/userguide/AMG-data-source-CloudWatch.html
