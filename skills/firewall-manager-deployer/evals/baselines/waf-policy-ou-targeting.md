# Baseline (no-skill) — waf-policy-ou-targeting

> This is the response a model produces **without** the skill
> definition. It creates the FMS WAF policy but misses the admin account
> delegation check, the remediation grace period decision, the include/
> exclude tag interaction (exclude overrides include), the policy
> priority first-match-wins ordering, and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create the FMS policy:

```bash
aws fms put-policy \
  --policy-name org-waf-common-rules \
  --security-service-policy-data Type=WAFV2 \
  --include-map ORG_UNIT=ou-prod-abcdef
```

Use AWSManagedRulesCommonRuleSet and that should cover it.
