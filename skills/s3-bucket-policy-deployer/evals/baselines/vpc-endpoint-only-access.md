# Baseline (no-skill) — vpc-endpoint-only-access

> This is the response a model produces **without** the skill
> definition. It uses `aws:SourceVpc` instead of `aws:SourceVpce`
> (which is only populated for VPC-endpoint traffic and has
> different semantics), uses `StringEquals` Allow instead of a Deny
> (which does not block internet traffic), and does not verify the
> endpoint ID. Generated for with-skill-vs-baseline comparison.

---

To restrict the bucket to VPC traffic:

```bash
aws s3api put-bucket-policy \
  --bucket internal-data \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": "arn:aws:s3:::internal-data/*",
      "Condition": {
        "StringEquals": { "aws:SourceVpc": "vpc-0abc123def456" }
      }
    }]
  }'
```

This restricts access to the specified VPC.
