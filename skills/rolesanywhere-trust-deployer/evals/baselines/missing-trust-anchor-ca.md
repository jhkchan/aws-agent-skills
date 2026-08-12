# Baseline (no-skill) — missing-trust-anchor-ca

> This is the response a model produces **without** the skill
> definition. It attempts to create the profile without flagging that
> no CA certificate has been provided (no trust anchor can exist) and
> that the IAM role's trust policy lacks the
> rolesanywhere.amazonaws.com principal. Both gaps will cause opaque
> AccessDenied failures. Does not emit a PREREQUISITES_MISSING
> verdict. Generated for with-skill-vs-baseline comparison.

---

Sure, here's the profile:

```bash
aws rolesanywhere create-profile \
  --name my-profile \
  --role-arns arn:aws:iam::123456789012:role/RolesAnywhereCIRunner \
  --duration-seconds 3600
```

You can figure out the trust anchor later.
