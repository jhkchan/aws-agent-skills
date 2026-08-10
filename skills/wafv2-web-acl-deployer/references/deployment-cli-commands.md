# Deployment CLI Commands — WAFv2 Web ACL Deployer

Full copy-pasteable CLI command sequence for all 9 provisioning steps.
Variables to substitute: `<region>`, `<account-id>`, `<web-acl-name>`,
`<scope>`, `<resource-arn>`, `<log-destination-arn>`.

## Step 0: Prerequisites check

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

# For REGIONAL scope, confirm the ALB / API Gateway / AppSync exists
aws elbv2 describe-load-balancers --region <region>
aws apigateway get-rest-apis --region <region>

# For CLOUDFRONT scope, confirm the distribution exists
aws cloudfront get-distribution --id <dist-id>

# Confirm logging destination exists
aws firehose describe-delivery-stream --delivery-stream-name aws-waf-logs-<name>
aws logs describe-log-groups --log-group-name-prefix /aws/wafv2/
aws s3api get-bucket-policy --bucket <log-bucket>

# Confirm IP sets / regex sets (if referenced by custom rules)
aws wafv2 list-ip-sets --scope <scope> --region <region>
aws wafv2 list-regex-pattern-sets --scope <scope> --region <region>

# Confirm managed rule group availability (ATP, Bot Control)
aws wafv2 list-available-managed-rule-groups --scope <scope> --region <region>
```

## Step 1: Create an IP set (if custom rules reference one)

```bash
aws wafv2 create-ip-set \
  --name payments-blocklist \
  --scope REGIONAL \
  --region us-east-1 \
  --addresses "$(cat ip-list.json)" \
  --ip-address-version IPV4 \
  --description "Blocked IPs for payments API"
```

## Step 2: Create the Web ACL (REGIONAL scope with managed rules)

```bash
cat > /tmp/web-acl.json <<'EOF'
{
  "Name": "payments-api-waf",
  "Scope": "REGIONAL",
  "DefaultAction": { "Allow": {} },
  "Description": "WAF for payments API ALB",
  "Rules": [
    {
      "Name": "allow-partner-ips",
      "Priority": 0,
      "Action": { "Allow": {} },
      "Statement": {
        "IPSetReferenceStatement": {
          "Arn": "arn:aws:wafv2:us-east-1:123456789012:regional/ipset/partner-ips/<id>"
        }
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "allow-partner-ips"
      }
    },
    {
      "Name": "aws-managed-common",
      "Priority": 10,
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesCommonRuleSet"
        }
      },
      "OverrideAction": { "None": {} },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "aws-managed-common"
      }
    },
    {
      "Name": "aws-managed-sqli",
      "Priority": 20,
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesSQLiRuleSet"
        }
      },
      "OverrideAction": { "None": {} },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "aws-managed-sqli"
      }
    },
    {
      "Name": "aws-managed-ip-rep",
      "Priority": 100,
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesAmazonIpReputationList"
        }
      },
      "OverrideAction": { "None": {} },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "aws-managed-ip-rep"
      }
    },
    {
      "Name": "rate-limit-api",
      "Priority": 5000,
      "Action": { "Block": {} },
      "Statement": {
        "RateBasedStatement": {
          "Limit": 2000,
          "AggregateKeyType": "IP",
          "ScopeDownStatement": {
            "ByteMatchStatement": {
              "SearchString": "/api/",
              "FieldToMatch": { "UriPath": {} },
              "PositionalConstraint": "STARTS_WITH"
            }
          }
        }
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "rate-limit-api"
      }
    }
  ],
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "payments-api-waf"
  },
  "Tags": [
    { "Key": "Environment", "Value": "production" },
    { "Key": "Application", "Value": "payments" }
  ]
}
EOF

WEB_ACL_ARN=$(aws wafv2 create-web-acl \
  --cli-input-json file:///tmp/web-acl.json \
  --region us-east-1 \
  --query 'Summary.ARN' --output text)

echo "Created Web ACL ARN: ${WEB_ACL_ARN}"
```

## Step 3: Create CLOUDFRONT-scope Web ACL

```bash
# CLOUDFRONT scope must be in us-east-1
cat > /tmp/web-acl-cf.json <<'EOF'
{
  "Name": "payments-cdn-waf",
  "Scope": "CLOUDFRONT",
  "DefaultAction": { "Allow": {} },
  "Description": "WAF for CloudFront distribution",
  "Rules": [
    {
      "Name": "aws-managed-common",
      "Priority": 10,
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesCommonRuleSet"
        }
      },
      "OverrideAction": { "None": {} },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "aws-managed-common"
      }
    },
    {
      "Name": "geo-block",
      "Priority": 1000,
      "Action": { "Block": {} },
      "Statement": {
        "GeoMatchStatement": {
          "CountryCodes": ["RU", "KP", "IR"]
        }
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "geo-block"
      }
    }
  ],
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "payments-cdn-waf"
  }
}
EOF

WEB_ACL_ARN_CF=$(aws wafv2 create-web-acl \
  --cli-input-json file:///tmp/web-acl-cf.json \
  --region us-east-1 \
  --query 'Summary.ARN' --output text)
```

## Step 4: Rate-based rule with FORWARDED_IP

```bash
# For traffic behind a CDN or ALB — use FORWARDED_IP aggregate key
cat > /tmp/rate-rule-forwarded.json <<'EOF'
{
  "Name": "rate-limit-forwarded-ip",
  "Priority": 5001,
  "Action": { "Block": {} },
  "Statement": {
    "RateBasedStatement": {
      "Limit": 1000,
      "AggregateKeyType": "FORWARDED_IP",
      "ForwardedIPConfig": {
        "HeaderName": "X-Forwarded-For",
        "FallbackBehavior": "MATCH",
        "Position": "FIRST"
      },
      "ScopeDownStatement": {
        "ByteMatchStatement": {
          "SearchString": "/api/v1/login",
          "FieldToMatch": { "UriPath": {} },
          "PositionalConstraint": "STARTS_WITH"
        }
      }
    }
  },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "rate-limit-forwarded-ip"
  }
}
EOF

# Update the Web ACL to include this rule
aws wafv2 update-web-acl \
  --id <web-acl-id> \
  --name payments-api-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=payments-api-waf \
  --rules file:///tmp/rate-rule-forwarded.json \
  --lock-token <lock-token> \
  --region us-east-1
```

## Step 5: CAPTCHA and Challenge rules

```bash
# CAPTCHA on signup endpoint
cat > /tmp/captcha-rule.json <<'EOF'
{
  "Name": "captcha-signup",
  "Priority": 1000,
  "Action": { "Captcha": {} },
  "Statement": {
    "ByteMatchStatement": {
      "SearchString": "/signup",
      "FieldToMatch": { "UriPath": {} },
      "PositionalConstraint": "STARTS_WITH"
    }
  },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "captcha-signup"
  }
}
EOF

# Challenge on search endpoint (low friction)
cat > /tmp/challenge-rule.json <<'EOF'
{
  "Name": "challenge-search",
  "Priority": 1001,
  "Action": { "Challenge": {} },
  "Statement": {
    "ByteMatchStatement": {
      "SearchString": "/search",
      "FieldToMatch": { "UriPath": {} },
      "PositionalConstraint": "STARTS_WITH"
    }
  },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "challenge-search"
  }
}
EOF
```

## Step 6: ATP rule group

```bash
cat > /tmp/atp-rule.json <<'EOF'
{
  "Name": "atp-login-protection",
  "Priority": 200,
  "Statement": {
    "ManagedRuleGroupStatement": {
      "VendorName": "AWS",
      "Name": "AWSManagedRulesATPRuleSet",
      "ManagedRuleGroupConfigs": [{
        "LoginPath": "/api/v1/login",
        "PayloadType": "JSON",
        "UsernameField": { "Identifier": "username" },
        "PasswordField": { "Identifier": "password" }
      }]
    }
  },
  "OverrideAction": { "Count": {} },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "atp-login-protection"
  }
}
EOF
```

## Step 7: Configure logging

```bash
# Option A: Kinesis Firehose (recommended)
# The delivery stream MUST be named with prefix aws-waf-logs-
aws firehose create-delivery-stream \
  --delivery-stream-name aws-waf-logs-payments \
  --delivery-stream-type DirectPut \
  --s3-destination-configuration \
    RoleARN=arn:aws:iam::123456789012:role/firehose-waf-role,\
    BucketARN=arn:aws:s3:::payments-waf-logs

# Attach logging to the Web ACL
aws wafv2 put-logging-configuration \
  --logging-configuration \
    WebACLArn=${WEB_ACL_ARN},\
    LogDestinationConfigs=arn:aws:firehose:us-east-1:123456789012:deliverystream/aws-waf-logs-payments \
  --region us-east-1

# Option B: CloudWatch Logs
# First create the log group and resource policy
aws logs create-log-group --log-group-name /aws/wafv2/payments

aws logs put-resource-policy \
  --policy-name aws-waf-logs-policy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": { "Service": "delivery.logs.amazonaws.com" },
      "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/wafv2/payments:*"
    }]
  }'

aws wafv2 put-logging-configuration \
  --logging-configuration \
    WebACLArn=${WEB_ACL_ARN},\
    LogDestinationConfigs=arn:aws:logs:us-east-1:123456789012:log-group:/aws/wafv2/payments \
  --region us-east-1
```

## Step 8: Associate with resources

```bash
# ALB
aws wafv2 associate-web-acl \
  --web-acl-arn ${WEB_ACL_ARN} \
  --resource-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/payments-alb/50dc6c495c0c9188 \
  --region us-east-1

# API Gateway REST API stage
aws wafv2 associate-web-acl \
  --web-acl-arn ${WEB_ACL_ARN} \
  --resource-arn arn:aws:apigateway:us-east-1::/restapis/abc123/stages/prod \
  --region us-east-1

# CloudFront (set on the distribution config, not via WAF API)
aws cloudfront get-distribution-config --id E123ABC > /tmp/cf-config.json
# Edit /tmp/cf-config.json: set WebACLId to the Web ACL ARN
ETAG=$(jq -r '.ETag' /tmp/cf-config.json)
jq '.DistributionConfig.WebACLId = "'${WEB_ACL_ARN_CF}'"' /tmp/cf-config.json > /tmp/cf-config-updated.json
aws cloudfront update-distribution \
  --id E123ABC \
  --if-match ${ETAG} \
  --distribution-config file:///tmp/cf-config-updated.json
```

## Step 9: Tagging + verification

```bash
aws wafv2 list-tags-for-resource \
  --resource-arn ${WEB_ACL_ARN} \
  --region us-east-1

aws wafv2 tag-resource \
  --resource-arn ${WEB_ACL_ARN} \
  --tags '[{"Key":"Environment","TagValue":"production"},{"Key":"Application","TagValue":"payments"}]' \
  --region us-east-1
```

## Post-deployment verification

```bash
# List Web ACLs
aws wafv2 list-web-acls --scope REGIONAL --region us-east-1

# Get full Web ACL config
aws wafv2 get-web-acl --scope REGIONAL --id <web-acl-id> --region us-east-1

# List resources associated with the Web ACL
aws wafv2 list-resources-for-web-acl --web-acl-arn ${WEB_ACL_ARN} --region us-east-1

# Get logging configuration
aws wafv2 get-logging-configuration --web-acl-arn ${WEB_ACL_ARN} --region us-east-1

# Get sampled requests (for debugging rule matches)
aws wafv2 get-sampled-requests \
  --web-acl-arn ${WEB_ACL_ARN} \
  --rule-metric-name rate-limit-api \
  --scope REGIONAL \
  --time-window StartTime=$(date -u -v-5M +%Y-%m-%dT%H:%M:%S),EndTime=$(date -u +%Y-%m-%dT%H:%M:%S) \
  --max-items 100 \
  --region us-east-1
```

## Terraform equivalents

```hcl
# REGIONAL Web ACL with managed rules + rate-based rule
resource "aws_wafv2_web_acl" "payments" {
  name        = "payments-api-waf"
  description = "WAF for payments API ALB"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name               = "payments-api-waf"
    sampled_requests_enabled  = true
  }

  managed_rule_group "common" {
    name      = "AWSManagedRulesCommonRuleSet"
    priority  = 10
    vendor    = "AWS"
  }

  managed_rule_group "sqli" {
    name      = "AWSManagedRulesSQLiRuleSet"
    priority  = 20
    vendor    = "AWS"
  }

  rate_rule "api-rate-limit" {
    name       = "rate-limit-api"
    priority   = 5000
    limit      = 2000
    aggregate_key_type = "IP"

    action { block {} }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "rate-limit-api"
      sampled_requests_enabled  = true
    }
  }
}

# Associate with ALB
resource "aws_wafv2_web_acl_association" "payments" {
  resource_arn = aws_lb.payments.arn
  web_acl_arn  = aws_wafv2_web_acl.payments.arn
}

# IP set
resource "aws_wafv2_ip_set" "blocklist" {
  name               = "payments-blocklist"
    scope             = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = ["10.0.0.0/8"]
}

# Logging configuration (Kinesis Firehose)
resource "aws_wafv2_web_acl_logging_configuration" "payments" {
  log_destination_configs = [aws_kinesis_firehose_delivery_stream.waf_logs.arn]
  resource_arn            = aws_wafv2_web_acl.payments.arn
}

# Firehose delivery stream (must be prefixed aws-waf-logs-)
resource "aws_kinesis_firehose_delivery_stream" "waf_logs" {
  name        = "aws-waf-logs-payments"
  destination = "s3"
  # ... s3 config
}

# CLOUDFRONT-scope Web ACL
resource "aws_wafv2_web_acl" "cdn" {
  name  = "payments-cdn-waf"
  scope = "CLOUDFRONT"
  # ... rules
}

# CloudFront distribution association
resource "aws_cloudfront_distribution" "payments" {
  # ...
  web_acl_id = aws_wafv2_web_acl.cdn.arn
}
```

## CloudFormation equivalents

- `AWS::WAFv2::WebACL` — `Scope` (CLOUDFRONT|REGIONAL), `DefaultAction`,
  `Rules` (managed rule group statements, custom rules, rate-based rules),
  `VisibilityConfig`.
- `AWS::WAFv2::WebACLAssociation` — `ResourceArn` (ALB/API Gateway),
  `WebACLArn`. For CloudFront, set `WebACLId` on the distribution.
- `AWS::WAFv2::IPSet` — `Scope`, `Addresses`, `IPAddressVersion`.
- `AWS::WAFv2::RegexPatternSet` — `Scope`, `RegularExpressionList`.
- `AWS::WAFv2::LoggingConfiguration` — `ResourceArn`, `LogDestinationConfigs`.
