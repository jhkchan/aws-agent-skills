# Baseline (no-skill) — account-termination

> This is the response a model produces **without** the skill
> definition. It deletes the account directly without going through the
> Service Catalog termination flow, misses the SSO assignment cleanup,
> and does not note the 90-day SUSPENDED period before permanent closure.
> Generated for with-skill-vs-baseline comparison.

---

Close the account:

```bash
aws organizations close-account --account-id 111122223333
```

The account will be deleted.
