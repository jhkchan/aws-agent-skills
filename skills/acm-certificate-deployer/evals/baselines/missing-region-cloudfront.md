# Baseline (no-skill) — missing-region-cloudfront

> This is the response a model produces **without** the skill
> definition. It lists CLI commands without flagging the us-east-1
> requirement for CloudFront, and does NOT emit the
> PREREQUISITES_MISSING verdict. Generated for with-skill-vs-baseline
> comparison.

---

Sure, here's how to create an ACM certificate for CloudFront:

1. Request the certificate:
```bash
aws acm request-certificate \
  --domain-name www.example.com \
  --validation-method DNS
```

2. Add the DNS validation record to Route53.

3. Once issued, attach it to your CloudFront distribution.

Let me know if you need help!
