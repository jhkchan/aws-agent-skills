# Baseline (no-skill) — user-pool-provider-rules-mapping

> This is the response a model produces **without** the skill
> definition. It creates the identity pool but misses the rules-based
> role mapping (uses token-based only), forgets the unauthenticated
> role, and does not emit the READY_TO_DEPLOY checklist. Generated for
> with-skill-vs-baseline comparison.

---

Create the pool:

```bash
aws cognito-identity create-identity-pool \
  --identity-pool-name "app-identity-pool" \
  --allow-unauthenticated-identities
```

Then set the authenticated role and you should be fine.
