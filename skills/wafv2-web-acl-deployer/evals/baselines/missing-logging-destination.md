# Baseline (no-skill) — missing-logging-destination

> This is the response a model produces **without** the skill definition.
> It attempts to create the Web ACL and enable logging without flagging
> the missing Firehose delivery stream as a prerequisite gap. It misses
> the PREREQUISITES_MISSING verdict entirely and produces a checklist
> without citing the specific logging destination requirement.

---

Here's how to create your WAF Web ACL with logging:

```bash
aws wafv2 create-web-acl \
  --name payments-api-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --region us-east-1

aws wafv2 put-logging-configuration \
  --logging-configuration WebACLArn=<arn>,LogDestinationConfigs=<firehose-arn>
```

You'll need to create the Firehose stream first. Use
`aws firehose create-delivery-stream`.
