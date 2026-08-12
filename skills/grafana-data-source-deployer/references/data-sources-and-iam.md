# Data Sources and IAM — Grafana Data Source Deployer

Deep reference on data source configuration (CloudWatch, Prometheus/
AMP, Athena, Timestream, OpenSearch, X-Ray), per-service IAM
permissions for the workspace role, data source provisioning via the
Grafana HTTP API, and common data source pitfalls. Loaded on demand
by the skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## CloudWatch data source

### Required IAM permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:ListMetrics",
        "cloudwatch:GetMetricData",
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:DescribeAlarms",
        "cloudwatch:DescribeAlarmHistory",
        "cloudwatch:DescribeAlarmsForMetric",
        "cloudwatch:GetMetricWidgetImage",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:StartQuery",
        "logs:StopQuery",
        "logs:GetQueryResults"
      ],
      "Resource": "*"
    }
  ]
}
```

### Data source JSON

```json
{
  "name": "CloudWatch-prod",
  "type": "cloudwatch",
  "access": "proxy",
  "jsonData": {
    "authType": "ec2_iam_role",
    "defaultRegion": "us-east-1",
    "customMetricsNamespaces": "MyApp/Custom",
    "logGroups": [
      { "name": "/aws/lambda/my-function", "arn": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/my-function" }
    ]
  },
  "isDefault": true
}
```

**Key:** `authType: ec2_iam_role` tells Grafana to use the workspace
IAM role. Do NOT put AWS access keys in the data source JSON.

### CloudWatch Metrics vs Logs

The CloudWatch data source in Grafana supports both Metrics and Logs:
- **Metrics:** uses `cloudwatch:ListMetrics` and
  `cloudwatch:GetMetricData` to query metric data.
- **Logs:** uses `logs:StartQuery` and `logs:GetQueryResults` to run
  CloudWatch Logs Insights queries.

Both sets of permissions are needed if you want both metrics and logs
panels.

## Prometheus (AMP) data source

### Required IAM permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "aps:QueryMetrics",
        "aps:ListWorkspaces",
        "aps:DescribeWorkspace",
        "aps:GetLabels",
        "aps:GetSeries",
        "aps:GetMetricMetadata"
      ],
      "Resource": "*"
    }
  ]
}
```

### Data source JSON

```json
{
  "name": "Prometheus-AMP",
  "type": "prometheus",
  "access": "proxy",
  "url": "https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-aaa111/api/v1",
  "jsonData": {
    "httpMethod": "POST",
    "sigV4Auth": true,
    "sigV4AuthType": "workspace",
    "sigV4Region": "us-east-1"
  }
}
```

**Key:** `sigV4Auth: true` with `sigV4AuthType: workspace` tells Grafana
to use the workspace IAM role for SigV4 signing. The `url` must point
to the AMP workspace's query endpoint.

### AMP workspace URL format

```text
https://aps-workspaces.<region>.amazonaws.com/workspaces/<workspace-id>/api/v1
```

Find the workspace ID:

```bash
aws amp list-workspaces --region us-east-1 \
  --query 'workspaces[*].{Id:workspaceId,Status:status,Alias:alias}' \
  --output table
```

## Athena data source

### Required IAM permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "athena:StartQueryExecution",
        "athena:GetQueryResults",
        "athena:StopQueryExecution",
        "athena:GetWorkGroup",
        "athena:ListDataCatalogs",
        "athena:ListDatabases",
        "athena:GetDatabase",
        "athena:ListTableMetadata",
        "athena:GetTableMetadata"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": "arn:aws:s3:::athena-query-results-*/*"
    },
    {
      "Effect": "Allow",
      "Action": ["glue:GetDatabase", "glue:GetDatabases", "glue:GetTable", "glue:GetTables", "glue:GetPartition"],
      "Resource": "*"
    }
  ]
}
```

### Data source JSON

```json
{
  "name": "Athena-prod",
  "type": "athena",
  "access": "proxy",
  "jsonData": {
    "authType": "default",
    "defaultRegion": "us-east-1",
    "catalog": "AwsDataCatalog",
    "database": "default",
    "workgroup": "primary",
    "outputLocation": "s3://athena-query-results-123456789012/"
  }
}
```

**Key:** `outputLocation` is the S3 bucket where Athena stores query
results. The workspace role must have `s3:GetObject` on this bucket.

## Timestream data source

### Required IAM permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "timestream:DescribeEndpoints",
        "timestream:SelectQuery",
        "timestream:CancelQuery",
        "timestream:ListMeasures",
        "timestream:ListDatabases",
        "timestream:ListTables",
        "timestream:DescribeDatabase",
        "timestream:DescribeTable"
      ],
      "Resource": "*"
    }
  ]
}
```

### Data source JSON

```json
{
  "name": "Timestream-prod",
  "type": "timestream",
  "access": "proxy",
  "jsonData": {
    "authType": "default",
    "defaultRegion": "us-east-1",
    "defaultDatabase": "YourDatabase",
    "defaultTable": "YourTable"
  }
}
```

## OpenSearch data source

### Required IAM permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "es:ESHttpGet",
        "es:ESHttpPost",
        "es:EShttpPut",
        "es:EShttpDelete",
        "es:DescribeDomain",
        "es:ListDomainNames"
      ],
      "Resource": "arn:aws:es:us-east-1:123456789012:domain/my-domain/*"
    }
  ]
}
```

### Data source JSON

```json
{
  "name": "OpenSearch-prod",
  "type": "elasticsearch",
  "access": "proxy",
  "url": "https://search-my-domain.us-east-1.es.amazonaws.com",
  "database": "log-index-*",
  "jsonData": {
    "esVersion": "7.10",
    "timeField": "@timestamp",
    "interval": "Daily",
    "sigV4Auth": true,
    "sigV4AuthType": "workspace",
    "sigV4Region": "us-east-1"
  }
}
```

## X-Ray data source

### Required IAM permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "xray:BatchGetTraces",
        "xray:GetTraceSummaries",
        "xray:GetGroups",
        "xray:GetGroup",
        "xray:GetSamplingRules",
        "xray:GetSamplingTargets",
        "xray:GetTimeSeriesServiceStatistics",
        "xray:GetServiceGraph"
      ],
      "Resource": "*"
    }
  ]
}
```

## Complete workspace IAM role policy

For a workspace using ALL data sources:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:ListMetrics", "cloudwatch:GetMetricData",
        "cloudwatch:GetMetricStatistics", "cloudwatch:DescribeAlarms",
        "logs:DescribeLogGroups", "logs:StartQuery", "logs:GetQueryResults"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "aps:QueryMetrics", "aps:ListWorkspaces",
        "aps:DescribeWorkspace", "aps:GetLabels", "aps:GetSeries"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "athena:StartQueryExecution", "athena:GetQueryResults",
        "athena:StopQueryExecution", "athena:GetWorkGroup",
        "glue:GetTable", "glue:GetDatabase"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": "arn:aws:s3:::athena-query-results-*/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "timestream:DescribeEndpoints", "timestream:SelectQuery",
        "timestream:ListMeasures", "timestream:ListDatabases"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "xray:BatchGetTraces", "xray:GetTraceSummaries",
        "xray:GetGroups", "xray:GetSamplingRules"
      ],
      "Resource": "*"
    }
  ]
}
```

## Data source provisioning via Grafana API

### List existing data sources

```bash
curl -s "$ENDPOINT/api/datasources" \
  -H "Authorization: Bearer $API_KEY" | \
  jq '.[].{Name:name,Type:type,UID:uid}'
```

### Get a data source UID (needed for dashboard JSON)

```bash
curl -s "$ENDPOINT/api/datasources/name/CloudWatch-prod" \
  -H "Authorization: Bearer $API_KEY" | jq '.uid'
```

### Update a data source

```bash
curl -s -X PUT "$ENDPOINT/api/datasources/uid/<uid>" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"CloudWatch-prod","type":"cloudwatch","jsonData":{"defaultRegion":"us-west-2"}}'
```

### Delete a data source

```bash
curl -s -X DELETE "$ENDPOINT/api/datasources/uid/<uid>" \
  -H "Authorization: Bearer $API_KEY"
```

## Common data source pitfalls

1. **Silent empty results from missing IAM permissions.** The #1 data
   source pitfall. The data source appears connected, but queries
   return no data. Always verify per-service permissions.

2. **Wrong AMP workspace URL.** The URL must include the full AMP
   workspace path including `/api/v1`. A partial URL causes query
   failures.

3. **Athena results bucket permissions.** The workspace role needs
   `s3:GetObject` on the Athena results bucket. Without it, Athena
   queries fail with S3 access errors.

4. **SigV4 misconfiguration for Prometheus.** Must set
   `sigV4Auth: true` AND `sigV4AuthType: workspace`. Missing either
   causes authentication failures.

5. **Data source UID mismatch in dashboards.** Dashboard JSON
   references data sources by UID. If the UID doesn't match the
   workspace data source, panels show "No data" silently.

## Terraform examples

```hcl
# Grafana workspace
resource "aws_grafana_workspace" "main" {
  name                     = "prod-observability"
  account_access_type      = "CURRENT_ACCOUNT"
  authentication_provider  = "AWS_SSO"
  permission_type          = "SERVICE_MANAGED"
  data_sources             = ["CLOUDWATCH", "PROMETHEUS"]
  description              = "Production observability"
  workspace_role_arn       = aws_iam_role.grafana.arn

  tags = {
    Environment = "production"
    Team        = "ops"
  }
}

# Workspace IAM role
resource "aws_iam_role" "grafana" {
  name = "GrafanaWorkspaceRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "grafana.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "grafana_permissions" {
  name = "GrafanaDataSourcePermissions"
  role = aws_iam_role.grafana.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:ListMetrics", "cloudwatch:GetMetricData",
          "cloudwatch:GetMetricStatistics", "cloudwatch:DescribeAlarms",
          "logs:DescribeLogGroups", "logs:StartQuery", "logs:GetQueryResults"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "aps:QueryMetrics", "aps:ListWorkspaces",
          "aps:DescribeWorkspace", "aps:GetLabels", "aps:GetSeries"
        ]
        Resource = "*"
      }
    ]
  })
}

# Workspace API key
resource "aws_grafana_workspace_api_key" "cicd" {
  workspace_id   = aws_grafana_workspace.main.id
  key_name       = "ci-cd-provisioning"
  key_role       = "ADMIN"
  seconds_to_live = 86400
}
```
