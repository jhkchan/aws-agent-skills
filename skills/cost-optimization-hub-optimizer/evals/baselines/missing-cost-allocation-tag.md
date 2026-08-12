# Baseline (no-skill) — missing-cost-allocation-tag

> This is the response a model produces **without** the skill
> definition. It attempts the tag filter without flagging that
> the user-defined tags are NOT activated in Cost Explorer, so
> the filter will silently return no matches. Does not emit the
> FURTHER_OPTIMIZATION_AVAILABLE verdict or the activation
> remediation. Generated for with-skill-vs-baseline comparison.

---

You can filter recommendations by tag like this:

```bash
aws cost-optimization-hub get-recommendations \
  --filter '{"tags":{"Environment":"production"}}'
```

If the results look empty, double-check the tag values.
