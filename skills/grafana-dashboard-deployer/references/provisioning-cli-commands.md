# Provisioning CLI Commands — Grafana Dashboard Deployer

Full copy-pasteable CLI command sequence for all provisioning steps.
Variables to substitute: `<workspace-name>`, `<workspace-id>`,
`<region>`, `<account-id>`, `<role-name>`, `<amp-id>`, `<kms-key-id>`.

## Step 0: Prerequisites check

```bash
# Confirm caller identity
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Confirm IAM Identity Center is enabled (for AWS_SSO auth)
aws sso-admin list-instances --query 'Instances[*].IdentityStoreId' --output text

# Confirm region
REGION=$(aws configure get region)
echo "Region: $REGION"

# Confirm AMP workspace is ACTIVE (if Prometheus data source)
aws amps list-workspaces --query 'workspaces[?status.statusCode==`ACTIVE`].[workspaceId,alias]' --output table

# Confirm OpenSearch domain (if OpenSearch data source)
aws opensearch list-domain-names --query 'DomainNames[*].DomainName' --output table

# Confirm SNS topic exists (for alert contact points)
aws sns list-topics --query 'Topics[*].TopicArn' --output table

# Confirm KMS key exists (for workspace encryption)
aws kms describe-key --key-id alias/<grafana-alias> \
  --query 'KeyMetadata.[KeyId,KeyState,Enabled]' --output text
```

## Step 1: Create customer-managed IAM role for data source access

```bash
# Trust policy for Amazon Managed Grafana
aws iam create-role \
  --role-name GrafanaDataSourceRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow","Principal": {"Service": "grafana.amazonaws.com"},"Action": "sts:AssumeRole"}]
  }'

# Inline policy with read permissions for each data source type
aws iam put-role-policy \
  --role-name GrafanaDataSourceRole \
  --policy-name GrafanaDataSourceRead \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {"Effect": "Allow","Action": ["cloudwatch:GetMetricData","cloudwatch:GetMetricStatistics","cloudwatch:ListMetrics"],"Resource": "*"},
      {"Effect": "Allow","Action": ["logs:DescribeLogGroups","logs:GetLogEvents","logs:StartQuery","logs:GetQueryResults"],"Resource": "*"},
      {"Effect": "Allow","Action": ["aps:GetLabels","aps:GetMetricMetadata","aps:GetSeries","aps:QueryMetrics"],"Resource": "arn:aws:aps:<region>:<account-id>:workspace/<amp-id>"},
      {"Effect": "Allow","Action": ["timestream:Select","timestream:DescribeEndpoints"],"Resource": "*"},
      {"Effect": "Allow","Action": ["xray:GetTraceSummaries","xray:GetTraceGraph","xray:GetSamplingRules"],"Resource": "*"},
      {"Effect": "Allow","Action": ["es:ESHttpGet","es:ESHttpHead"],"Resource": "arn:aws:es:<region>:<account-id>:domain/<domain>/*"},
      {"Effect": "Allow","Action": ["sns:Publish"],"Resource": "arn:aws:sns:<region>:<account-id>:<topic-name>"}
    ]
  }'
```

## Step 2: Create AMP workspace (if Prometheus data source)

```bash
aws amps create-workspace \
  --workspace-name <amp-name> \
  --alias <amp-alias> \
  --kms-key-arn arn:aws:kms:<region>:<account-id>:key/<kms-key-id>

# Wait for ACTIVE
aws amps describe-workspace --workspace-id <amp-id> \
  --query 'workspace.status.statusCode' --output text
```

## Step 3: Create the Grafana workspace

```bash
aws grafana create-workspace \
  --workspace-name <workspace-name> \
  --account-access-type CURRENT_ACCOUNT \
  --authentication-providers AWS_SSO \
  --permission-type CUSTOMER_MANAGED \
  --data-sources CLOUDWATCH PROMETHEUS XRAY \
  --grafana-version 10.4 \
  --description "Production observability workspace"

# Capture workspace ID
WORKSPACE_ID=$(aws grafana list-workspaces \
  --query 'workspaces[?name==`<workspace-name>`].id' --output text)
echo "Workspace ID: $WORKSPACE_ID"
```

## Step 4: Create workspace API key for dashboard deployment

```bash
GRAFANA_KEY=$(aws grafana create-workspace-api-key \
  --workspace-id $WORKSPACE_ID \
  --key-name deploy-key \
  --key-role ADMIN \
  --seconds-to-live 3600 \
  --query 'key' --output text)

echo "API Key created (expires in 1 hour)"
```

## Step 5: Get workspace endpoint

```bash
WORKSPACE_ENDPOINT=$(aws grafana describe-workspace \
  --workspace-id $WORKSPACE_ID \
  --query 'workspace.endpoint' --output text)

echo "Grafana URL: https://$WORKSPACE_ENDPOINT"
```

## Step 6: Import dashboard via Grafana HTTP API

```bash
# Create dashboard JSON
cat > /tmp/dashboard.json << 'EOF'
{
  "dashboard": {
    "title": "Production Observability",
    "schemaVersion": 39,
    "refresh": "30s",
    "time": {"from": "now-6h", "to": "now"},
    "templating": {
      "list": [
        {"name": "datasource", "type": "datasource", "query": "cloudwatch"},
        {"name": "region", "type": "query", "datasource": "$datasource", "query": "regions()"}
      ]
    },
    "panels": [
      {
        "type": "timeseries", "title": "CPU Utilization",
        "datasource": "$datasource",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "targets": [{"namespace": "AWS/EC2", "metricName": "CPUUtilization", "statistics": ["Average"]}]
      }
    ]
  },
  "overwrite": true
}
EOF

# Import via API
curl -X POST \
  -H "Authorization: Bearer $GRAFANA_KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/dashboard.json \
  https://$WORKSPACE_ENDPOINT/api/dashboards/db
```

## Step 7: Configure alert rules via Grafana HTTP API

```bash
# Create alert rule
cat > /tmp/alert-rule.json << 'EOF'
{
  "uid": "cpu-high",
  "title": "CPU Utilization High",
  "condition": "B",
  "data": [
    {"refId": "A", "datasourceUid": "cloudwatch-uid", "model": {"namespace": "AWS/EC2", "metricName": "CPUUtilization", "statistics": ["Average"]}},
    {"refId": "B", "model": {"expression": "$A > 85", "type": "threshold"}}
  ],
  "for": "5m",
  "labels": {"severity": "warning", "team": "platform"}
}
EOF

curl -X POST \
  -H "Authorization: Bearer $GRAFANA_KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/alert-rule.json \
  https://$WORKSPACE_ENDPOINT/api/v1/provisioning/alert-rules
```

## Step 8: Configure contact point (SNS)

```bash
cat > /tmp/contact-point.json << 'EOF'
{
  "name": "sns-platform",
  "type": "sns",
  "settings": {
    "topic": "arn:aws:sns:us-east-1:123456789012:grafana-alerts",
    "authProvider": "aws_iam",
    "region": "us-east-1"
  }
}
EOF

curl -X POST \
  -H "Authorization: Bearer $GRAFANA_KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/contact-point.json \
  https://$WORKSPACE_ENDPOINT/api/v1/provisioning/contact-points
```

## Step 9: Configure notification policy

```bash
cat > /tmp/notification-policy.json << 'EOF'
{
  "routes": [
    {"receiver": "sns-platform", "object_matchers": [["team", "=", "platform"]]},
    {"receiver": "sns-platform", "object_matchers": [["severity", "=", "critical"]]}
  ]
}
EOF

curl -X PUT \
  -H "Authorization: Bearer $GRAFANA_KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/notification-policy.json \
  https://$WORKSPACE_ENDPOINT/api/v1/provisioning/policies
```

## Verification

```bash
aws grafana describe-workspace --workspace-id <workspace-id>
aws grafana list-workspaces
aws amps describe-workspace --workspace-id <amp-id>
aws iam get-role --role-name GrafanaDataSourceRole
aws iam get-role-policy --role-name GrafanaDataSourceRole --policy-name GrafanaDataSourceRead
```

## Terraform equivalent

```hcl
# AMP workspace (for Prometheus data source)
resource "aws_prometheus_workspace" "amp" {
  alias = "prod-metrics"
}

# IAM role for Grafana data source access
resource "aws_iam_role" "grafana" {
  name = "GrafanaDataSourceRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{Effect = "Allow", Principal = {Service = "grafana.amazonaws.com"}, Action = "sts:AssumeRole"}]
  })
}

resource "aws_iam_role_policy" "grafana_datasource" {
  name = "GrafanaDataSourceRead"
  role = aws_iam_role.grafana.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {Effect = "Allow", Action = ["cloudwatch:GetMetricData", "cloudwatch:ListMetrics", "logs:DescribeLogGroups"], Resource = "*"},
      {Effect = "Allow", Action = ["aps:QueryMetrics"], Resource = aws_prometheus_workspace.amp.arn}
    ]
  })
}

# Managed Grafana workspace
resource "aws_grafana_workspace" "workspace" {
  name                     = "prod-observability"
  account_access_type      = "CURRENT_ACCOUNT"
  authentication_providers = ["AWS_SSO"]
  permission_type          = "CUSTOMER_MANAGED"
  data_sources             = ["CLOUDWATCH", "PROMETHEUS", "XRAY"]
  grafana_version          = "10.4"
  description              = "Production observability workspace"

  tags = {
    Environment = "production"
    Workload    = "observability"
  }
}
```
