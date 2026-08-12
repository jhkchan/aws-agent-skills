# Baseline (no-skill) — revocation-configuration

> This is the response a model produces **without** the skill
> definition. It does not mention CRL configuration at all, missing
> that without a CRL a compromised certificate remains valid until its
> expiration date. Does not emit the READY_TO_DEPLOY checklist.
> Generated for with-skill-vs-baseline comparison.

---

For revocation, you can revoke certificates in your CA and they
should stop working. The trust anchor will pick it up
automatically.

```bash
openssl ca -revoke client-cert.pem
```

That should be enough.
