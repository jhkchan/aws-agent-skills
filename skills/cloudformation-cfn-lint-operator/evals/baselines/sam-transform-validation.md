# Baseline (no-skill) — sam-transform-validation

> This is the response a model produces **without** the skill
> definition. It runs cfn-lint directly on the SAM template without
> expanding the transform first (missing the key insight that cfn-lint
> has only partial SAM support), does not run cfn-nag on the expanded
> output, and lacks the OPERATION_COMPLETED checklist format.
> Generated for with-skill-vs-baseline comparison.

---

To validate your SAM template:

```bash
cfn-lint template-sam.yaml
```

Then deploy with `sam deploy`.
