# Baseline (no-skill) — subnet-share-with-accounts

> This is the response a model produces **without** the skill definition.
> It produces a basic create-resource-share command but misses the
> allowExternalPrincipals flag (leaves it default), does not verify the
> permission association, does not check Organization feature set for
> auto-accept, and lacks the structured checklist output format.

---

Here's how to create your RAM resource share:

```bash
aws ram create-resource-share \
  --name shared-subnets-prod \
  --principals 111111111111 222222222222 \
  --resources arn=arn:aws:ec2:us-east-1:123456789012:subnet/subnet-abc123,type=ec2:Subnet \
              arn=arn:aws:ec2:us-east-1:123456789012:subnet/subnet-def456,type=ec2:Subnet \
  --region us-east-1
```

The accounts should be able to see the shared subnets after this.
