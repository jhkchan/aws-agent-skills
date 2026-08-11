# Baseline (no-skill) — overlapping-priority-conflict

> This is the response a model produces **without** the skill
> definition. It creates the WAF policy at priority 1 without flagging
> that an existing WAF policy already occupies priority 1 for the same
> OU. FMS first-match-wins means the new policy would silently never
> apply. Does not emit a PREREQUISITES_MISSING verdict. Generated for
> with-skill-vs-baseline comparison.

---

Create the policy:

```bash
aws fms put-policy \
  --policy-name org-waf-secondary \
  --security-service-policy-data Type=WAFV2 \
  --include-map ORG_UNIT=ou-prod-abcdef
```

Use AWSManagedRulesSQLiRuleSet and monitor-only remediation.
