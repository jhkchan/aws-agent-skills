# Baseline (no-skill) — resource-set-type-mapping

> This is the response a model produces **without** the skill
> definition. It does not know the correct CloudFormation resource
> type strings for resource sets, may confuse NLB with ALB types, and
> does not emit the READY_TO_DEPLOY checklist. Generated for
> with-skill-vs-baseline comparison.

---

Create resource sets and readiness checks:

```bash
aws route53-recovery-readiness create-resource-set \
  --resource-set-name "app-resources" \
  --resource-set-type "LoadBalancer"
```

Then add readiness checks on top.
