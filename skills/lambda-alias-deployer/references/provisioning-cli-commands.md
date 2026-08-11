# Provisioning CLI Commands — Lambda Alias Deployer

Full copy-pasteable CLI command sequence for provisioning Lambda
aliases with traffic shifting, API Gateway integration, CloudWatch
alarms, provisioned concurrency, and SnapStart. Variables to
substitute: `<region>`, `<account-id>`, `<function-name>`,
`<alias-name>`, `<version>`, `<api-id>`.

## Step 0: Prerequisites check

```bash
# Confirm caller identity
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Confirm region
REGION=$(aws configure get region)
echo "Region: $REGION"

# Confirm function exists
aws lambda get-function \
  --function-name my-function \
  --query 'Configuration.FunctionArn' --output text

# List published versions
aws lambda list-versions-by-function \
  --function-name my-function \
  --query 'Versions[*].Version' --output table
```

## Step 1: Publish a version

```bash
NEW_VERSION=$(aws lambda publish-version \
  --function-name my-function \
  --query Version --output text)

echo "Published version: $NEW_VERSION"
```

## Step 2: Create an alias

```bash
aws lambda create-alias \
  --function-name my-function \
  --name prod \
  --function-version "$NEW_VERSION" \
  --description "Production alias"
```

## Step 3: Traffic shifting (canary)

```bash
OLD_VERSION=5
NEW_VERSION=6

# 10% canary
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --function-version "$OLD_VERSION" \
  --routing-config AdditionalVersionWeights="{\"$NEW_VERSION\":0.1}"

# Monitor, then 25%
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --routing-config AdditionalVersionWeights="{\"$NEW_VERSION\":0.25}"

# Finalize 100%
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --function-version "$NEW_VERSION" \
  --routing-config '{}'

# Rollback (if needed)
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --function-version "$OLD_VERSION" \
  --routing-config '{}'
```

## Step 4: API Gateway integration

```bash
# Grant API Gateway permission to invoke the alias
aws lambda add-permission \
  --function-name "my-function:prod" \
  --statement-id apigateway-prod \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:$ACCOUNT_ID:abc123/*/GET/hello"

# Update the API Gateway integration to use the alias ARN
# Integration URI must be:
#   arn:aws:lambda:us-east-1:$ACCOUNT_ID:function:my-function:prod
```

## Step 5: CloudWatch alarm per alias

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "my-function-prod-errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 60 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions \
    Name=FunctionName,Value=my-function \
    Name=Resource,Value=my-function:prod \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:$ACCOUNT_ID:alerts"
```

## Step 6: Provisioned concurrency on alias

```bash
# Configure provisioned concurrency on the alias
aws lambda put-provisioned-concurrency-config \
  --function-name my-function \
  --qualifier prod \
  --provisioned-concurrent-executions 10

# Verify
aws lambda get-provisioned-concurrency-config \
  --function-name my-function \
  --qualifier prod
```

## Step 7: Auto Scaling for provisioned concurrency

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace lambda \
  --resource-id "function:my-function:prod" \
  --scalable-dimension lambda:function:ProvisionedConcurrency \
  --min-capacity 2 \
  --max-capacity 50

# Target tracking policy
aws application-autoscaling put-scaling-policy \
  --policy-name prod-pc-scaling \
  --service-namespace lambda \
  --resource-id "function:my-function:prod" \
  --scalable-dimension lambda:function:ProvisionedConcurrency \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "LambdaProvisionedConcurrencyUtilization"
    },
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'
```

## Step 8: Enable SnapStart

```bash
# Enable SnapStart on the function (before publishing)
aws lambda update-function-configuration \
  --function-name my-function \
  --snap-start ApplyOn=PublishedVersions

# Publish a new version (gets a snapshot)
SNAP_VERSION=$(aws lambda publish-version \
  --function-name my-function \
  --query Version --output text)

echo "SnapStart version: $SNAP_VERSION"

# Verify SnapStart status
aws lambda get-function-configuration \
  --function-name my-function \
  --qualifier "$SNAP_VERSION" \
  --query 'SnapStart'
```

## Verification

```bash
# Alias configuration
aws lambda get-alias \
  --function-name my-function \
  --name prod

# Provisioned concurrency
aws lambda get-provisioned-concurrency-config \
  --function-name my-function \
  --qualifier prod

# CloudWatch alarm
aws cloudwatch describe-alarms \
  --alarm-names my-function-prod-errors

# All aliases for the function
aws lambda list-aliases \
  --function-name my-function

# Auto Scaling target
aws application-autoscaling describe-scalable-targets \
  --service-namespace lambda \
  --resource-ids function:my-function:prod
```

## Terraform equivalent

```hcl
# Publish version
resource "aws_lambda_alias" "prod" {
  name             = "prod"
  description      = "Production alias"
  function_name    = aws_lambda_function.main.function_name
  function_version = aws_lambda_function.main.version

  routing_config {
    additional_version_weights = {
      "6" = 0.1
    }
  }
}

# Provisioned concurrency on alias
resource "aws_lambda_provisioned_concurrency_config" "prod" {
  function_name                     = aws_lambda_function.main.function_name
  qualifier                         = aws_lambda_alias.prod.name
  provisioned_concurrent_executions = 10
}

# CloudWatch alarm scoped to alias
resource "aws_cloudwatch_metric_alarm" "prod_errors" {
  alarm_name          = "my-function-prod-errors"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  statistic           = "Sum"
  period              = 60
  threshold           = 5
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1

  dimensions = {
    FunctionName = aws_lambda_function.main.function_name
    Resource     = "${aws_lambda_function.main.function_name}:${aws_lambda_alias.prod.name}"
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}
```

## AWS CLI quick reference

| Operation | Command |
|---|---|
| Publish version | `aws lambda publish-version` |
| Create alias | `aws lambda create-alias` |
| Update alias | `aws lambda update-alias` |
| Delete alias | `aws lambda delete-alias` |
| Get alias | `aws lambda get-alias` |
| List aliases | `aws lambda list-aliases` |
| List versions | `aws lambda list-versions-by-function` |
| Put provisioned concurrency | `aws lambda put-provisioned-concurrency-config` |
| Get provisioned concurrency | `aws lambda get-provisioned-concurrency-config` |
| Add permission | `aws lambda add-permission` |
| Enable SnapStart | `aws lambda update-function-configuration` |
