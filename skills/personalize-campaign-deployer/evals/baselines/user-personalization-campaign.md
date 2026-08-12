# Baseline (no-skill) — user-personalization-campaign

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but picks the wrong recipe (SIMS
> or Popularity-Counting), misses the minProvisionedTPS cost-floor
> implication, forgets the event tracker, and omits the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create a dataset group, then a solution with the SIMS recipe:

```bash
aws personalize create-dataset-group --name retail-recs
aws personalize create-solution \
  --dataset-group-arn <arn> \
  --recipe-arn arn:aws:personalize:::recipe/aws-sims
```

Then create a campaign with default settings and you should be good.
