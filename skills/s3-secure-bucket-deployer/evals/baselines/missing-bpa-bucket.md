# Baseline (no-skill) — missing-bpa-bucket

> This is the response a model produces **without** the skill definition.
> It gives generic advice but misses the PREREQUISITES_MISSING verdict
> shape, the Object Ownership = BucketOwnerEnforced recommendation,
> and the structured checklist with verification commands.

---

Your legacy bucket is missing some security configurations. Here's what
you should do:

1. Enable Block Public Access on the bucket:
```bash
aws s3api put-public-access-block --bucket legacy-app-data \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

2. Add a bucket policy to enforce HTTPS:
```bash
aws s3api put-bucket-policy --bucket legacy-app-data --policy '{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Principal": "*",
    "Action": "s3:*",
    "Resource": ["arn:aws:s3:::legacy-app-data","arn:aws:s3:::legacy-app-data/*"],
    "Condition": {"Bool": {"aws:SecureTransport": false}}
  }]
}'
```

3. The bucket already has SSE-S3 encryption and versioning, so those are
fine.

4. Consider setting up Object Ownership controls.

That should cover the main security gaps.
