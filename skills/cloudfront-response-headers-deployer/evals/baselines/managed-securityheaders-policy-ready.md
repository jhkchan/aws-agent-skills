# Baseline (no-skill) response: managed-securityheaders-policy-ready

This file captures what a generic assistant produces WITHOUT the
cloudfront-response-headers-deployer skill loaded — the contrast that
proves the skill knows the managed policy IDs by heart and the
attach-vs-embed distinction.

---

To attach the managed SecurityHeadersPolicy:

1. Go to CloudFront → Distributions → select E27TVSIEXAMPLE.
2. Edit the DefaultCacheBehavior.
3. Under Response Headers Policy, select "SecurityHeadersPolicy" from
   the dropdown.
4. Save changes and wait for the distribution to redeploy.

The managed policy includes HSTS, X-Frame-Options, X-Content-Type-Options,
and Referrer-Policy. You can also create a custom policy if you need
Content-Security-Policy.

Let me know if you need anything else.
