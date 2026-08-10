# Baseline (no-skill) — rate-based-forwarded-ip-api-gateway

> This is the response a model produces **without** the skill definition.
> It creates a basic rate-based rule but uses `IP` aggregate key (not
> FORWARDED_IP) because it does not know the CDN/proxy distinction. It
> misses the ForwardedIPConfig fields (HeaderName, FallbackBehavior,
> Position), the CloudWatch Logs resource policy requirement, and the
> API Gateway association ARN format.

---

Here's how to protect your API Gateway with WAF:

```bash
aws wafv2 create-web-acl \
  --name orders-api-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --region us-west-2
```

Add a rate-based rule with a limit of 500 and the managed SQLi
rules. Associate it with your API Gateway stage.
