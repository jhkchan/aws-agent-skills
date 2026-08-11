# Baseline (no-skill) — cross-account-ap-delegation

> This is the response a model produces **without** the skill definition.
> It grants the foreign account `s3:CreateAccessPoint` without adding the
> containment Deny on the foreign-owned AP ARN — the foreign account can
> attach a permissive AP policy and expose the `internal/` prefix.
> Generated for with-skill-vs-baseline comparison.

---

Add this to the bucket policy for `shared-with-partner`:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::991122334455:root"},
    "Action": "s3:CreateAccessPoint",
    "Resource": "arn:aws:s3:::shared-with-partner"
  }]
}
```

Then the partner account runs:

```bash
aws s3control create-access-point \
  --account-id 991122334455 \
  --name partner-ap \
  --bucket arn:aws:s3:::shared-with-partner
```

The partner can now scope their AP to `partner-data/` in their own AP policy.
