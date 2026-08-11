# End-to-End Example: Production Grafana Workspace with CloudWatch + Alerting

A walkthrough showing how to use the `grafana-dashboard-deployer` skill
from invocation through verification. Mirrors the structured-eval pattern
of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an Amazon Managed Grafana workspace for production
observability. The workspace needs:

- IAM Identity Center (AWS_SSO) authentication
- Customer-managed IAM role for CloudWatch read access
- CloudWatch data source (us-east-1, us-west-2)
- Grafana version 10.4
- Dashboard with 12 panels (EC2, Lambda, RDS) using templating variables
- Alert rules for CPU > 85% and Lambda errors > 5
- SNS notification via arn:aws:sns:us-east-1:123456789012:grafana-alerts

Workspace name: `prod-observability`
Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-grafana-dashboard
```

Then paste the workspace requirements.

### Option B: Natural language

```
You: "Create a Managed Grafana workspace prod-observability in us-east-1.
      IAM Identity Center auth, customer-managed IAM role. CloudWatch data
      source for us-east-1 and us-west-2. Grafana 10.4. Dashboard with 12
      panels for EC2/Lambda/RDS. Alert on CPU > 85% and Lambda errors > 5
      with SNS notification. Account: 123456789012."
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
WORKSPACE: prod-observability
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Workspace: prod-observability, version: 10.4 (Standard)
  [✓] Authentication: AWS_SSO (IAM Identity Center)
  [✓] Permission type: CUSTOMER_MANAGED
  [✓] IAM role: GrafanaDataSourceRole (cloudwatch:GetMetricData, cloudwatch:ListMetrics, logs:DescribeLogGroups)
  [✓] Data source: CloudWatch (regions: us-east-1, us-west-2)
  [✓] Dashboard: Production Observability (12 panels, templating: $region, $datasource)
  [✓] Alert rules: CPU > 85% (5m for), Lambda errors > 5 (5m for)
  [✓] Notification policies: route by severity
  [✓] Contact points: SNS arn:aws:sns:us-east-1:123456789012:grafana-alerts
  [✓] Tags: Environment=production, Workload=observability
VERIFICATION_COMMANDS:
  aws grafana describe-workspace --workspace-id <workspace-id>
  aws iam get-role --role-name GrafanaDataSourceRole
```

---

## Step 3 — Provisioning commands

The skill generates the copy-pasteable CLI sequence (from
`references/provisioning-cli-commands.md`):

```bash
# 1. Create customer-managed IAM role for data source access
aws iam create-role \
  --role-name GrafanaDataSourceRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow","Principal": {"Service": "grafana.amazonaws.com"},"Action": "sts:AssumeRole"}]
  }'

aws iam put-role-policy \
  --role-name GrafanaDataSourceRole \
  --policy-name GrafanaCloudWatchRead \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {"Effect": "Allow","Action": ["cloudwatch:GetMetricData","cloudwatch:GetMetricStatistics","cloudwatch:ListMetrics"],"Resource": "*"},
      {"Effect": "Allow","Action": ["logs:DescribeLogGroups","logs:GetLogEvents","logs:StartQuery","logs:GetQueryResults"],"Resource": "*"}
    ]
  }'

# 2. Create the Grafana workspace
aws grafana create-workspace \
  --workspace-name prod-observability \
  --account-access-type CURRENT_ACCOUNT \
  --authentication-providers AWS_SSO \
  --permission-type CUSTOMER_MANAGED \
  --data-sources CLOUDWATCH \
  --grafana-version 10.4 \
  --description "Production observability workspace"

# 3. Get workspace API key for dashboard import
GRAFANA_KEY=$(aws grafana create-workspace-api-key \
  --workspace-id <workspace-id> \
  --key-name deploy-key \
  --key-role ADMIN \
  --seconds-to-live 3600 \
  --query 'key' --output text)

# 4. Import dashboard via Grafana HTTP API
curl -X POST \
  -H "Authorization: Bearer $GRAFANA_KEY" \
  -H "Content-Type: application/json" \
  -d @dashboard.json \
  https://<workspace-endpoint>/api/dashboards/db
```

---

## Step 4 — Post-deployment verification

```bash
# Workspace status — wait for "ACTIVE"
aws grafana describe-workspace --workspace-id <workspace-id> \
  --query 'workspace.status' --output text

# Verify IAM role and policy
aws iam get-role --role-name GrafanaDataSourceRole
aws iam get-role-policy --role-name GrafanaDataSourceRole --policy-name GrafanaCloudWatchRead

# Verify workspace URL is accessible
curl -s -o /dev/null -w "%{http_code}" https://<workspace-endpoint>/health
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Permission type | SERVICE_MANAGED | CUSTOMER_MANAGED for compliance | Service-managed grants broad read; customer-managed enables least-privilege. |
| IAM role | Omitted (assumes auto) | Explicit role with scoped CW permissions | Without correct IAM, data sources return permission errors on every query. |
| Alerting layers | Just rules | Rules + notification policies + contact points | A rule without a policy or contact point fires but goes nowhere. |
| Dashboard templating | Hardcoded data source | $datasource variable | Hardcoded UIDs break when importing across workspaces. |
| Auth mode | Any | AWS_SSO (IAM Identity Center) recommended | Switching auth modes requires recreating the workspace. |

---

## Related artifacts

- **Skill definition:** `skills/grafana-dashboard-deployer/SKILL.md`
- **Provisioning CLI commands:** `skills/grafana-dashboard-deployer/references/provisioning-cli-commands.md`
- **Data sources and dashboard JSON:** `skills/grafana-dashboard-deployer/references/data-sources-and-dashboard-json.md`
- **Slash command:** `commands/aws/deploy-grafana-dashboard.md`
- **Eval suite:** `skills/grafana-dashboard-deployer/evals/evals.json`
- **Legacy test cases:** `skills/grafana-dashboard-deployer/eval/test-cases.yaml`
