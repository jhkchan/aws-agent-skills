# Baseline (no-skill) response: alb-custom-origin-deploy

This file captures what a generic assistant produces WITHOUT the
cloudfront-distribution-deployer skill loaded — the contrast that proves
the skill adds structure (https-only origin protocol enforcement, custom
origin headers for origin auth, response headers policy for security
headers, managed cache policy selection, real-time logging).

---

To put CloudFront in front of your ALB, you'll set up a distribution
with the ALB as a custom origin.

Architecture:

- Origin: prod-alb.us-east-1.elb.amazonaws.com
- Cache behavior: disabled (dynamic content)
- HTTPS redirect for viewers
- WAF attached

Commands:

1. aws cloudfront create-distribution with origin pointing at ALB
2. Configure the WAF
3. Deploy

You can forward headers to the ALB by configuring the cache behavior.
Make sure the ALB accepts HTTPS.

The distribution should work for your dynamic API. Cache will be
disabled so requests always hit the ALB.

Let me know if you need help configuring the cache policy.
