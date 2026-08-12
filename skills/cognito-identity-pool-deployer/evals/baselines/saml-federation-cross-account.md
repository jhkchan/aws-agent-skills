# Baseline (no-skill) — saml-federation-cross-account

> This is the response a model produces **without** the skill
> definition. It does not address the cross-account trust policy
> requirement, misses the SAML provider trust conditions, and does
> not emit the READY_TO_DEPLOY checklist. Generated for
> with-skill-vs-baseline comparison.

---

Create the pool with SAML:

```bash
aws cognito-identity create-identity-pool \
  --identity-pool-name "corp-saml-pool"
```

Point it to your SAML role.
