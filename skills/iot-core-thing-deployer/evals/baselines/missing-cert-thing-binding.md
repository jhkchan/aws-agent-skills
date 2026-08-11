# Baseline (no-skill) — missing-cert-thing-binding

> This is the response a model produces **without** the skill
> definition. It creates the thing and policy but does not flag the
> missing cert-to-thing binding as a prerequisite failure. Generated
> for with-skill-vs-baseline comparison.

---

Create the thing:

```bash
aws iot create-thing --thing-name device-001
```

Create and attach policy:

```bash
aws iot create-policy --policy-name device-policy --policy-document '...'
```

You should be good to go.
