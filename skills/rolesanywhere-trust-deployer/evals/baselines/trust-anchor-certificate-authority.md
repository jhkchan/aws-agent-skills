# Baseline (no-skill) — trust-anchor-certificate-authority

> This is the response a model produces **without** the skill
> definition. It emits the create-trust-anchor CLI command but misses
> that the IAM role must have a trust policy explicitly allowing
> rolesanywhere.amazonaws.com as a principal (a role trusting only
> ec2.amazonaws.com cannot be assumed via Roles Anywhere), does not
> flag the CERTIFICATE_BUNDLE source type, and does not emit the
> READY_TO_DEPLOY checklist. Generated for with-skill-vs-baseline
> comparison.

---

Here's how to create the trust anchor:

```bash
aws rolesanywhere create-trust-anchor \
  --name prod-pki-trust-anchor \
  --source file://source.json
```

Put your CA certificate in the source file and you should be good.
