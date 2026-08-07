# Baseline (no-skill) response: missing-required-fields

This file captures what a generic assistant produces WITHOUT the
cloudfront-distribution-deployer skill loaded — the contrast that proves
the skill adds structure (PREREQUISITES_MISSING verdict with enumerated
REQUIRED fields, refusal to silently guess defaults).

---

Here's a CloudFront distribution plan for your S3 bucket with the
app.example.com domain.

Architecture:

- Origin: app-assets.s3.us-east-1.amazonaws.com
- Domain: app.example.com
- Cache: CachingOptimized
- Price class: 100

Steps:

1. Create the distribution.
2. Configure the cache policy as CachingOptimized.
3. Set the alternate domain name app.example.com.
4. Deploy.

I'll use sensible defaults for the other settings — HTTPS redirect, the
default TLS, and CloudFront's default domain. You can add a custom cert
later if needed.

Let me know if you want to add WAF or logging after the initial setup.
