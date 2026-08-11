# Baseline (no-skill) — missing-organization-delegated-admin

> This is the response a model produces **without** the skill definition.
> It does not detect that the delegated administrator has not been
> registered and Config is not enabled as a trusted service in
> Organizations. It emits a create command that will silently fail or
> show no source accounts, rather than flagging the missing prerequisites.

---

You can create the aggregator like this:

```bash
aws configservice put-configuration-aggregator \
  --configuration-aggregator-name org-compliance-aggregator \
  --organization-aggregation-source RoleArn=arn:aws:iam::123456789012:role/ConfigRole,AllAwsRegions=true \
  --region us-east-1
```

This should aggregate all accounts in your organization. Add your
conformance pack after.
