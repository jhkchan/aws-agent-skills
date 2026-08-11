# Baseline (no-skill) — vpc-only-team-ap

> This is the response a model produces **without** the skill definition.
> It creates the access point but omits the through-AP-only bucket-policy
> Deny (so the "VPC-only" claim is false), uses the bucket ARN instead of
> the access-point ARN in the AP policy (dead policy), and skips per-AP
> Block Public Access. Generated for with-skill-vs-baseline comparison.

---

To create a VPC-only access point for Team A:

1. Create the access point:
```bash
aws s3control create-access-point \
  --account-id 123456789012 \
  --name team-a-vpc-ap \
  --bucket prod-shared-data \
  --vpc-configuration VpcId=vpc-0abc123def456
```

2. Add a policy to the access point:
```bash
aws s3control put-access-point-policy \
  --account-id 123456789012 \
  --name team-a-vpc-ap \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::123456789012:role/TeamARole"},
      "Action": ["s3:GetObject","s3:PutObject","s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::prod-shared-data",
        "arn:aws:s3:::prod-shared-data/team-a/*"
      ]
    }]
  }'
```

Now Team A can access the bucket through the access point from VPC
vpc-0abc123def456.
