# Baseline (no-skill) — regional-alb-with-managed-rules

> This is the response a model produces **without** the skill definition.
> It produces a basic create-web-acl command but misses the rule priority
> ordering (allow-list rules before managed rules), the visibility config
> requirement on every rule, the Firehose `aws-waf-logs-` prefix
> requirement, the distinction between OverrideAction None vs Count for
> managed rules, and the structured checklist output format.

---

Here's how to create your WAF Web ACL:

```bash
aws wafv2 create-web-acl \
  --name payments-api-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --region us-east-1
```

Add the managed rules and associate it with your ALB. You can
enable logging to Firehose after creating the stream.
