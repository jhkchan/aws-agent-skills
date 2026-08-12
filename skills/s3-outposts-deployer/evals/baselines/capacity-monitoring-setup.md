# Baseline (no-skill) — capacity-monitoring-setup

> This is the response a model produces **without** the skill
> definition. It creates the bucket but does not address the finite
> capacity constraint of Outpost storage, misses the endpoint requirement,
> and does not emit the READY_TO_DEPLOY checklist. Generated for
> with-skill-vs-baseline comparison.

---

Create the bucket:

```bash
aws s3 mb s3://monitored-bucket
```

Add a CloudWatch alarm for size if you want.
