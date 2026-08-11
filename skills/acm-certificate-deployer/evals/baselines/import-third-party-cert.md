# Baseline (no-skill) — import-third-party-cert

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the manual renewal
> warning (imported certs are NOT auto-renewed), the PEM format
> requirements, and the READY_TO_DEPLOY checklist format. Generated
> for with-skill-vs-baseline comparison.

---

To import a certificate into ACM:

1. Import the PEM files:
```bash
aws acm import-certificate \
  --certificate fileb://certificate.pem \
  --private-key fileb://private-key.pem \
  --certificate-chain fileb://chain.pem
```

2. The certificate should now be available in ACM.

That's it.
