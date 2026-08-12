# Baseline (no-skill) — cloudfront-managed-and-custom-allow

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the CloudFront scope
> us-east-1 constraint, the specific-allow-before-broad-block
> priority ordering (allow must be priority 0 before geo block),
> the WCU budget calculation, the Firehose aws-waf-logs-* naming
> requirement, and the READY_TO_DEPLOY checklist format. Generated
> for with-skill-vs-baseline comparison.

---

Here is a Web ACL with the managed rules and custom rules:

```bash
aws wafv2 create-web-acl \
  --name production-cloudfront-acl \
  --scope CLOUDFRONT \
  --default-action Allow={}
```

Add the managed rule groups and custom rules, then associate with
the CloudFront distribution.
