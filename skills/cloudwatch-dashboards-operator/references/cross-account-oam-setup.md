# CloudWatch OAM Cross-Account Setup Reference

Load this reference when implementing cross-account CloudWatch dashboards
via Observability Access Manager (OAM). Covers sink creation, source
account linking, and dashboard configuration for cross-account visibility.

## OAM architecture

```
Monitoring Account (111111111111)
  ┌─────────────────────────────────┐
  │  OAM Sink: org-monitoring-sink   │
  │  Dashboard: cross-account-view   │
  │  @Account dimension filters      │
  └──────────┬──────────────────────┘
             │ OAM Link (MetricLink: true)
             │
  ┌──────────┴──────────┐
  │                     │
  ▼                     ▼
Source Account          Source Account
222222222222             333333333333
(RDS, EC2, Lambda)       (RDS, EC2, Lambda)
```

## Step 1: Create OAM sink in monitoring account

```bash
# Create the sink in the monitoring (aggregator) account
aws oam create-sink \
  --name org-monitoring-sink \
  --tags Environment=prod,Team=platform

# Capture the sink ARN
SINK_ARN=$(aws oam list-sinks \
  --query 'Items[?Name==`org-monitoring-sink`].Arn' \
  --output text)

echo "Sink ARN: $SINK_ARN"
```

## Step 2: Create link from each source account

Run in EACH source account:

```bash
# In source account 222222222222
aws oam create-link \
  --sink-identifier arn:aws:oam:us-east-1:111111111111:sink:org-monitoring-sink \
  --label "prod-app-account" \
  --resource-types '["AWS::CloudWatch::Metric","AWS::Logs::LogGroup","AWS::XRay::Trace"]' \
  --link-configuration '{
    "MetricLinkConfiguration": {
      "Filter": {
        "NamespacePrefixes": ["AWS/", "Application/"]
      }
    }
  }'

# In source account 333333333333
aws oam create-link \
  --sink-identifier arn:aws:oam:us-east-1:111111111111:sink:org-monitoring-sink \
  --label "prod-data-account" \
  --resource-types '["AWS::CloudWatch::Metric","AWS::Logs::LogGroup","AWS::XRay::Trace"]'
```

## Step 3: Verify links

```bash
# In monitoring account
aws oam list-links \
  --query 'Items[].{Label:Label,SourceAccount:SourceAccountArn,Status:LinkStatus,Sink:SinkArn}'
```

Expected output:
```json
[
  {"Label": "prod-app-account", "SourceAccount": "222222222222", "Status": "LINKED", "Sink": "arn:aws:oam:us-east-1:111111111111:sink:org-monitoring-sink"},
  {"Label": "prod-data-account", "SourceAccount": "333333333333", "Status": "LINKED", "Sink": "arn:aws:oam:us-east-1:111111111111:sink:org-monitoring-sink"}
]
```

## Step 4: Create cross-account dashboard

```bash
# Dashboard body with @Account variable
cat > cross-account-rds-overview.json << 'EOF'
{
  "widgets": [
    {
      "type": "metric",
      "x": 0, "y": 0, "width": 24, "height": 6,
      "properties": {
        "title": "RDS CPU - All Accounts",
        "region": "us-east-1",
        "period": 300,
        "stat": "Average",
        "view": "timeSeries",
        "metrics": [
          ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", "${DBInstance}", {"account": "${@Account}"}]
        ],
        "liveData": true
      }
    },
    {
      "type": "metric",
      "x": 0, "y": 6, "width": 24, "height": 6,
      "properties": {
        "title": "Top 20 RDS Instances by CPU (All Accounts)",
        "region": "us-east-1",
        "view": "table",
        "query": "SELECT avg(CPUUtilization) FROM AWS/RDS GROUP BY @Account, DBInstanceIdentifier ORDER BY avg() DESC LIMIT 20"
      }
    },
    {
      "type": "alarm",
      "x": 0, "y": 12, "width": 24, "height": 6,
      "properties": {
        "title": "Cross-Account RDS Alarms",
        "region": "us-east-1",
        "alarms": [
          "arn:aws:cloudwatch:us-east-1:222222222222:alarm:rds-cpu-high-app",
          "arn:aws:cloudwatch:us-east-1:333333333333:alarm:rds-cpu-high-data"
        ]
      }
    }
  ]
}
EOF

# Deploy the dashboard
aws cloudwatch put-dashboard \
  --dashboard-name cross-account-rds-overview \
  --dashboard-body file://cross-account-rds-overview.json
```

## Step 5: IAM permissions for OAM

**Monitoring account IAM role** (the operator creating dashboards):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oam:ListSinks",
        "oam:ListLinks",
        "oam:GetSink",
        "oam:GetLink"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutDashboard",
        "cloudwatch:GetDashboard",
        "cloudwatch:ListDashboards",
        "cloudwatch:DeleteDashboards"
      ],
      "Resource": "*"
    }
  ]
}
```

**Source account IAM role** (for creating the link):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oam:CreateLink",
        "oam:DeleteLink",
        "oam:GetLink",
        "oam:UpdateLink"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "iam:CreateServiceLinkedRole",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "iam:AWSServiceName": "oam.cloudwatch.amazonaws.com"
        }
      }
    }
  ]
}
```

## OAM filter patterns

Limit which metrics flow from source to monitoring account:

```bash
# Only send AWS/ namespace metrics
aws oam update-link \
  --identifier <link-id> \
  --link-configuration '{
    "MetricLinkConfiguration": {
      "Filter": {
        "NamespacePrefixes": ["AWS/"]
      }
    }
  }'

# Only send specific namespaces
aws oam update-link \
  --identifier <link-id> \
  --link-configuration '{
    "MetricLinkConfiguration": {
      "Filter": {
        "NamespacePrefixes": ["AWS/RDS", "AWS/Lambda", "Application/"]
      }
    }
  }'
```

## Organizations integration

For large-scale deployments, use CloudFormation StackSets to deploy OAM
links across all accounts in an OU:

```yaml
# StackSet template for source accounts
Resources:
  OAMLink:
    Type: AWS::Oam::Link
    Properties:
      SinkIdentifier: !Sub "arn:aws:oam:us-east-1:111111111111:sink:org-monitoring-sink"
      Label: !Sub "${AWS::AccountId}"
      ResourceTypes:
        - "AWS::CloudWatch::Metric"
        - "AWS::Logs::LogGroup"
```

Deploy via:
```bash
aws cloudformation create-stack-set \
  --stack-set-name oam-link-deployment \
  --template-body file://oam-link.yaml \
  --permission-model SERVICE_MANAGED \
  --capabilities CAPABILITY_IAM \
  --auto-deployment '{"Enabled": true, "RetainStacksOnAccountRemoval": false}'

aws cloudformation create-stack-instances \
  --stack-set-name oam-link-deployment \
  --deployment-targets OrganizationalUnitIds=["ou-xxxx-xxxxxxxx"] \
  --regions us-east-1
```

## Verification commands

```bash
# Verify sink is receiving data
aws oam get-sink \
  --identifier org-monitoring-sink \
  --query '{Name:Name,Arn:Arn,State:State}'

# Verify link status for each source account
aws oam list-links \
  --query 'Items[].{Account:Label,Source:SourceAccountArn,Status:LinkStatus,Metrics:ResourceTypes}'

# Test cross-account metric visibility
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=prod-db \
  --statistics Average \
  --period 300 \
  --start-time 2026-08-05T00:00:00Z \
  --end-time 2026-08-05T01:00:00Z \
  --include-linked-accounts
```
