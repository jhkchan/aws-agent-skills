# Baseline (no-skill) — missing-domain-prerequisite

> This is the response a model produces **without** the skill
> definition. It attempts to create the repository without checking
> whether the parent domain exists (create-repository will fail with
> a validation error). Does not emit a PREREQUISITES_MISSING verdict.
> Generated for with-skill-vs-baseline comparison.

---

Create the repository:

```bash
aws codeartifact create-repository \
  --domain my-domain \
  --repository my-packages \
  --region us-east-1
```

That should work.
