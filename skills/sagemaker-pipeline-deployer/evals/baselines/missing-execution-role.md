# Baseline (no-skill) — missing-execution-role

> This is the response a model produces **without** the skill
> definition. It proceeds to build the pipeline without flagging the
> missing execution role or the `iam:PassRole` requirement on the
> default SageMaker role for child-job roles — the pipeline will create
> successfully but fail at the first job-launching step. Does not emit a
> PREREQUISITES_MISSING verdict. Generated for with-skill-vs-baseline
> comparison.

---

Here is the pipeline definition:

```python
pipeline = Pipeline(
    name="training-pipeline",
    steps=[preprocess, train, register],
)
pipeline.upsert()
pipeline.start()
```

The default SageMaker role should be fine.
