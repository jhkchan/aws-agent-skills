# Baseline (no-skill) — logging-missing-firehose-prefix

> This is the response a model produces **without** the skill
> definition. It enables logging to the Firehose stream without
> flagging the naming prefix violation (must start with
> aws-waf-logs-). Does not emit a PREREQUISITES_MISSING verdict.
> Generated for with-skill-vs-baseline comparison.

---

Create the Web ACL and enable logging:

```bash
aws wafv2 create-web-acl \
  --name edge-protection \
  --scope CLOUDFRONT \
  --default-action Allow={}

aws wafv2 put-logging-configuration \
  --web-acl-arn <arn> \
  --logging-configuration \
    LogDestinationConfigs=arn:aws:firehose:us-east-1:...:deliverystream/waf-traffic-stream
```
