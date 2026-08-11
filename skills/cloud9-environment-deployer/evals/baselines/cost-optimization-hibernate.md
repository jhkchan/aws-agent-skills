# Baseline (no-skill) — cost-optimization-hibernate

> This is the response a model produces **without** the skill
> definition. It creates the environment but does not set the
> aggressive 15-minute auto-hibernation, missing the key cost
> optimization. Does not emit a READY_TO_DEPLOY checklist.
> Generated for with-skill-vs-baseline comparison.

---

```bash
aws cloud9 create-environment-ec2 \
  --name "budget-ide" \
  --instance-type t3.micro
```

That should be cheap enough.
