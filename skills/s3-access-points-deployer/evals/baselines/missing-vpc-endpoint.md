# Baseline (no-skill) — missing-vpc-endpoint

> This is the response a model produces **without** the skill definition.
> It creates the access point without flagging the missing VPC endpoint,
> producing a silent partial deployment. Generated for with-skill-vs-
> baseline comparison.

---

You can create a VPC-only access point like this:

```bash
aws s3control create-access-point \
  --account-id 123456789012 \
  --name internal-logs-ap \
  --bucket internal-logs \
  --vpc-configuration VpcId=vpc-998877
```

Then add a policy:

```bash
aws s3control put-access-point-policy \
  --account-id 123456789012 \
  --name internal-logs-ap \
  --policy '<policy-json>'
```

Your bucket is now VPC-only.
