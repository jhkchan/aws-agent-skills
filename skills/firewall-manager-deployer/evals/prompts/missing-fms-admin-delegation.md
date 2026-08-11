# Eval: missing-fms-admin-delegation

**Difficulty:** medium
**Branch:** PREREQUISITES_MISSING — no FMS administrator account delegated; put-policy will fail with AccessDeniedException

## Prompt

Create an FMS WAF policy named org-waf-policy targeting OU
ou-prod-abcdef in us-east-1. No FMS admin account has been
delegated yet. Use AWSManagedRulesCommonRuleSet. Remediation
auto-apply with 7-day grace.
