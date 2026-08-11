# Eval: overlapping-priority-conflict

**Difficulty:** medium
**Branch:** PREREQUISITES_MISSING — existing WAF policy at priority 1 targeting same OU; first-match wins means the new policy would never apply

## Prompt

Create an FMS WAF policy named org-waf-secondary targeting OU
ou-prod-abcdef in us-east-1. FMS admin account is 111111111111.
There is already a WAF policy org-waf-primary at priority 1
targeting the same OU. The new policy should be at priority 1.
Use AWSManagedRulesSQLiRuleSet. Remediation monitor-only.
