# Baseline (no-skill) — weighted-canary-traffic-split

> This is the response a model produces **without** the skill
> definition. It creates two target groups but misses that weights are
> relative (not percentages that must sum to 100), that health check
> status determines which targets receive traffic, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-baseline
> comparison.

---

Create two target groups and add a rule:

```bash
aws vpc-lattice create-target-group --name tg-canary --type INSTANCE
```

Route some traffic to canary. Use weights 20 and 80.
