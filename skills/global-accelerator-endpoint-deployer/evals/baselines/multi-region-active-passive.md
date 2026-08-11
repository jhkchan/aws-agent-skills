# Baseline (no-skill) — multi-region-active-passive

> This is the response a model produces **without** the skill
> definition. It creates the accelerator but misses the traffic dial
> failover semantics (DR must have dial 0.0, not removed), the
> independent health check configuration, the flow logs setup, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-baseline
> comparison.

---

Create the accelerator and add endpoints in both regions:

```bash
aws globalaccelerator create-accelerator --name "prod-accelerator"
```

Add ALB endpoints to each region.
