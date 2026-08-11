# Baseline (no-skill) — cross-account-external-id

> This is the response a model produces **without** the skill
> definition. It grants cross-account access using `:root` as the
> principal (which delegates to the entire partner account instead
> of a specific role), omits the `aws:ExternalId` condition (no
> confused-deputy protection), and does not include the HTTPS-only
> Deny. Generated for with-skill-vs-baseline comparison.

---

To grant the partner account access to the shared prefix:

```bash
aws s3api put-bucket-policy \
  --bucket prod-shared-data \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::998877665544:root" },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::prod-shared-data/*"
    }]
  }'
```

The partner account can now access the bucket.
