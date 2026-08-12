# Baseline (no-skill) — segment-based-multivariate-holdout

> This is the response a model produces **without** the skill
> definition. It creates the journey but uses a conditional split
> instead of a multivariate split for the A/B test (or sets
> percentages that do not sum to 100), and confuses the holdout
> with a multivariate branch that sends no message (participant
> still enters the journey). Does not emit a READY_TO_DEPLOY
> checklist. Generated for with-skill-vs-baseline comparison.

---

Create the journey with a split:

```bash
aws pinpoint create-journey --application-id app-xyz789 \
  --write-journey-request '{"Name":"WeeklyPromoABTest"}'
```

Add a 50/50 split and a 10% holdout branch.
