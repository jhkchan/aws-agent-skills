# Baseline (no-skill) response: cross-account-dest-bucket-policy-missing-blocked

This file captures what a generic assistant produces WITHOUT the
s3-replication-operator skill loaded.

---

For cross-account S3 replication, the IAM role in account 111111111111
needs `s3:ReplicateObject` on the destination bucket. Add a policy like:

```bash
aws s3api put-bucket-policy --bucket audit-logs-dest --policy '{
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::111111111111:role/s3-repl-role"},
    "Action": ["s3:ReplicateObject", "s3:ReplicateDelete"],
    "Resource": "arn:aws:s3:::audit-logs-dest/*"
  }]
}'
```

Also make sure the destination KMS key policy grants the role
`kms:Encrypt`. After that, replication should start working.
