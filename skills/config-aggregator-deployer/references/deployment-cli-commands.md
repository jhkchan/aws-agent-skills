# Deployment CLI Commands — Config Aggregator Deployer

Full copy-pasteable CLI command sequence for all 9 provisioning steps.
Variables to substitute: `<region>`, `<account-id>`, `<aggregator-name>`,
`<organization-id>`, `<source-account-id>`, `<s3-bucket>`.

## Step 0: Prerequisites check

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

# Confirm Organizations all features enabled
aws organizations describe-organization --query 'Organization.FeatureSet' --output text

# Confirm Config is a trusted service
aws organizations list-aws-service-access-for-organization \
  --filter config.amazonaws.com

# Confirm delegated administrator for Config
aws organizations list-delegated-administrators \
  --service-principal config.amazonaws.com

# Confirm Config recorder is running on source accounts
aws configservice describe-configuration-recorder-status \
  --configuration-recorder-names default

# Confirm delivery channel exists
aws configservice describe-delivery-channels

# Confirm conformance pack template availability
aws configservice describe-conformance-pack-templates
```

## Step 1: Enable Config trusted service + register delegated admin

```bash
# Enable AWS Config as a trusted service in Organizations (management account)
aws organizations enable-aws-service-access \
  --service-principal config.amazonaws.com

# Designate the aggregator account as delegated admin
aws organizations register-delegated-administrator \
  --account-id 123456789012 \
  --service-principal config.amazonaws.com
```

## Step 2: Create the organization aggregator

```bash
# Create the aggregator service role in the management account
cat > /tmp/config-aggregator-trust.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "config.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role \
  --role-name ConfigAggregatorRole \
  --assume-role-policy-document file:///tmp/config-aggregator-trust.json

aws iam put-role-policy \
  --role-name ConfigAggregatorRole \
  --policy-name ConfigAggregatorOrgAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["organizations:ListAccounts", "organizations:DescribeOrganization"],
      "Resource": "*"
    }]
  }'

# Create the aggregator
cat > /tmp/aggregator.json <<'EOF'
{
  "ConfigurationAggregatorName": "org-compliance-aggregator",
  "OrganizationAggregationSource": {
    "RoleArn": "arn:aws:iam::123456789012:role/ConfigAggregatorRole",
    "AllAwsRegions": true
  },
  "Tags": [
    { "Key": "Environment", "Value": "production" },
    { "Key": "Governance", "Value": "compliance" }
  ]
}
EOF

aws configservice put-configuration-aggregator \
  --cli-input-json file:///tmp/aggregator.json \
  --region us-east-1
```

## Step 3: Create an authorized-account aggregator

```bash
cat > /tmp/aggregator-auth.json <<'EOF'
{
  "ConfigurationAggregatorName": "authorized-accounts-aggregator",
  "AccountAggregationSources": [
    {
      "AccountIds": ["111111111111", "222222222222", "333333333333"],
      "AllAwsRegions": true
    }
  ],
  "Tags": [
    { "Key": "Environment", "Value": "production" }
  ]
}
EOF

aws configservice put-configuration-aggregator \
  --cli-input-json file:///tmp/aggregator-auth.json \
  --region us-east-1
```

## Step 4: Authorize source accounts (authorized-account only)

```bash
# Run on each SOURCE account — grant aggregator account permission
aws configservice put-aggregation-authorization \
  --authorized-account-id 123456789012 \
  --authorized-aws-region us-east-1

# For multi-region, run per region
aws configservice put-aggregation-authorization \
  --authorized-account-id 123456789012 \
  --authorized-aws-region eu-west-1
```

Organization aggregators do NOT need this — the delegated admin
auto-authorizes.

## Step 5: Verify and enable recorders in source accounts

```bash
# Check recorder status on each source account
aws configservice describe-configuration-recorder-status

# If recorder is not running, enable Config on the source account
# Create the Config role
cat > /tmp/config-trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "config.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role \
  --role-name AWS-ConfigRole \
  --assume-role-policy-document file:///tmp/config-trust-policy.json

aws iam attach-role-policy \
  --role-name AWS-ConfigRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWS_ConfigRole

# Create delivery channel
cat > /tmp/delivery-channel.json <<'EOF'
{
  "name": "default",
  "s3BucketName": "config-bucket-111111111111",
  "configSnapshotDeliveryProperties": {
    "deliveryFrequency": "Six_Hours"
  }
}
EOF

aws configservice put-delivery-channel \
  --delivery-channel file:///tmp/delivery-channel.json

# Start the recorder
aws configservice start-configuration-recorder \
  --configuration-recorder-name default
```

## Step 6: Deploy organization conformance pack

```bash
# Deploy org-level conformance pack from S3 template
aws configservice put-organization-conformance-pack \
  --organization-conformance-pack-name OperationalBestPractices-for-Security \
  --template-s3-uri s3://config-templates-123456789012/security-best-practices.yaml \
  --region us-east-1

# Deploy with input parameters
aws configservice put-organization-conformance-pack \
  --organization-conformance-pack-name OperationalBestPractices-for-EC2 \
  --template-s3-uri s3://config-templates-123456789012/ec2-best-practices.yaml \
  --conformance-pack-input-parameters \
    ParameterName=DesiredInstanceType,ParameterValue=t3.medium \
    ParameterName=AllowedRegions,ParameterValue=us-east-1 \
  --region us-east-1

# Deploy with inline template body (2024 feature)
aws configservice put-organization-conformance-pack \
  --organization-conformance-pack-name custom-compliance-pack \
  --template-body file:///tmp/custom-compliance-pack.yaml \
  --region us-east-1
```

## Step 7: Deploy organization config rule with Lambda processor

```bash
# Deploy the Lambda function
aws lambda create-function \
  --function-name config-tag-policy-rule \
  --runtime python3.12 \
  --role arn:aws:iam::123456789012:role/ConfigLambdaRole \
  --handler index.handler \
  --zip-file fileb://config-rule.zip \
  --region us-east-1

# Grant Config permission to invoke the Lambda
aws lambda add-permission \
  --function-name config-tag-policy-rule \
  --statement-id ConfigInvokePermission \
  --action lambda:InvokeFunction \
  --principal config.amazonaws.com \
  --region us-east-1

# Create the organization custom config rule
aws configservice put-organization-config-rule \
  --organization-config-rule-name tag-policy-compliance \
  --organization-custom-rule \
    LambdaFunctionArn=arn:aws:lambda:us-east-1:123456789012:function:config-tag-policy-rule,\
    OrganizationRuleStatus=ENABLED,\
    MaximumExecutionFrequency=One_Hour \
  --region us-east-1
```

## Step 8: Proactive rules (pre-deployment evaluation)

```bash
# Create a Config rule with proactive mode enabled
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "s3-bucket-versioning-proactive",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "S3_BUCKET_VERSIONING_ENABLED"
    },
    "Proactive": true
  }' \
  --region us-east-1

# Pre-deployment evaluation — check a hypothetical resource
EVAL_TOKEN=$(aws configservice start-resource-evaluation \
  --resource-type "AWS::S3::Bucket" \
  --resource-id "my-new-bucket" \
  --evaluation-mode PROACTIVE \
  --configuration '{"BucketName":"my-new-bucket","VersioningConfiguration":{"Status":"Suspended"}}' \
  --query 'EvaluationToken' --output text \
  --region us-east-1)

# Retrieve the evaluation result
aws configservice get-resource-evaluation-status \
  --evaluation-token ${EVAL_TOKEN} \
  --region us-east-1
```

## Step 9: Verification and post-deployment checks

```bash
# Verify the aggregator exists
aws configservice describe-configuration-aggregators \
  --configuration-aggregator-names org-compliance-aggregator \
  --region us-east-1

# Check aggregation source status
aws configservice describe-configuration-aggregator-sources-status \
  --configuration-aggregator-name org-compliance-aggregator \
  --region us-east-1

# List org conformance packs
aws configservice describe-organization-conformance-packs \
  --region us-east-1

# Check org conformance pack per-account status
aws configservice get-organization-conformance-pack-detailed-status \
  --organization-conformance-pack-name OperationalBestPractices-for-Security \
  --region us-east-1

# Check org config rule deployment status
aws configservice describe-organization-config-rule-statuses \
  --region us-east-1

# Aggregate compliance query across accounts/regions
aws configservice get-aggregate-compliance-details-by-config-rule \
  --configuration-aggregator-name org-compliance-aggregator \
  --config-rule-name s3-bucket-versioning-proactive \
  --account-id 111111111111 \
  --aws-region us-east-1 \
  --region us-east-1

# Aggregate config rule summary across all accounts
aws configservice get-aggregate-config-rule-compliance-summary \
  --configuration-aggregator-name org-compliance-aggregator \
  --region us-east-1
```

## Terraform equivalents

```hcl
# Organization aggregator
resource "aws_config_configuration_aggregator" "org" {
  name = "org-compliance-aggregator"

  organization_aggregation_source {
    all_regions = true
    role_arn    = aws_iam_role.config_aggregator.arn
  }

  tags = {
    Environment = "production"
    Governance  = "compliance"
  }
}

# Authorized-account aggregator
resource "aws_config_configuration_aggregator" "accounts" {
  name = "authorized-accounts-aggregator"

  account_aggregation_source {
    account_ids = ["111111111111", "222222222222", "333333333333"]
    all_regions = true
  }
}

# Organization conformance pack
resource "aws_config_organization_conformance_pack" "security" {
  name            = "OperationalBestPractices-for-Security"
  template_s3_uri = "s3://config-templates-123456789012/security-best-practices.yaml"
}

# Organization custom config rule with Lambda
resource "aws_config_organization_custom_rule" "tag_policy" {
  name                           = "tag-policy-compliance"
  lambda_function_arn            = aws_lambda_function.config_tag_rule.arn
  organization_rule_status       = "ENABLED"
  maximum_execution_frequency    = "One_Hour"
}

# Aggregation authorization (for authorized-account type)
resource "aws_config_aggregate_authorization" "auth" {
  account_id           = "111111111111"
  region               = "us-east-1"
}
```

## CloudFormation equivalents

- `AWS::Config::ConfigurationAggregator` — `OrganizationAggregationSource`
  or `AccountAggregationSources`.
- `AWS::Config::OrganizationConformancePack` — `OrganizationConformancePackName`,
  `TemplateS3Uri` or `TemplateBody`, `ConformancePackInputParameters`.
- `AWS::Config::OrganizationConfigRule` — `OrganizationCustomRuleMetadata`
  (LambdaFunctionArn) or `OrganizationManagedRuleMetadata`.
- `AWS::Config::AggregationAuthorization` — `AuthorizedAccountId`,
  `AuthorizedAwsRegion`.
- `AWS::Config::ConformancePack` — account-level conformance pack
  (use OrganizationConformancePack for org-wide).
