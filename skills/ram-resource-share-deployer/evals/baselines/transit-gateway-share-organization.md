# Baseline (no-skill) — transit-gateway-share-organization

> This is the response a model produces **without** the skill definition.
> It creates the share with the Organization ARN but misses the
> allowExternalPrincipals flag, does not verify Organizations all features
> is enabled (required for Organization ARN principals to auto-accept),
> does not verify the permission association, and lacks the structured
> checklist output format.

---

Create your RAM resource share with the Organization ARN:

```bash
aws ram create-resource-share \
  --name shared-tgw-org \
  --principals arn:aws:organizations::123456789012:organization/o-abc123def \
  --resources arn=arn:aws:ec2:us-east-1:123456789012:transit-gateway/tgw-0abc123def,type=ec2:TransitGateway \
  --region us-east-1
```

All accounts in your Organization will have access to the Transit Gateway.
