# Baseline (no-skill) — missing-safety-rule

> This is the response a model produces **without** the skill
> definition. It creates routing controls without safety rules and does
> not flag the missing safety rule as a prerequisite failure. Does not
> emit a PREREQUISITES_MISSING verdict. Generated for
> with-skill-vs-baseline comparison.

---

Sure, here are the routing controls:

```bash
aws route53-recovery-control-config create-routing-control \
  --cluster-arn <arn> --routing-control-name "cell-a"

aws route53-recovery-control-config create-routing-control \
  --cluster-arn <arn> --routing-control-name "cell-b"
```

No safety rules needed, just toggle them as you want.
