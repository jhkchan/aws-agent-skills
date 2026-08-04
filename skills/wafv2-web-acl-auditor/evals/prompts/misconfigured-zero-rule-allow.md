# Eval prompt: misconfigured-zero-rule-allow

Audit the following WAFv2 Web ACL configuration against effective-protection
principles. Emit the standard VERDICT block (WEBACL, VERDICT, REASON, RISK,
GAPS, REMEDIATION).

Web ACL name: open-door-acl
Web ACL config (describe-web-acl output):

```json
{
  "Name": "open-door-acl",
  "Scope": "REGIONAL",
  "DefaultAction": { "Allow": {} },
  "Rules": [],
  "VisibilityConfig": {
    "CloudWatchMetricsEnabled": false,
    "MetricName": "open-door-acl",
    "SampledRequestsEnabled": false
  }
}
```
