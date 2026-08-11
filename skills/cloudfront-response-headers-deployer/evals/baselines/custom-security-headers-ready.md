# Baseline (no-skill) response: custom-security-headers-ready

This file captures what a generic assistant produces WITHOUT the
cloudfront-response-headers-deployer skill loaded — the contrast that
proves the skill catches Override semantics, CSP compatibility, HSTS
scope, and CORS credentials validation.

---

Here's how to add security headers to your CloudFront distribution:

1. Go to CloudFront → Response Headers Policies → Create policy.
2. Name it `prod-security-headers-policy`.
3. Enable the security headers:
   - Content-Security-Policy: `default-src 'self'`
   - Strict-Transport-Security: max-age 63072000
   - X-Frame-Options: DENY
   - X-Content-Type-Options: nosniff
4. Enable CORS:
   - Allow origins: `*`
   - Allow methods: GET, POST, OPTIONS
   - Allow credentials: true
5. Save and attach to your distribution's default cache behavior.

Wait for the distribution to redeploy and you should see the headers in
your browser. Let me know if you need help with any of the values.
