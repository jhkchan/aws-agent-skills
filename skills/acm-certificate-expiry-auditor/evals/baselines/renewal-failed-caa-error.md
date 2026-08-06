# Baseline (no-skill) response: renewal-failed-caa-error

This file captures what a generic assistant produces WITHOUT the
acm-certificate-expiry-auditor skill loaded.

---

The certificate renewal failed with a CAA_ERROR. This usually means your
domain's CAA record does not authorize the certificate authority that ACM
uses. The certificate expires on August 24, 2026, which is about 20 days
away, so this is urgent.

Check your CAA records and make sure ACM's issuer is allowed:

```
dig www.example.com CAA
```

Add a record like `www.example.com. CAA 0 issue "amazon.com"` if missing.
ACM should retry the renewal automatically after the DNS change propagates.
