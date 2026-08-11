# Baseline (no-skill) — public-dns-cloudfront

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the us-east-1
> requirement for CloudFront, the apex + wildcard domain scoping,
> the DNS validation CNAME persistence requirement, the automatic
> renewal behavior, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Here's how to request an ACM certificate:

1. Request the certificate:
```bash
aws acm request-certificate \
  --domain-name example.com \
  --validation-method DNS
```

2. Add the CNAME to Route53 (check the console for the record).

3. Wait for it to be issued, then attach to CloudFront.

That should work.
