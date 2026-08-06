# Eval prompt: ok-comprehensive

Audit the following WAFv2 Web ACL configuration against effective-protection
principles. This ACL has 3 managed rule groups in BLOCK mode, a forwarded-IP
rate-based rule, logging, and full visibility. Evaluate whether this meets the
OK bar. Emit the standard VERDICT block (WEBACL, VERDICT, REASON, RISK, GAPS,
REMEDIATION).

Web ACL name: production-hardened-acl
Web ACL config (describe-web-acl output):

```json
{
  "Name": "production-hardened-acl",
  "Scope": "CLOUDFRONT",
  "DefaultAction": { "Allow": {} },
  "Rules": [
    {
      "Name": "AWS-AWSManagedRulesCommonRuleSet",
      "Priority": 10,
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesCommonRuleSet"
        }
      },
      "OverrideAction": { "None": {} },
      "VisibilityConfig": {
        "CloudWatchMetricsEnabled": true,
        "MetricName": "CommonRuleSet",
        "SampledRequestsEnabled": true
      }
    },
    {
      "Name": "AWS-AWSManagedRulesKnownBadInputsRuleSet",
      "Priority": 20,
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesKnownBadInputsRuleSet"
        }
      },
      "OverrideAction": { "None": {} },
      "VisibilityConfig": {
        "CloudWatchMetricsEnabled": true,
        "MetricName": "KnownBadInputs",
        "SampledRequestsEnabled": true
      }
    },
    {
      "Name": "AWS-AWSManagedRulesAmazonIpReputationList",
      "Priority": 30,
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesAmazonIpReputationList"
        }
      },
      "OverrideAction": { "None": {} },
      "VisibilityConfig": {
        "CloudWatchMetricsEnabled": true,
        "MetricName": "IPReputationList",
        "SampledRequestsEnabled": true
      }
    },
    {
      "Name": "rate-limit-forwarded-ip",
      "Priority": 40,
      "Action": { "Block": {} },
      "Statement": {
        "RateBasedStatement": {
          "Limit": 2000,
          "AggregateKeyType": "FORWARDED_IP",
          "EvaluationWindowSec": 300,
          "ForwardedIPConfig": {
            "HeaderName": "X-Forwarded-For",
            "FallbackBehavior": "MATCH"
          }
        }
      },
      "VisibilityConfig": {
        "CloudWatchMetricsEnabled": true,
        "MetricName": "rate-limit-forwarded-ip",
        "SampledRequestsEnabled": true
      }
    }
  ],
  "LoggingConfiguration": {
    "LogDestinationConfigs": ["arn:aws:firehose:us-east-1:123456789012:deliverystream/waf-logs"]
  },
  "VisibilityConfig": {
    "CloudWatchMetricsEnabled": true,
    "MetricName": "production-hardened-acl",
    "SampledRequestsEnabled": true
  }
}
```
