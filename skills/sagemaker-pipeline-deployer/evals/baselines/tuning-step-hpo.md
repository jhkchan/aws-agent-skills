# Baseline (no-skill) — tuning-step-hpo

> This is the response a model produces **without** the skill
> definition. It wires the TuningStep but hardcodes the best-model S3
> path (missing get_top_model_s3_uri, which is the only correct way to
> consume the best tuned model artifact downstream), misses the
> account-quota implication of max_jobs=20, and does not emit the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Add a tuning step with 20 jobs and 4 parallel:

```python
tuner = HyperparameterTuner(estimator, "validation:auc", "Maximize",
    {"max_depth": IntegerParameter(3, 10), "eta": ContinuousParameter(0.05, 0.4)},
    max_jobs=20, max_parallel_jobs=4)
tuning = TuningStep(name="Tune", tuner=tuner, inputs={...})

# Use the best model
model = Model(model_data="s3://my-bucket/tuning/best/model.tar.gz", ...)
```

Then register the model.
