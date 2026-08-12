# Baseline (no-skill) — caching-and-parallelism

> This is the response a model produces **without** the skill
> definition. It enables caching and parallelism but assumes caching
> means re-runs are free (missing the cache-key composition and the
> image-tag-vs-digest gotcha that makes `:v1.4.2` either invalidate
> correctly or not depending on tag immutability), and does not emit
> the READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Turn on caching and set parallelism to 5:

```python
pipeline = Pipeline(
    name="training-pipeline",
    steps=[...],
    enable_caching=True,
)
pipeline.start(parallelism_config={"MaxParallelExecutionSteps": 5})
```

Caching will skip unchanged steps automatically.
