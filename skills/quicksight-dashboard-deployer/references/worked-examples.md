# Worked Examples — QuickSight Dashboard Deployer

Filled-in CLI configuration examples moved out of the SKILL.md body. Loaded on demand.


## Step 2 — Data source connection: RDS PostgreSQL example

**Create RDS PostgreSQL data source (via VPC connection):**

```bash
aws quicksight create-data-source \
  --aws-account-id 123456789012 \
  --data-source-id ds-rds-prod \
  --name "RDS PostgreSQL Production" \
  --type POSTGRESQL \
  --data-source-parameters '{"PostgreSqlParameters":{"Host":"prod-db.cluster-abc123.us-east-1.rds.amazonaws.com","Port":5432,"Database":"analytics"}}' \
  --credentials '{"CredentialPair":{"Username":"quicksight_reader","Password":"<password>"}}' \
  --vpc-connection-arn "arn:aws:quicksight:us-east-1:123456789012:vpcConnection/vpc-conn-123" \
  --region us-east-1
```


## Step 5 — Dashboard creation and sharing commands

**Create dashboard from analysis:**

```bash
aws quicksight create-dashboard \
  --aws-account-id 123456789012 \
  --dashboard-id "sales-dashboard" \
  --name "Sales Performance Dashboard" \
  --source-entity '{"SourceAnalysis":{"Arn":"arn:aws:quicksight:us-east-1:123456789012:analysis/sales-analysis","DataSetReferences":[{"DataSetPlaceholder":"sales-metrics","DataSetArn":"arn:aws:quicksight:us-east-1:123456789012:dataset/ds-sales-metrics"}]}}' \
  --dashboard-publish-options '{"AdHocFilteringOption":{"AvailabilityStatus":"ENABLED"},"ExportToCSVOption":{"AvailabilityStatus":"ENABLED"}}' \
  --version-description "Initial version" \
  --region us-east-1
```

**Share dashboard with a user:**

```bash
aws quicksight create-dashboard-permission \
  --aws-account-id 123456789012 \
  --dashboard-id "sales-dashboard" \
  --grant-permissions '{"Principal":"arn:aws:quicksight:us-east-1:123456789012:user/default/reader@example.com","Actions":["quicksight:DescribeDashboard","quicksight:ListDashboardVersions","quicksight:QueryDashboard"]}' \
  --region us-east-1
```


## Step 8 — VPC connection and IAM role examples

**Create VPC connection:**

```bash
aws quicksight create-vpc-connection \
  --aws-account-id 123456789012 \
  --vpc-connection-id "vpc-conn-prod" \
  --name "Production VPC Connection" \
  --subnet-ids "subnet-aaa111" "subnet-bbb222" \
  --security-group-ids "sg-quicksight-access" \
  --dns-resolvers "10.0.0.2" \
  --role-arn "arn:aws:iam::123456789012:role/QuickSightVpcRole" \
  --region us-east-1
```

The IAM role must trust `quicksight.amazonaws.com` and have
`ec2:CreateNetworkInterface`, `ec2:DeleteNetworkInterface`, and
`ec2:DescribeNetworkInterfaces` permissions for the specified subnets
and security groups. Wait for status `AVAILABLE` before using in a
data source.

**QuickSight service role trust policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "quicksight.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```


## Step 9 — Namespace and group commands

**Create a namespace (for multi-tenant isolation):**

```bash
aws quicksight create-namespace \
  --aws-account-id 123456789012 \
  --namespace "tenant-a" \
  --identity-store QUICKSIGHT \
  --region us-east-1
```

**Create a group (for group-based RLS):**

```bash
aws quicksight create-group \
  --aws-account-id 123456789012 \
  --namespace default \
  --group-name "east-region-readers" \
  --description "Readers with access to East region data" \
  --region us-east-1
```
