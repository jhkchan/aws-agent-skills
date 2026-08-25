# Worked Examples - wafv2-web-acl-auditor

## Worked example: multi-rule aggregation, MISCONFIGURED (moved from SKILL.md)

A Web ACL with CommonRuleSet in BLOCK (good) but a shadow Allow rule at
priority 0 matching `/api/*`, no rate-based rule, and no logging:

```text
WEBACL: api-gateway-acl
VERDICT: MISCONFIGURED
REASON: Step 2: custom rule "api-bypass" at priority 0 with Action Allow
matches URIPath STARTS_WITH /api/, shadowing all managed rule groups
(priority 10+) for the entire API surface. No rate-based rule (Step 5) and
no logging configuration (Step 6) compound the exposure — the WAF is both
bypassed and blind.
RISK: CRITICAL
GAPS: shadow-rule, no-rate-limit, no-logging
REMEDIATION: (1) Move the api-bypass rule to a priority HIGHER than the
managed rule groups, or scope it to an exact-match health-check path and
remove the STARTS_WITH wildcard. (2) Add a rate-based rule with
AggregateKeyType FORWARDED_IP and HeaderName X-Forwarded-For. (3) Enable
logging to CloudWatch Logs or Kinesis Data Firehose.
```
