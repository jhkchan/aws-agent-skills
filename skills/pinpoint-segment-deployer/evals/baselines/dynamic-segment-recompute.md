# Baseline (no-skill) — dynamic-segment-recompute

> This is the response a model produces **without** the skill
> definition. It creates the segment and campaign but treats the
> segment as a static list (misses the dynamic-recompute behavior
> where the segment re-evaluates at send time and the endpoint count
> differs from design time), does not flag the dimension composition
> (ALL vs ANY), and does not emit the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create the segment:

```bash
aws pinpoint create-segment \
  --application-id app-abc123 \
  --write-segment-request '{"Name":"active-mobile-7d"}'
```

Then create the campaign targeting it.
