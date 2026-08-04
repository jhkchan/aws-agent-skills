# Baseline (no-skill) response: misconfigured-zero-rule-allow

This file captures what a generic assistant produces WITHOUT the
wafv2-web-acl-auditor skill loaded. Note: the baseline identifies the empty
rules array but misses the deterministic classification framework, the
severity matrix, and the structured VERDICT block the skill emits.

---

This Web ACL doesn't seem to have any rules configured. The `DefaultAction`
is set to `Allow`, which means all traffic will be allowed through to your
backend by default. Since the `Rules` array is empty, there's no inspection
happening at all — the WAF is effectively doing nothing.

You should add some managed rule groups like the AWS Managed Rules Common
Rule Set to provide baseline protection against common web exploits. You
might also want to enable CloudWatch metrics and sampled requests so you
can monitor traffic.

The visibility config has both metrics and sampled requests disabled, so
you won't have any observability into what's hitting the WAF.
