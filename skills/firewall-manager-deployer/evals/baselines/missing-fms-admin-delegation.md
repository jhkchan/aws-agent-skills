# Baseline (no-skill) — missing-fms-admin-delegation

> This is the response a model produces **without** the skill
> definition. It attempts to create the FMS WAF policy without checking
> that the FMS administrator account has been delegated, which will fail
> with AccessDeniedException. Does not emit a PREREQUISITES_MISSING
> verdict. Generated for with-skill-vs-baseline comparison.

---

Sure, here's the policy:

```bash
aws fms put-policy \
  --policy-name org-waf-policy \
  --security-service-policy-data Type=WAFV2 \
  --include-map ORG_UNIT=ou-prod-abcdef
```

Then add the managed rule group and enable remediation.
