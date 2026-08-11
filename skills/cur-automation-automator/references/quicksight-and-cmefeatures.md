# QuickSight, Cost Categories, tags, and CUR 2.0 reference

Loaded on demand when the skill needs the QuickSight setup pattern,
Cost Category structure, tag activation, or CUR 2.0 / BCM Data Exports
details.

## QuickSight integration

### Account edition check

```bash
aws quicksight describe-account --aws-account-id 111111111111 \
  --query 'Account.AccountEdition'
```

- `STANDARD` — no scheduled SPICE refresh on Athena datasets. Manual
  refresh only. Dashboard data is stale within an hour.
- `ENTERPRISE` — up to 32 scheduled refreshes per dataset, hourly.
  Required for production cost dashboards.
- `ENTERPRISE_AND_Q` — adds Q (natural-language) on top of Enterprise.

### Upgrade to Enterprise

```bash
aws quicksight update-account-subscription \
  --aws-account-id 111111111111 \
  --edition ENTERPRISE \
  --contact-number "+1-555-0100" \
  --email finops@example.com
```

### Data source on Athena (CloudFormation)

```yaml
QuickSightAthenaSource:
  Type: AWS::QuickSight::DataSource
  Properties:
    AwsAccountId: !Ref AWS::AccountId
    DataSourceId: cur-athena-source
    Name: CUR-Athena
    Type: ATHENA
    DataSourceParameters:
      AthenaParameters:
        WorkGroup: finops-cur
    SslProperties:
      DisableSsl: false
    Permissions:
      - Principal: !Sub "arn:aws:quicksight:${AWS::Region}:${AWS::AccountId}:user/default/admin"
        Actions:
          - quicksight:DescribeDataSource
          - quicksight:DescribeDataSourcePermissions
          - quicksight:PassDataSource
          - quicksight:UpdateDataSource
          - quicksight:DeleteDataSource
          - quicksight:UpdateDataSourcePermissions
```

### SPICE dataset on CUR with row-level security

```yaml
CURDataset:
  Type: AWS::QuickSight::DataSet
  Properties:
    AwsAccountId: !Ref AWS::AccountId
    DataSetId: cur-hourly-dataset
    Name: cur-hourly
    ImportMode: SPICE
    PhysicalTableMap:
      cur:
        RelationalTable:
          DataSourceArn: !Ref QuickSightAthenaSource
          Catalog: AwsDataCatalog
          Schema: prod_cur
          Name: cur_hourly
          InputColumns:
            - Name: lineitem_usageaccountid
              Type: STRING
            - Name: product_servicename
              Type: STRING
            - Name: lineitem_unblendedcost
              Type: DECIMAL
    LogicalTableMap:
      cur:
        Source:
          PhysicalTableId: cur
        DataTransforms:
          - FilterOperation:
              ConditionExpression: "day >= '2026/07/01'"
    Permissions:
      - Principal: !Sub "arn:aws:quicksight:${AWS::Region}:${AWS::AccountId}:user/default/admin"
        Actions:
          - quicksight:DescribeDataSet
          - quicksight:UpdateDataSet
          - quicksight:DeleteDataSet
```

### Scheduled refresh (Enterprise only)

```bash
aws quicksight create-ingestion \
  --aws-account-id 111111111111 \
  --data-set-id cur-hourly-dataset \
  --ingestion-id daily-refresh
```

For scheduled refresh, use the QuickSight console (cron-based schedule
UI) or the AWS CLI `update-data-set` with `ScheduleRefreshProperties`.

## Cost Categories (chargeback)

### Cost Category structure

```yaml
AWSCostCategoryChargeback:
  Type: AWS::CE::CostCategoryDefinition
  Properties:
    Name: chargeback-by-env
    RuleVersion: CostCategoryExpression.v1
    Rules:
      - Value: production
        Rules:
          - Dimensions:
              Key: TAG
              Values: ["env$prod"]
              MatchOptions: [EQUALS]
      - Value: staging
        Rules:
          - Dimensions:
              Key: TAG
              Values: ["env$staging"]
              MatchOptions: [EQUALS]
      - Value: Uncategorized
        Rules:
          - Dimensions:
              Key: TAG
              Values: ["env$prod", "env$staging"]
              MatchOptions: [ABSENT_MATCH]  # NOT in either prod/staging
    DefaultValue: Uncategorized
```

### Rule type matrix

| Type | Use case | Example |
|---|---|---|
| `EQUAL` | Split a shared cost equally across N accounts | Shared KMS key split across all linked accounts |
| `PROPORTIONAL` | Split by each account's % of total spend | Shared Datadog subscription split by EC2 spend share |
| `FIXED` | Charge a fixed monthly fee per account | Platform support fee: $5k/month per BU |
| `ATTRIBUTES` | Group by tag value or dimension | env=prod → 100% of those resources |

## Cost-allocation tag activation

### Activation is payer-only and non-backfilling

```bash
# PAYER ACCOUNT ONLY
aws ce update-cost-allocation-tags-status-upstream \
  --tag-keys "env" "team" "cost-center" "project" \
  --status "Active" \
  --profile payer-profile
```

Rules:
- Activation is **payer-only**. Linked accounts get `AccessDenied`.
- Activation is **NOT retroactive**. CUR data delivered BEFORE
  activation has no tag data; CUR data delivered AFTER activation has
  the tag column.
- Activation is **idempotent**. Re-activating an already-active tag is
  a no-op.
- **1-hour cooldown** after deactivation before re-activation.

### Listing currently activated tags

```bash
aws ce list-cost-allocation-tags --status Active
```

## CUR 2.0 / Split Cost Allocation Data (SCAD)

### Enable SCAD (payer console or API)

```bash
# PAYER ACCOUNT ONLY
aws ce update-cost-allocation-tags-status-upstream \
  --tag-keys "aws:ecs:serviceName" \
              "aws:ecs:clusterName" \
              "aws:eks:clusterName" \
              "aws:lambda:functionName" \
  --status "Active"
```

### SCAD columns added to CUR

| Column | Example value |
|---|---|
| `split_cost_allocation_data_service` | `AmazonEKS` |
| `split_cost_allocation_data_resource` | `default/my-deployment/abc-pod-xyz` |
| `split_cost_allocation_data_usage` | `15.5 vCPU-hours` |
| `split_cost_allocation_data_net_unblended_cost` | `1.42` |

### EKS Container Insights prerequisite

```bash
aws eks update-cluster-config \
  --name prod-eks-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit"],"enabled":true}]}'

# Enable Container Insights on the cluster
aws eks create-addon \
  --cluster-name prod-eks-cluster \
  --addon-name amazon-cloudwatch-observability \
  --configuration-values '{"agent":{"cpuLimit":"200m","memoryLimit":"800Mi"}}'
```

Without Container Insights, SCAD produces empty split-cost columns for
24-48 hours before erroring.

## BCM Data Exports (modern CUR 2.0 API)

### Create export

```bash
aws bcm-data-exports create-export \
  --export '{
    "Name": "cur-2-hourly-with-sca",
    "ExportStatus": "ACTIVE",
    "DestinationConfigurations": {
      "S3Destination": {
        "S3Bucket": "prod-cur-bucket",
        "S3Prefix": "cur-2/",
        "S3Region": "us-east-1",
        "S3OutputType": "PARQUET"
      }
    },
    "DataQuery": {
      "QueryStatement": "SELECT \"identity_lineitemid\" AS \"line_item_id\", \"lineitem_usageaccountid\" AS \"usage_account_id\", \"lineitem_unblendedcost\" AS \"unblended_cost\" FROM COST_AND_USAGE_REPORT_ACCOUNT_DAILY",
      "TableConfigurations": {
        "COST_AND_USAGE_REPORT": {
          "TIME_GRANULARITY": "HOURLY",
          "INCLUDE_RESOURCES": "TRUE",
          "INCLUDE_SPLIT_COST_ALLOCATION_DATA": "TRUE"
        }
      }
    }
  }'
```

### Table names supported by BCM Data Exports

| Table | Granularity | Use case |
|---|---|---|
| `COST_AND_USAGE_REPORT_ACCOUNT_DAILY` | Daily, per account | Legacy CUR 1.0 equivalent |
| `COST_AND_USAGE_REPORT_ACCOUNT_HOURLY` | Hourly, per account | Resource-level + SCAD |
| `COST_AND_USAGE_REPORT_ORG_DAILY` | Daily, org-wide | Consolidated billing |
| `COST_AND_USAGE_REPORT_ORG_HOURLY` | Hourly, org-wide | Org-wide resource-level |
| `MAX` (compute savings plan) | Real-time | Compute Savings Plan recommendation |

### Service-linked role

The `AWSServiceRoleForBCMDataExports` SLR is auto-created on first
`create-export` call. To pre-create:

```bash
aws iam create-service-linked-role \
  --aws-service-name bcm-data-exports.amazonaws.com
```

If a Service Control Policy denies `iam:CreateServiceLinkedRole`, the
SLR creation fails silently and the export sits in `INACTIVE` state.

## Amazon Q cost analysis

### Prerequisites

1. Q Business Pro subscription ($20/user/month, payer-scoped).
2. Q Business application in the payer account.
3. CUR connector (Q Business data source) configured with read-only
   access to the Athena workgroup.

### When to use Q vs Athena named queries

| Use case | Tool |
|---|---|
| "Show me top 10 services this month" | Athena named query (deterministic, fast) |
| "Why did my EC2 cost spike last week?" | Q (exploratory, NL → SQL) |
| "Which accounts have unused EC2?" | Athena named query |
| "What changed in my cost trend?" | Q (analytical, NL → SQL + narrative) |
| Daily Slack post of top spenders | Lambda + Athena (programmatic) |
| Exec boardroom walkthrough | Q (NL questions in real time) |

Q is not a replacement for Athena pipelines — it is an ad-hoc
exploration layer. Use both: Athena for repeatable pipelines, Q for
exploratory analysis.
