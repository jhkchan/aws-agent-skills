# Baseline (no-skill) — single-region-alb

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the anycast-IPs-pinned-
> at-creation constraint, the traffic dial vs endpoint weight
> distinction, the independent health check configuration, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-baseline
> comparison.

---

Create the accelerator:

```bash
aws globalaccelerator create-accelerator --name "my-accelerator"
```

Then add a listener and endpoint group:
