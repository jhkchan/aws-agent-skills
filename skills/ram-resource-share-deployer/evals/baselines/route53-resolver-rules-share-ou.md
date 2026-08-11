# Baseline (no-skill) — route53-resolver-rules-share-ou

> This is the response a model produces **without** the skill definition.
> It creates the share with the OU ARN but misses the
> allowExternalPrincipals flag, does not verify Organizations all features
> is enabled (required for OU ARN principals), does not verify the
> resolver rule type permission, and lacks the structured checklist
> output format.

---

Share the resolver rule with the OU:

```bash
aws ram create-resource-share \
  --name shared-resolver-rules-ou \
  --principals arn:aws:organizations::123456789012:ou/o-abc123def/ou-xyz456 \
  --resources arn=arn:aws:route53resolver:us-east-1:123456789012:resolver-rule/rslvr-rr-abc123,type=route53resolver:ResolverRule \
  --region us-east-1
```

Accounts in that OU should be able to use the resolver rule.
