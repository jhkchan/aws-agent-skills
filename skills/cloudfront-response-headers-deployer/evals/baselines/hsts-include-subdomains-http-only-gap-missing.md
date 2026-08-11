# Baseline (no-skill) response: hsts-include-subdomains-http-only-gap-missing

This file captures what a generic assistant produces WITHOUT the
cloudfront-response-headers-deployer skill loaded — the contrast that
proves the skill catches the HSTS includeSubDomains scope mismatch
before the operator ships an irreversible config.

---

To set up HSTS on your CloudFront distribution:

1. Create a response headers policy named `prod-hsts-policy`.
2. Enable Strict-Transport-Security:
   - Max-age: 63072000 (2 years)
   - Include subdomains: checked
   - Preload: checked
3. Attach to the distribution's default cache behavior.

This will force HTTPS for example.com and all subdomains for 2 years.
That's the most secure configuration.

Let me know if you need help.
