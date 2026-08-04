# Eval prompt: adequate-good-baseline

Audit the following WAFv2 Web ACL configuration against effective-protection
principles. This ACL has CommonRuleSet and KnownBadInputsRuleSet in BLOCK
mode, a rate-based rule, and logging. Consider what gaps remain. Emit the
standard VERDICT block (WEBACL, VERDICT, REASON, RISK, GAPS, REMEDIATION).

Web ACL name: baseline-protected-acl
Web ACL config (describe-web-acl output):

```json
{
  "Name": "baseline-protected-acl",
  "Scope": "REGIONAL",
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
      "Name": "rate-limit-rule",
      "Priority": 30,
      "Action": { "Block": {} },
      "Statement": {
        "RateBasedStatement": {
          "Limit": 2000,
          "AggregateKeyType": "IP",
          "EvaluationWindowSec": 300
        }
      },
      "VisibilityConfig": {
        "CloudWatchMetricsEnabled": true,
        "MetricName": "rate-limit-rule",
        "SampledRequestsEnabled": true
      }
    }
  ],
  "LoggingConfiguration": {
    "LogDestinationConfigs": ["arn:aws:logs:us-east-1:123456789012:log-group:waf-logs"]
  },
  "VisibilityConfig": {
    "CloudWatchMetricsEnabled": true,
    "MetricName": "baseline-protected-acl",
    "SampledRequestsEnabled": true
  }
}
```
