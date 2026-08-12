# Baseline (no-skill) — table-bucket-policy-separate

> This is the response a model produces **without** the skill
> definition. It uses `aws s3api put-bucket-policy` with `s3:*` IAM
> actions — which does NOT work on a table bucket. Table buckets
> require `put-table-bucket-policy` with `s3tables:*` actions. The
> baseline misses the entire separation between table bucket policy
> and regular S3 bucket policy. Generated for with-skill-vs-baseline
> comparison.

---

Create the bucket and add a bucket policy:

```bash
aws s3api create-bucket --bucket shared-tables --region us-east-1

aws s3api put-bucket-policy --bucket shared-tables --policy '{
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "999999999999"},
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::shared-tables/*"
  }]
}'
```
