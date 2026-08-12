# Baseline (no-skill) — cloudfront-acl-wrong-region

> This is the response a model produces **without** the skill
> definition. It creates the CloudFront-scoped Web ACL in us-west-2
> without flagging the region constraint (CloudFront scope requires
> us-east-1). Does not emit a PREREQUISITES_MISSING verdict. The
> association with the CloudFront distribution will fail at runtime.
> Generated for with-skill-vs-baseline comparison.

---

Create the CloudFront Web ACL in us-west-2:

```bash
aws wafv2 create-web-acl \
  --name cdn-protection \
  --scope CLOUDFRONT \
  --region us-west-2 \
  --default-action Block={}
```

Add the managed rule groups and associate with distribution
E9876543210.
