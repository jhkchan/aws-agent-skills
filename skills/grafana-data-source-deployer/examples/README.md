# End-to-End Example: Grafana Data Source Deployment

A walkthrough showing how to use the `grafana-data-source-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a Managed Grafana workspace with CloudWatch and
Prometheus (AMP) data sources using IAM Identity Center authentication.
The workspace needs per-service IAM permissions for both data sources.
The deployment needs:

- Workspace name: prod-observability
- Authentication: IAM Identity Center (AWS_SSO)
- Permission type: SERVICE_MANAGED
- Data sources: CloudWatch (metrics + logs), Prometheus (AMP)
- Workspace IAM role: GrafanaWorkspaceRole
- Region: us-east-1
- Account: 123456789012

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-grafana-data-source
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Grafana workspace with CloudWatch and Prometheus
      data sources. Use IAM Identity Center."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a grafana workspace"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

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

---

## Step 3 — Provisioning commands

### 3a. Create workspace IAM role with per-service permissions

```bash
# Create trust policy
WORKSPACE_ROLE_ARN=$(aws iam create-role \
  --role-name GrafanaWorkspaceRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"grafana.amazonaws.com"},"Action":"sts:AssumeRole"}]}' \
  --query 'Role.Arn' --output text)

# Attach permissions for CloudWatch + Prometheus
aws iam put-role-policy \
  --role-name GrafanaWorkspaceRole \
  --policy-name GrafanaDataSourcePermissions \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {"Effect":"Allow","Action":["cloudwatch:ListMetrics","cloudwatch:GetMetricData","cloudwatch:GetMetricStatistics","cloudwatch:DescribeAlarms","logs:DescribeLogGroups","logs:StartQuery","logs:GetQueryResults"],"Resource":"*"},
      {"Effect":"Allow","Action":["aps:QueryMetrics","aps:ListWorkspaces","aps:DescribeWorkspace","aps:GetLabels","aps:GetSeries"],"Resource":"*"}
    ]
  }'
```

### 3b. Create the Grafana workspace

```bash
WORKSPACE_ID=$(aws grafana create-workspace \
  --workspace-name prod-observability \
  --account-access-type CURRENT_ACCOUNT \
  --authentication-provider AWS_SSO \
  --permission-type SERVICE_MANAGED \
  --workspace-role-arn "$WORKSPACE_ROLE_ARN" \
  --data-sources CLOUDWATCH PROMETHEUS \
  --description "Production observability Grafana workspace" \
  --region us-east-1 \
  --query 'workspace.id' --output text)

# Wait for ACTIVE status
aws grafana describe-workspace \
  --workspace-id "$WORKSPACE_ID" \
  --query 'workspace.status' --region us-east-1
# Expected: ACTIVE
```

### 3c. Create API key and add data sources

```bash
ENDPOINT="https://g-${WORKSPACE_ID}.grafana-workspace.us-east-1.amazonaws.com"

# Create API key
API_KEY=$(aws grafana create-workspace-api-key \
  --workspace-id "$WORKSPACE_ID" \
  --key-name "datasource-setup" \
  --key-role ADMIN \
  --seconds-to-live 3600 --region us-east-1 \
  --query 'key' --output text)

# Add CloudWatch data source
curl -s -X POST "$ENDPOINT/api/datasources" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d '{"name":"CloudWatch-prod","type":"cloudwatch","access":"proxy","jsonData":{"authType":"ec2_iam_role","defaultRegion":"us-east-1"},"isDefault":true}'

# Add Prometheus (AMP) data source
curl -s -X POST "$ENDPOINT/api/datasources" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d '{"name":"Prometheus-AMP","type":"prometheus","access":"proxy","url":"https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-aaa111/api/v1","jsonData":{"httpMethod":"POST","sigV4Auth":true,"sigV4AuthType":"workspace","sigV4Region":"us-east-1"}}'
```

### 3d. Import dashboards and configure notifications

```bash
# Import dashboards
curl -s -X POST "$ENDPOINT/api/dashboards/db" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d @overview.json

curl -s -X POST "$ENDPOINT/api/dashboards/db" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d @metrics.json

# Configure Slack notification channel
curl -s -X POST "$ENDPOINT/api/v1/provisioning/contact-points" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d '{"name":"ops-team-slack","type":"slack","settings":{"url":"https://hooks.slack.com/services/xxx","channel":"#ops-alerts"}}'
```

---

## Step 4 — Post-deployment verification

```bash
# Workspace status — should be ACTIVE
aws grafana describe-workspace \
  --workspace-id "$WORKSPACE_ID" \
  --query 'workspace.{Status:status,Endpoint:endpoint,Auth:authenticationProviders}' \
  --region us-east-1

# Verify data sources via Grafana API
curl -s "$ENDPOINT/api/datasources" \
  -H "Authorization: Bearer $API_KEY" | \
  jq '.[] | {Name:name,Type:type,UID:uid}'

# Verify workspace IAM role permissions
aws iam get-role-policy \
  --role-name GrafanaWorkspaceRole \
  --policy-name GrafanaDataSourcePermissions \
  --query 'PolicyDocument.Statement[*].Action' --output table
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| IAM permissions | No role or generic role | Per-service scoped permissions | Missing perms = silent empty results |
| Data source auth | Hardcoded credentials | authType: ec2_iam_role / sigV4Auth | Security best practice; uses workspace role |
| Workspace status | Assumes immediate availability | Waits for ACTIVE before configuring API | API calls fail on non-ACTIVE workspace |
| Data source UID | Not verified | UID match checked for dashboard JSON | Mismatched UID = "No data" silently |
| API key TTL | No TTL or forgotten | Appropriate seconds-to-live | Keys expire; plan rotation |
| Notification channels | Not configured | Contact points created before alerts | Alerts without contact points silently fire |

---

## Related artifacts

- **Skill definition:** `skills/grafana-data-source-deployer/SKILL.md`
- **Data sources and IAM guide:** `skills/grafana-data-source-deployer/references/data-sources-and-iam.md`
- **Authentication and access guide:** `skills/grafana-data-source-deployer/references/authentication-and-access.md`
- **Slash command:** `commands/aws/deploy-grafana-data-source.md`
- **Eval suite:** `skills/grafana-data-source-deployer/evals/evals.json`
- **Legacy test cases:** `skills/grafana-data-source-deployer/eval/test-cases.yaml`
