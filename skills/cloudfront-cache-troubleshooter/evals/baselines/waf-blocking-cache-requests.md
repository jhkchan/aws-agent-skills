# Baseline (no-skill) response: waf-blocking-cache-requests

This file captures what a generic assistant produces WITHOUT the
cloudfront-cache-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, category-aware walk,
specific remediation).

---

Your CloudFront distribution is returning 403 on all `/api/*` requests.
Since the origin (ALB) returns 200 when accessed directly, the issue is
in the CloudFront layer.

Since you have a WAF web ACL attached, the WAF might be blocking the
requests. You should check the WAF rules to see if any are blocking
legitimate traffic.

You can also try removing the WAF from the distribution temporarily to
see if that resolves the issue:

```bash
aws cloudfront update-distribution --id E4D5E6F7G8 \
  --if-match <ETag> \
  --distribution-config file://config-no-waf.json
```

If removing the WAF fixes it, you know the WAF rules are too aggressive.
Adjust the rules and re-attach the WAF.

You should also check if your origin is returning errors that CloudFront
is caching, which could also cause 403s.
