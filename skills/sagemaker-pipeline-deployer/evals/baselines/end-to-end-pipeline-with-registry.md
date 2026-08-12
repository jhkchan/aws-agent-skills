# Baseline (no-skill) — end-to-end-pipeline-with-registry

> This is the response a model produces **without** the skill
> definition. It strings steps into a sequential list (missing the DAG
> dependency model and property-reference wiring), assumes the steps
> list order is the execution order, forgets the
> `iam:PassRole` requirement on the pipeline execution role for
> child-job roles, treats RegisterModel as "deployment" (missing the
> PendingManualApproval gate), and does not emit the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Sure — define the pipeline as a list of steps in order:

```python
pipeline = Pipeline(
    name="xgb-training-pipeline",
    steps=[preprocess, train, evaluate, check_auc, create_model, transform, register],
)
```

The steps will run in that order. RegisterModel deploys the model.
Caching is on by default.
