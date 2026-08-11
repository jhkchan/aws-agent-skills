# Deployment CLI commands — deep reference

This reference expands the SKILL.md deployment steps with the
full copy-pasteable CLI command sequence, Terraform equivalents,
CloudFormation snippets, and StackSets templates for fleet-scale
link deployment. Load when wiring cross-account observability
end-to-end or migrating a fleet to OAM.

## Sink lifecycle

### Create the sink (monitoring account)

```bash
aws oam create-sink \
  --name ProdObservabilitySink \
  --tags Environment=prod,Team=observability \
  --region us-east-1
```

The response returns a sink ARN like
`arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink`.

### Read the sink

```bash
aws oam get-sink \
  --identifier arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink \
  --region us-east-1

aws oam list-sinks --region us-east-1
```

### Tag the sink

```bash
aws oam tag-resource \
  --resource-arn arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink \
  --tags team=observability,env=prod,cost-center=infra

aws oam list-tags-for-resource \
  --resource-arn arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink
```

### Delete the sink

```bash
# All attached links MUST be deleted from source accounts first
aws oam delete-sink \
  --identifier arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink \
  --region us-east-1
```

## Sink policy

### Put the sink policy

```bash
cat > /tmp/sink-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::444455556666:root" },
      "Action": ["oam:CreateLink", "oam:UpdateLink", "oam:DeleteLink"],
      "Resource": "*",
      "Condition": {
        "ForAllValues:StringEquals": {
          "oam:ResourceTypes": [
            "AWS::CloudWatch::Metric",
            "AWS::Logs::LogGroup",
            "AWS::XRay::Trace",
            "AWS::ApplicationSignals::Service"
          ]
        }
      }
    }
  ]
}
EOF

aws oam put-sink-policy \
  --sink-identifier arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink \
  --policy file:///tmp/sink-policy.json \
  --region us-east-1
```

### Get the sink policy

```bash
aws oam get-sink-policy \
  --sink-identifier arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink \
  --region us-east-1
```

### Org-wide sink policy

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "*" },
    "Action": ["oam:CreateLink", "oam:UpdateLink", "oam:DeleteLink"],
    "Resource": "*",
    "Condition": {
      "StringEquals": { "aws:PrincipalOrgID": "o-abcdef1234" },
      "ForAllValues:StringEquals": {
        "oam:ResourceTypes": ["AWS::CloudWatch::Metric", "AWS::Logs::LogGroup"]
      }
    }
  }]
}
```

## Source account IAM role

```bash
# Run from each SOURCE account
cat > /tmp/oam-link-trust.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "lambda.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role \
  --role-name OAMLinkRole \
  --assume-role-policy-document file:///tmp/oam-link-trust.json

cat > /tmp/oam-link-permission.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "oam:CreateLink", "oam:UpdateLink", "oam:GetLink",
      "oam:DeleteLink", "oam:GetSink", "oam:ListAttachedLinks"
    ],
    "Resource": "arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink"
  }]
}
EOF

aws iam put-role-policy \
  --role-name OAMLinkRole \
  --policy-name OAMLinkPermissions \
  --policy-document file:///tmp/oam-link-permission.json
```

## Link lifecycle (run from SOURCE account)

### Create the link

```bash
cat > /tmp/link-config.json <<'EOF'
{
  "ResourceTypes": [
    "AWS::CloudWatch::Metric",
    "AWS::Logs::LogGroup",
    "AWS::XRay::Trace",
    "AWS::ApplicationSignals::Service"
  ],
  "LinkConfiguration": {
    "MetricConfiguration": {
      "Filter": "Namespace IN (\"AWS/EC2\", \"AWS/ECS\", \"AWS/Lambda\", \"AWS/ApplicationSignals\")"
    },
    "LogGroupConfiguration": {
      "Filter": "/aws/ecs/prod-app OR /aws/lambda/payments-api OR prefix(\"/aws/ecs/prod-\")"
    },
    "TraceConfiguration": {
      "Filter": "Service(\"api-gateway\") OR Service(\"checkout\") OR Service(\"payments\")"
    }
  }
}
EOF

aws oam create-link \
  --sink-identifier arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink \
  --label prod-app-link \
  --link-configuration file:///tmp/link-config.json \
  --tags Environment=prod,App=checkout \
  --region us-east-1
```

### Read the link

```bash
aws oam get-link \
  --identifier arn:aws:oam:us-east-1:444455556666:link/prod-app-link-abcdef \
  --region us-east-1

aws oam list-links --region us-east-1
```

### Update the link

```bash
cat > /tmp/link-config-update.json <<'EOF'
{
  "ResourceTypes": ["AWS::CloudWatch::Metric", "AWS::Logs::LogGroup"],
  "LinkConfiguration": {
    "MetricConfiguration": {
      "Filter": "Namespace IN (\"AWS/EC2\", \"AWS/ECS\", \"AWS/Lambda\", \"AWS/RDS\", \"AWS/ApplicationSignals\")"
    }
  }
}
EOF

aws oam update-link \
  --identifier arn:aws:oam:us-east-1:444455556666:link/prod-app-link-abcdef \
  --link-configuration file:///tmp/link-config-update.json \
  --region us-east-1
```

### List attached links (monitoring account)

```bash
aws oam list-attached-links \
  --sink-identifier arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink \
  --region us-east-1
```

### Delete the link

```bash
aws oam delete-link \
  --identifier arn:aws:oam:us-east-1:444455556666:link/prod-app-link-abcdef \
  --region us-east-1
```

## Managed Grafana cross-account wiring

### Create the Grafana read role (monitoring account)

```bash
cat > /tmp/grafana-trust.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "grafana.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role \
  --role-name GrafanaCrossAccountReadRole \
  --assume-role-policy-document file:///tmp/grafana-trust.json

cat > /tmp/grafana-permission.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricData", "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics", "cloudwatch:DescribeAlarms"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogGroups", "logs:FilterLogEvents",
        "logs:GetLogEvents", "logs:StartQuery", "logs:GetQueryResults"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "xray:GetTraceSummaries", "xray:GetTraceGraph",
        "xray:GetSamplingRules", "xray:GetSamplingTargets"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["oam:GetSink", "oam:ListAttachedLinks"],
      "Resource": "arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name GrafanaCrossAccountReadRole \
  --policy-name GrafanaCrossAccountRead \
  --policy-document file:///tmp/grafana-permission.json
```

### Attach the data source to the workspace

```bash
aws grafana update-workspace \
  --workspace-id g-abcdef1234 \
  --workspace-data-sources '[{"Type":"CLOUDWATCH","Settings":{"accountID":"111122223333","roleArn":"arn:aws:iam::111122223333:role/GrafanaCrossAccountReadRole"}},{"Type":"XRAY"}]' \
  --region us-east-1
```

## AMP cross-account workspace

```bash
# Source account owns the workspace
aws amp create-workspace --alias prod-prometheus --region us-east-1

# Trust policy on the cross-account role
cat > /tmp/amp-cross-account-trust.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::111122223333:root" },
    "Action": "sts:AssumeRole",
    "Condition": { "StringEquals": { "aws:PrincipalTag/Role": "GrafanaAMP" } }
  }]
}
EOF

aws iam create-role \
  --role-name AMPQueryRole \
  --assume-role-policy-document file:///tmp/amp-cross-account-trust.json

cat > /tmp/amp-query-permission.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "aps:GetLabels", "aps:GetMetricMetadata", "aps:GetSeries",
      "aps:Query", "aps:RemoteWrite"
    ],
    "Resource": "arn:aws:aps:us-east-1:444455556666:workspace/ws-abcdef1234"
  }]
}
EOF

aws iam put-role-policy \
  --role-name AMPQueryRole \
  --policy-name AMPQueryPermissions \
  --policy-document file:///tmp/amp-query-permission.json
```

## Terraform equivalents

### Sink + sink policy

```hcl
resource "aws_oam_sink" "prod" {
  name = "ProdObservabilitySink"
  tags = { Environment = "prod", Team = "observability" }
}

resource "aws_oam_sink_policy" "prod" {
  sink_identifier = aws_oam_sink.prod.sink_identifier
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = "arn:aws:iam::444455556666:root" }
      Action    = ["oam:CreateLink", "oam:UpdateLink", "oam:DeleteLink"]
      Resource  = "*"
    }]
  })
}
```

### Link (in source account provider)

```hcl
resource "aws_oam_link" "prod_app" {
  sink_identifier = "arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink"
  label           = "prod-app-link"
  resource_types  = ["AWS::CloudWatch::Metric", "AWS::Logs::LogGroup"]

  link_configuration {
    metric_configuration {
      filter = "Namespace IN (\"AWS/EC2\", \"AWS/ECS\")"
    }
    log_group_configuration {
      filter = "prefix(\"/aws/ecs/\")"
    }
  }

  tags = { Environment = "prod", App = "checkout" }
}
```

## CloudFormation snippets

### Sink (AWS::Oam::Sink)

```yaml
ProdObservabilitySink:
  Type: AWS::Oam::Sink
  Properties:
    Name: ProdObservabilitySink
    Tags:
      Environment: prod
      Team: observability
```

### Link (AWS::Oam::Link, deployed in source account)

```yaml
ProdAppLink:
  Type: AWS::Oam::Link
  Properties:
    SinkIdentifier: arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink
    Label: prod-app-link
    ResourceTypes:
      - AWS::CloudWatch::Metric
      - AWS::Logs::LogGroup
    LinkConfiguration:
      MetricConfiguration:
        Filter: 'Namespace IN ("AWS/EC2", "AWS/ECS")'
      LogGroupConfiguration:
        Filter: 'prefix("/aws/ecs/")'
    Tags:
      Environment: prod
```

## StackSets template for fleet deployment

Deploy the link across many source accounts from the monitoring
account using CloudFormation StackSets:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: OAM link for fleet source accounts
Parameters:
  SinkArn:
    Type: String
  SinkRegion:
    Type: String
Resources:
  OAMLinkRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: OAMLinkRole
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal: { Service: cloudformation.amazonaws.com }
            Action: sts:AssumeRole
      Policies:
        - PolicyName: OAMLinkPermissions
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - oam:CreateLink
                  - oam:UpdateLink
                  - oam:GetLink
                  - oam:DeleteLink
                Resource: !Ref SinkArn
  OAMLink:
    Type: AWS::Oam::Link
    Properties:
      SinkIdentifier: !Ref SinkArn
      Label: !Sub "fleet-link-${AWS::AccountId}"
      ResourceTypes:
        - AWS::CloudWatch::Metric
        - AWS::Logs::LogGroup
      LinkConfiguration:
        MetricConfiguration:
          Filter: 'Namespace IN ("AWS/EC2", "AWS/ECS", "AWS/Lambda")'
        LogGroupConfiguration:
          Filter: 'prefix("/aws/")'
```

Deploy with:

```bash
aws cloudformation create-stack-set \
  --stack-set-name oam-fleet-link \
  --template-body file://fleet-link.yaml \
  --parameters ParameterKey=SinkArn,ParameterValue=arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink \
               ParameterKey=SinkRegion,ParameterValue=us-east-1 \
  --permission-model SERVICE_MANAGED \
  --auto-deployment Enabled=true,RetainStacksOnAccountDeletion=false \
  --region us-east-1

aws cloudformation create-stack-instances \
  --stack-set-name oam-fleet-link \
  --deployment-targets OrganizationalUnitIds=[ou-abcdef] \
  --regions us-east-1 \
  --region us-east-1
```

## Verification

```bash
# Monitoring account
aws oam list-sinks --region us-east-1
aws oam get-sink --identifier <sink-arn> --region us-east-1
aws oam list-attached-links --sink-identifier <sink-arn> --region us-east-1

# Source account
aws oam list-links --region us-east-1
aws oam get-link --identifier <link-arn> --region us-east-1

# Cross-account data
aws cloudwatch list-metrics --namespace AWS/ApplicationSignals --region us-east-1
aws logs describe-log-groups --log-group-name-prefix /aws/ecs --region us-east-1
aws xray get-trace-summaries \
  --start-time $(date -u +%s --date='10 min ago') \
  --end-time $(date -u +%s) --region us-east-1
```
