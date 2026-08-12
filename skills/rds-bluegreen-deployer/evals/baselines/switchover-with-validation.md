# Baseline (no-skill) — switchover-with-validation

> This is the response a model produces **without** the skill
> definition. It performs the switchover without confirming green
> validation results, misses the switchover timeout significance, does
> not note the endpoint CNAME auto-follow behavior, does not warn about
> application retry requirements, and lacks the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

To switch over your Blue/Green Deployment:

```bash
aws rds switchover-blue-green-deployment \
  --blue-green-deployment-identifier bg-prod-upgrade-2026
```

That should do it.
