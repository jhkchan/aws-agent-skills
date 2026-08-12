# Baseline (no-skill) response: repository-verification-bucket-region-mismatch

---

The repository verification is failing. This is usually an IAM or
bucket policy issue. Double-check that the snapshot role has
`s3:PutObject` and `s3:ListBucket` on the bucket, and that the trust
policy allows the OpenSearch service to assume the role.

You might also want to verify the bucket name is correct and that
the bucket exists in the right account.
