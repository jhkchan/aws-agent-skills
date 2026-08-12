# Baseline (no-skill) — principal-tag-abac-mapping

> This is the response a model produces **without** the skill
> definition. It does not know how to configure principal tag mapping
> for ABAC, misses the tag-to-claim attribute mapping, and does not
> emit the READY_TO_DEPLOY checklist. Generated for
> with-skill-vs-baseline comparison.

---

Create the pool:

```bash
aws cognito-identity create-identity-pool \
  --identity-pool-name "abac-pool"
```

Set the authenticated role. ABAC should work with tags somehow.
