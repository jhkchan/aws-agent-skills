# Eval prompt: weak-minimal-no-logging

Audit the following WAFv2 Web ACL configuration against effective-protection
principles. Consider managed-rule coverage, rate-based rules, logging, and
visibility. Emit the standard VERDICT block (WEBACL, VERDICT, REASON, RISK,
GAPS, REMEDIATION).

Web ACL name: minimal-acl
Web ACL config (describe-web-acl output):

```json
{
  "Name": "minimal-acl",
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
        "CloudWatchMetricsEnabled": false,
        "MetricName": "CommonRuleSet",
        "SampledRequestsEnabled": false
      }
    }
  ],
  "VisibilityConfig": {
    "CloudWatchMetricsEnabled": false,
    "MetricName": "minimal-acl",
    "SampledRequestsEnabled": false
  }
}
```
