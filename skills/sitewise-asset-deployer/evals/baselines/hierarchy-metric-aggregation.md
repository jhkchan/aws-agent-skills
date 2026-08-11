# Baseline (no-skill) — hierarchy-metric-aggregation

> This is the response a model produces **without** the skill
> definition. It creates the parent and child models but misses that
> hierarchies must be defined in the parent MODEL (not on the asset
> instance at runtime), the hierarchy name-to-child-model binding, and
> the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the two asset models:

```bash
aws iotsitewise create-asset-model --asset-model-name "Production Line"
aws iotsitewise create-asset-model --asset-model-name "Machine"
```

Then create the assets and link them.
