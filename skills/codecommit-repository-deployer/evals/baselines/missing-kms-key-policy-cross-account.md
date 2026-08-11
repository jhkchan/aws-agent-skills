# Baseline (no-skill) — missing-kms-key-policy-cross-account

> This is the response a model produces **without** the skill
> definition. It grants cross-account access via the repository resource
> policy but does NOT flag the missing KMS key policy grant for the
> cross-account principal. The deployment will fail with AccessDenied
> when the cross-account principal tries to push or pull the encrypted
> repository. Does not emit a PREREQUISITES_MISSING verdict. Generated
> for with-skill-vs-baseline comparison.

---

Grant cross-account access to account 888888888888:

```bash
# Add resource policy granting the cross-account principal
```

The cross-account user should now be able to access the repository.
