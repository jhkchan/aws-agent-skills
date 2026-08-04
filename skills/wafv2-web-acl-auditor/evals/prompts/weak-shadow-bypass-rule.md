# Eval prompt: weak-shadow-bypass-rule

Audit the following WAFv2 Web ACL configuration against effective-protection
principles. Pay close attention to rule priority ordering and how a custom
rule at a lower priority might interact with managed rule groups at higher
priorities. Emit the standard VERDICT block (WEBACL, VERDICT, REASON, RISK,
GAPS, REMEDIATION).

Web ACL name: shadow-bypass-acl
Web ACL config (describe-web-acl output):

```json
{
  "Name": "shadow-bypass-acl",
  "Scope": "REGIONAL",
  "DefaultAction": { "Block": {} },
  "Rules": [
    {
      "Name": "api-allow-rule",
      "Priority": 0,
      "Action": { "Allow": {} },
      "Statement": {
        "ByteMatchStatement": {
          "SearchString": "/api/",
          "FieldToMatch": { "UriPath": {} },
          "TextTransformations": [{ "Priority": 0, "Type": "NONE" }],
          "PositionalConstraint": "STARTS_WITH"
        }
      },
      "VisibilityConfig": {
        "CloudWatchMetricsEnabled": true,
        "MetricName": "api-allow-rule",
        "SampledRequestsEnabled": true
      }
    },
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
    }
  ],
  "VisibilityConfig": {
    "CloudWatchMetricsEnabled": true,
    "MetricName": "shadow-bypass-acl",
    "SampledRequestsEnabled": true
  }
}
```
