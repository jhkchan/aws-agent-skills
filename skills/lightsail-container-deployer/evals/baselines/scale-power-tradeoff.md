# Baseline (no-skill) — scale-power-tradeoff

> This is the response a model produces **without** the skill
> definition. It creates the service but does not explain the power-vs-
> scale trade-off, does not flag that 2 nodes provides redundancy vs
> 1 node, and misses the READY_TO_DEPLOY checklist format. Generated
> for with-skill-vs-baseline comparison.

---

Create the container service:

```bash
aws lightsail create-container-service \
  --service-name worker-service --power medium --scale 2
```

Deploy the worker image.
