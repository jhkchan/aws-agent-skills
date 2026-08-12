# Baseline (no-skill) — social-provider-guest-access

> This is the response a model produces **without** the skill
> definition. It lists some CLI commands but misses the
> ServerSideTokenCheck requirement, the unauthenticated role trust
> policy distinction, and the READY_TO_DEPLOY checklist. Generated for
> with-skill-vs-baseline comparison.

---

Set up Google and Facebook:

```bash
aws cognito-identity create-identity-pool \
  --identity-pool-name "social-app-pool"
```

Then add your providers and roles.
