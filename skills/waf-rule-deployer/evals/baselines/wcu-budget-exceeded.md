# Baseline (no-skill) — wcu-budget-exceeded

> This is the response a model produces **without** the skill
> definition. It attempts to create the Web ACL with all requested
> managed rule groups and custom rules without flagging the WCU
> budget overage. Does not emit a PREREQUISITES_MISSING verdict.
> Generated for with-skill-vs-baseline comparison.

---

Sure, here is the Web ACL with all the managed rule groups:

```bash
aws wafv2 create-web-acl \
  --name comprehensive-acl \
  --scope CLOUDFRONT \
  --default-action Allow={}
```

Add all nine managed rule groups and the 20 custom regex rules.
