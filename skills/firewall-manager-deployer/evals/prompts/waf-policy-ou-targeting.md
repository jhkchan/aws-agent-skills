# Eval: waf-policy-ou-targeting

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — WAF policy (WAFV2), OU-based targeting, AWSManagedRulesCommonRuleSet + KnownBadInputsRuleSet, auto-remediation with 7-day grace, include/exclude tags

## Prompt

Create an FMS WAF policy named org-waf-common-rules targeting
OU ou-prod-abcdef in us-east-1. FMS admin account is 111111111111.
Use AWSManagedRulesCommonRuleSet and
AWSManagedRulesKnownBadInputsRuleSet managed rule groups.
Remediation should be auto-apply with a 7-day grace period.
Include tags: Environment=production. Exclude tags:
ComplianceExempt=true. Policy priority 1.
