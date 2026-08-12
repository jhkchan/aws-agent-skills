# Baseline (no-skill) — regional-alb-rate-and-geo

> This is the response a model produces **without** the skill
> definition. It creates the Web ACL but misses the rate-based rule
> 5-minute evaluation window semantics, the FORWARDED_IP caveat
> behind proxies, the priority ordering requirement (geo block
> before rate-based), and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create the Web ACL and attach rules:

```bash
aws wafv2 create-web-acl \
  --name api-protection-acl \
  --scope REGIONAL \
  --default-action Allow={}
```

Then add a rate limit and a geo block, and associate with the ALB.
