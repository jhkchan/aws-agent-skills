# Baseline (no-skill) — missing-principal-ids

> This is the response a model produces **without** the skill definition.
> It does not detect that no principals have been specified. It proceeds
> to create a resource share without principals, which will create an
> empty share that no one can access — rather than flagging the missing
> prerequisite and asking for the principal IDs.

---

You can create the resource share first and add principals later:

```bash
aws ram create-resource-share \
  --name shared-subnets-prod \
  --resources arn=arn:aws:ec2:us-east-1:123456789012:subnet/subnet-abc123,type=ec2:Subnet \
  --region us-east-1
```

Once you decide which accounts to share with, you can add them with
`associate-resource-share`.
