# Eval prompt: misconfigured-count-mode

Audit the following WAFv2 Web ACL configuration against effective-protection
principles. Pay close attention to the OverrideAction on each managed rule
group. Emit the standard VERDICT block (WEBACL, VERDICT, REASON, RISK,
GAPS, REMEDIATION).

Web ACL name: count-mode-acl
Web ACL config (describe-web-acl output):

```json
{
  "Name": "count-mode-acl",
  "Scope": "REGIONAL",
  "DefaultAction": { "Allow": {} },
  "Rules": [
    {
      "Name": "AWS-AWSManagedRulesCommonRuleSet",
      "Priority": 0,
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesCommonRuleSet"
        }
      },
      "OverrideAction": { "Count": {} },
      "VisibilityConfig": {
        "CloudWatchMetricsEnabled": true,
        "MetricName": "CommonRuleSet",
        "SampledRequestsEnabled": true
      }
    },
    {
      "Name": "AWS-AWSManagedRulesSQLiRuleSet",
      "Priority": 1,
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesSQLiRuleSet"
        }
      },
      "OverrideAction": { "Count": {} },
      "VisibilityConfig": {
        "CloudWatchMetricsEnabled": true,
        "MetricName": "SQLiRuleSet",
        "SampledRequestsEnabled": true
      }
    }
  ],
  "VisibilityConfig": {
    "CloudWatchMetricsEnabled": true,
    "MetricName": "count-mode-acl",
    "SampledRequestsEnabled": true
  }
}
```
