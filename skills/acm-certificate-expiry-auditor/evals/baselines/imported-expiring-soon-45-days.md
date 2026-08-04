# Baseline (no-skill) response: imported-expiring-soon-45-days

This file captures what a generic assistant produces WITHOUT the
acm-certificate-expiry-auditor skill loaded.

---

This is an imported certificate expiring on September 18, 2026 (about 45
days away). Since it is imported, ACM will not renew it automatically — you
need to get a new certificate from your external CA and re-import it before
the expiry date.

```bash
aws acm import-certificate \
  --certificate file://new.pem \
  --private-key file://new.key \
  --certificate-chain file://chain.pem
```

Plan to do this in the next few weeks to avoid cutting it close.
