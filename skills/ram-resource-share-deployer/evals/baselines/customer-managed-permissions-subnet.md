# Baseline (no-skill) — customer-managed-permissions-subnet

> This is the response a model produces **without** the skill definition.
> It creates the resource share with the default managed permission
> instead of a customer-managed permission, missing the
> create-permission step, the associate-resource-share-permission step,
> and the fine-grained policy template. It also lacks the structured
> checklist output format.

---

Create the resource share:

```bash
aws ram create-resource-share \
  --name shared-subnets-custom-perm \
  --principals arn:aws:organizations::123456789012:ou/o-abc123def/ou-xyz456 \
  --resources arn=arn:aws:ec2:us-east-1:123456789012:subnet/subnet-abc123,type=ec2:Subnet \
  --region us-east-1
```

You can create a custom permission policy if needed after the share is
created.
