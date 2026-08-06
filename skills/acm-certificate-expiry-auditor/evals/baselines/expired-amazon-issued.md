# Baseline (no-skill) response: expired-amazon-issued

This file captures what a generic assistant produces WITHOUT the
acm-certificate-expiry-auditor skill loaded.

---

This certificate expired on July 15, 2026. Since today is August 4, 2026, it
has been expired for about 20 days. The certificate is in use by an ALB, so
HTTPS on api.example.com is likely failing.

You should request a new certificate and switch the ALB listener to use it.
Once the new certificate is in place, you can delete the expired one.

```bash
aws acm request-certificate --domain-name api.example.com --validation-method DNS
```
