# Baseline (no-skill) — cloudfront-global-with-bot-control

> This is the response a model produces **without** the skill definition.
> It knows to create a CLOUDFRONT-scope ACL but misses the Bot Control
> category override syntax, the FORWARDED_IP aggregate key configuration
> (Position FIRST, FallbackBehavior), the `aws-waf-logs-` Firehose prefix
> requirement, and the CloudFront distribution association pattern (set
> WebACLId on the distribution, not via WAF API).

---

Create a CloudFront WAF:

```bash
aws wafv2 create-web-acl \
  --name payments-cdn-waf \
  --scope CLOUDFRONT \
  --default-action Allow={} \
  --region us-east-1
```

Add Bot Control rules and a geo-block rule. Then associate the
ACL with your CloudFront distribution.
