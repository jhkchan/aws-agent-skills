# Baseline (no-skill) — missing-authenticated-role

> This is the response a model produces **without** the skill
> definition. It creates the identity pool without flagging the
> missing authenticated IAM role and trust policy as a prerequisite
> failure. Does not emit a PREREQUISITES_MISSING verdict. Generated for
> with-skill-vs-baseline comparison.

---

Sure, here's the pool:

```bash
aws cognito-identity create-identity-pool \
  --identity-pool-name "quick-pool"
```

You can add roles later.
