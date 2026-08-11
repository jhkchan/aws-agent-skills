# Baseline (no-skill) — org-aggregator-delegated-admin

> This is the response a model produces **without** the skill definition.
> It produces a basic put-configuration-aggregator command but misses the
> delegated administrator prerequisite (enable-aws-service-access +
> register-delegated-administrator), the org-level conformance pack
> deployment (uses account-level instead of org-level), the Lambda
> resource policy granting config.amazonaws.com invoke permission, and the
> structured checklist output format.

---

Here's how to create your Config aggregator:

```bash
aws configservice put-configuration-aggregator \
  --configuration-aggregator-name org-compliance-aggregator \
  --organization-aggregation-source RoleArn=arn:aws:iam::123456789012:role/ConfigRole,AllAwsRegions=true \
  --region us-east-1
```

You can add conformance packs and config rules after the aggregator
is created. Make sure Config is enabled in your accounts.
