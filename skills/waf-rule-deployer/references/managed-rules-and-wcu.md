# Managed Rule Groups and WCU Budget — WAF Rule Deployer

Deep reference on managed rule group selection (vendor names,
coverage, versioning), WCU (Web ACL Capacity Units) budget planning
(per-rule costs, per-ACL limits, referenced rule group offloading),
and version pinning strategy. Loaded on demand by the skill — kept
out of the main SKILL.md body so the provisioning procedure stays
scannable.

## Managed rule group catalog

### AWS-managed rule groups (VendorName: AWS)

All AWS-managed rule groups use `VendorName: AWS`. The `Name` field
matches the rule group identifier.

| Name | Coverage | Approx WCU | Paid? |
|---|---|---|---|
| AWSManagedRulesCommonRuleSet | OWASP Top 10 essentials | ~700 | No |
| AWSManagedRulesSQLiRuleSet | SQL injection signatures | ~200 | No |
| AWSManagedRulesAmazonIpReputationList | Known malicious IPs | ~20 | No |
| AWSManagedRulesLinuxRuleSet | Linux-specific exploits | ~200 | No |
| AWSManagedRulesWindowsRuleSet | Windows-specific exploits | ~200 | No |
| AWSManagedRulesUnixRuleSet | Unix LFI, shell escape | ~200 | No |
| AWSManagedRulesPHPRuleSet | PHP-specific exploits | ~200 | No |
| AWSManagedRulesWordPressRuleSet | WordPress exploits | ~100 | No |
| AWSManagedRulesBotControlRuleSet | Bot detection | ~50 | Yes |
| AWSManagedRulesATPRuleSet | Account takeover prevention | ~50 | Yes |
| AWSManagedRulesACFPRuleSet | Account creation fraud | ~50 | Yes |

### AWSManagedRulesCommonRuleSet detail

The CommonRuleSet is the foundation rule group. It includes rules
for:
- SQLi (cross-checks with SQLiRuleSet for deeper coverage)
- XSS (cross-site scripting)
- LFI (local file inclusion)
- RFI (remote file inclusion)
- RCE (remote code execution)
- WordPress admin path exploitation
- Generic HTTP anomalies (missing User-Agent, etc.)

It excludes rules that the `AWSManagedRulesAmazonIpReputationList`
covers (known bad IPs). Use both together for layered protection.

### Version pinning

```bash
# List available versions for a managed rule group
aws wafv2 describe-managed-rule-group \
  --vendor-name AWS \
  --name AWSManagedRulesCommonRuleSet \
  --scope CLOUDFRONT \
  --region us-east-1 \
  --query 'AvailableRules' --output table
```

**Version strategy:**
- **Default (Version: null):** AWS keeps the rule group at the
  latest version automatically. New threat signatures are added
  without user intervention. Best for new deployments.
- **Pinned (Version: Version_2.1):** the rule group stays at the
  specified version. No automatic updates. Best for production
  predictability. Review quarterly and upgrade to capture new
  signatures.

**Trade-off:** pinning prevents surprise behavior changes (a new
signature that false-positives on your traffic) but also delays
protection against new threats. For high-security environments,
consider staying on default (latest) and monitoring COUNT metrics
for false positives.

## WCU budget planning

### Per-ACL limit

The default WCU limit per Web ACL is **1500**. This is a soft limit
that can be increased via AWS Support (some accounts may have higher
limits).

### Per-rule WCU costs (approximate)

WCU costs are approximate and can change. Always verify current
costs in the AWS WAF documentation.

```text
Managed rule groups:
  AWSManagedRulesCommonRuleSet          ~700
  AWSManagedRulesSQLiRuleSet            ~200
  AWSManagedRulesAmazonIpReputationList ~20
  AWSManagedRulesLinuxRuleSet           ~200
  AWSManagedRulesWindowsRuleSet         ~200
  AWSManagedRulesUnixRuleSet            ~200
  AWSManagedRulesPHPRuleSet             ~200
  AWSManagedRulesWordPressRuleSet       ~100
  AWSManagedRulesBotControlRuleSet      ~50
  AWSManagedRulesATPRuleSet             ~50
  AWSManagedRulesACFPRuleSet            ~50

Custom rule statements:
  ByteMatchStatement (single condition)     1
  GeoMatchStatement                         3
  IPSetReferenceStatement                   1
  RegexPatternSetReferenceStatement         25
  SizeConstraintStatement                   1
  RateBasedStatement                        1 + base rule cost
  NotStatement                              1 + nested cost
  OrStatement / AndStatement                1 + nested costs

  Regex (inline, not pattern set)           25
  SqliMatchField (inline)                   20
  XssMatchField (inline)                    20
```

### Budget calculation example

```text
Production CloudFront ACL:
  Managed:
    CommonRuleSet                700
    SQLiRuleSet                  200
    AmazonIpReputationList        20
    BotControlRuleSet             50
    ATPRuleSet                    50
  Subtotal managed:             1020 WCU

  Custom:
    allow-partner-ip (IPSet)       1
    block-high-risk-geo (Geo)      3
    rate-limit-login (RateBased)   2
    block-bad-user-agent (Byte)    1
    block-large-body (Size)        1
  Subtotal custom:                 8 WCU

  Total:                        1028 WCU (under 1500, 472 headroom)

Adding LinuxRuleSet (200) + WindowsRuleSet (200):
  1028 + 400 = 1428 WCU (72 headroom — tight)

Adding 3 more regex pattern set matches (3 × 25 = 75):
  1428 + 75 = 1503 WCU → EXCEEDS 1500 LIMIT → FAILS
```

### Referenced rule group offloading

A referenced rule group is a separate WAF rule group resource that
is referenced by the Web ACL. It has its OWN WCU budget (up to 1500
per rule group), separate from the ACL budget. The reference itself
consumes only 1 WCU in the ACL.

```bash
# Create a custom rule group (separate WCU budget)
RULE_GROUP_ARN=$(aws wafv2 create-rule-group \
  --scope CLOUDFRONT --region us-east-1 \
  --name "custom-exceptions" \
  --capacity 1500 \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName='custom-exceptions' \
  --query 'Summary.RuleGroupARN' --output text)

# Add rules to the rule group (consumes the rule group's budget, not the ACL's)
aws wafv2 update-rule-group \
  --scope CLOUDFRONT --region us-east-1 \
  --id <rule-group-id> \
  --rules '[...]' \
  --visibility-config ...

# Reference the rule group in the Web ACL (consumes 1 WCU in the ACL)
# In the Web ACL rules array:
# {
#   "Name": "custom-exceptions-ref",
#   "Priority": 5,
#   "Statement": {
#     "RuleGroupReferenceStatement": {
#       "ARN": "<rule-group-arn>"
#     }
#   },
#   "Action": { "Allow": {} },
#   "VisibilityConfig": { ... }
# }
```

**Key benefit:** offloading 200 WCU of custom rules to a referenced
rule group frees 200 WCU in the ACL budget for more managed rule
groups.

### WCU limit increase

If 1500 WCU is insufficient and rule group offloading is not viable,
request a limit increase via AWS Support. The hard limit varies by
account and region.

## Terraform examples

```hcl
# CloudFront-scoped Web ACL (must be us-east-1)
resource "aws_wafv2_web_acl" "production" {
  provider    = aws.use1
  name        = "production-cloudfront-acl"
  description = "Production WAF for CloudFront"
  scope       = "CLOUDFRONT"

  default_action {
    allow {}
  }

  # Custom allow at priority 0 (before any block)
  rule {
    name     = "allow-partner-ip"
    priority = 0
    action {
      allow {}
    }
    statement {
      ip_set_reference_statement {
        arn = aws_wafv2_ip_set.partner_cidrs[0].arn
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "allow-partner-ip"
      sampled_requests_enabled   = true
    }
  }

  # Managed rule group at priority 10
  rule {
    name     = "common-ruleset"
    priority = 10
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
        # version     = "Version_2.1"  # pin for production predictability
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "common-ruleset"
      sampled_requests_enabled   = true
    }
  }

  # Custom geo block at priority 40
  rule {
    name     = "block-high-risk-geo"
    priority = 40
    action {
      block {}
    }
    statement {
      geo_match_statement {
        country_codes = ["RU", "KP"]
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "block-high-risk-geo"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "production-cloudfront-acl"
    sampled_requests_enabled   = true
  }

  tags = {
    Environment = "production"
    Protected   = "cloudfront"
  }
}

# IP set in us-east-1 (same scope and region as the ACL)
resource "aws_wafv2_ip_set" "partner_cidrs" {
  provider        = aws.use1
  name            = "partner-cidrs"
  description     = "Known partner IP ranges"
  scope           = "CLOUDFRONT"
  ip_address_version = "IPV4"
  addresses       = ["203.0.113.0/24", "198.51.100.10/32"]
}

# Logging via Firehose
resource "aws_wafv2_web_acl_logging_configuration" "production" {
  provider        = aws.use1
  log_destination_configs = [
    aws_kinesis_firehose_delivery_stream.waf_logs.arn
  ]
  resource_arn = aws_wafv2_web_acl.production.arn

  redacted_fields {
    single_header {
      name = "Authorization"
    }
  }
}

resource "aws_kinesis_firehose_delivery_stream" "waf_logs" {
  provider = aws.use1
  name     = "aws-waf-logs-production"

  destination {
    s3 {
      role_arn   = aws_iam_role.firehose.arn
      bucket_arn = aws_s3_bucket.waf_logs.arn
    }
  }
}

# CloudFront association
resource "aws_cloudfront_distribution" "production" {
  # ...
  web_acl_id = aws_wafv2_web_acl.production.arn
}
```

## Common pitfalls

1. **Stacking too many managed rule groups.** CommonRuleSet (700) +
   SQLiRuleSet (200) + LinuxRuleSet (200) + WindowsRuleSet (200) =
   1300 WCU before any custom rules. Plan carefully.

2. **Forgetting that pinned versions stop updates.** A rule group
   pinned to `Version_1.0` will never receive new threat signatures.
   Review quarterly.

3. **Not using referenced rule groups for custom rules.** Custom
   rules in the Web ACL consume the ACL budget. Moving them to a
   referenced rule group frees ACL budget for managed groups.

4. **Bot Control and ATP are paid.** These managed rule groups have
   additional charges per request. Confirm budget before enabling.

## Step 4 - offload WCU to a referenced rule group (moved from SKILL.md)

**Offload WCU to a rule group** (up to 1500 WCU separately):

```bash
aws wafv2 create-rule-group \
  --scope CLOUDFRONT --region us-east-1 \
  --name "custom-exceptions" --capacity 1500 \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName='custom-exceptions'
# Reference it in the Web ACL via RuleGroupReferenceStatement (1 WCU)
```
