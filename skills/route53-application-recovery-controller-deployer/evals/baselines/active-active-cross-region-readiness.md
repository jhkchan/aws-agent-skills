# Baseline (no-skill) — active-active-cross-region-readiness

> This is the response a model produces **without** the skill
> definition. It lists some CLI commands but misses the OR safety rule
> threshold 2 requirement for three-cell active-active, the readiness
> check cross-region validation, and the READY_TO_DEPLOY checklist.
> Generated for with-skill-vs-baseline comparison.

---

Set up routing controls across your regions:

```bash
aws route53-recovery-control-config create-routing-control \
  --cluster-arn <arn> --routing-control-name "cell-a"
```

Repeat for each cell and toggle as needed.
