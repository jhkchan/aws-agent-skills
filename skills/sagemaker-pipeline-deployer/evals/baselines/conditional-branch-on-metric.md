# Baseline (no-skill) — conditional-branch-on-metric

> This is the response a model produces **without** the skill
> definition. It writes a Python `if accuracy >= 0.9:` instead of a
> ConditionStep (the conditional is a runtime DAG branch, not authoring-
> time Python), misses the JsonGet-from-PropertyFile mechanism for
> reading the metric at execution time, and does not emit the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Add an if-statement in your pipeline code:

```python
if accuracy >= 0.9:
    create_model()
    register_model()
else:
    fail()
```

That will branch the pipeline based on the metric.
