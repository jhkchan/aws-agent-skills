# Baseline (no-skill) — as2-connector-trading-partner

> This is the response a model produces **without** the skill
> definition. It mentions AS2 but misses the certificate exchange
> requirement, the local/partner profile model, the MDN signing
> configuration, and the READY_TO_DEPLOY checklist format. Generated
> for with-skill-vs-baseline comparison.

---

Create an AS2 connector:

```bash
aws transfer create-connector --url https://as2.acme.com
```

Configure the compression and encryption settings as needed.
